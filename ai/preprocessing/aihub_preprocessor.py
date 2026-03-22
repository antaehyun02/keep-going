"""AI Hub 08-14 안면부 피부질환 데이터 전처리 파이프라인.

사용법:
    python -m scin.data.aihub_preprocessor \
        --data_root ~/.cache/skinai_data \
        --output_dir scin/data/processed_aihub
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from PIL import Image
from tqdm import tqdm

CLASS_MAP = {
    "건선": 0, "아토피피부염": 1, "여드름": 2,
    "주사": 3, "지루피부염": 4, "정상": 5,
}
IDX_TO_CLASS = {v: k for k, v in CLASS_MAP.items()}

logger = logging.getLogger(__name__)


class AIHubPreprocessor:
    """AI Hub 08-14 데이터 전처리기."""

    def __init__(self, data_root: str, output_dir: str):
        self.data_root = Path(data_root)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self):
        """전체 전처리 파이프라인 실행."""
        print("=" * 60)
        print("AI Hub 08-14 전처리 파이프라인")
        print("=" * 60)

        print("\n[1/7] manifest 로드...")
        df = self.load_manifest()

        print(f"\n[2/7] 정면(front) 필터링...")
        df = self.filter_front(df)

        print(f"\n[3/7] 이미지 유효성 검증...")
        df = self.validate_images(df)

        print(f"\n[4/7] JSON 메타데이터 파싱...")
        df = self.parse_json_meta(df)

        print(f"\n[5/7] 라벨 인코딩...")
        df = self.encode_labels(df)

        print(f"\n[6/7] 데이터셋 분할...")
        split_dfs = self.split_dataset(df)

        print(f"\n[7/7] CSV 저장...")
        self.save_csv(split_dfs)

        print("\n" + "=" * 60)
        self.print_summary(split_dfs)

    def load_manifest(self) -> pd.DataFrame:
        """manifest.csv 로드 또는 로컬 디렉토리 스캔."""
        manifest_path = self.data_root / "manifest.csv"

        if manifest_path.exists():
            df = pd.read_csv(manifest_path)
            print(f"  → manifest.csv 로드: {len(df)}건")
            return df

        print("  → manifest.csv 없음. 로컬 디렉토리 스캔...")
        return self._scan_local_directory()

    def _scan_local_directory(self) -> pd.DataFrame:
        """로컬 디렉토리 구조에서 데이터 목록 생성."""
        records = []
        split_dirs = {
            "1.Training": "train", "2.Validation": "val", "3.Test": "test",
            "Training": "train", "Validation": "val", "Test": "test",
            "train": "train", "val": "val", "test": "test",
        }

        for split_dir in sorted(self.data_root.iterdir()):
            if not split_dir.is_dir():
                continue

            split_name = None
            for key, val in split_dirs.items():
                if key in split_dir.name:
                    split_name = val
                    break
            if not split_name:
                continue

            source_dir = split_dir / "1.원천데이터"
            if not source_dir.exists():
                source_dir = split_dir

            for png_path in source_dir.rglob("*.png"):
                parts = png_path.relative_to(source_dir).parts
                class_name = parts[0] if len(parts) > 1 else "unknown"
                direction_kr = parts[1] if len(parts) > 2 else ""

                direction = "front" if ("P2" in png_path.name or "정면" in direction_kr) else "side"

                records.append({
                    "file_id": "",
                    "filename": png_path.name,
                    "image_path": str(png_path),
                    "storage_path": str(png_path.relative_to(self.data_root)),
                    "class_name": class_name,
                    "class_idx": CLASS_MAP.get(class_name, -1),
                    "split": split_name,
                    "direction": direction,
                })

        df = pd.DataFrame(records)
        print(f"  → 로컬 스캔 완료: {len(df)}건")
        return df

    def filter_front(self, df: pd.DataFrame) -> pd.DataFrame:
        """정면(front) 이미지만 필터링."""
        before = len(df)

        mask_direction = df["direction"] == "front"
        mask_filename = df["filename"].str.contains("P2", na=False)
        mask = mask_direction | mask_filename

        df = df[mask].reset_index(drop=True)
        print(f"  → {before}건 → {len(df)}건 (정면만)")
        return df

    def validate_images(self, df: pd.DataFrame) -> pd.DataFrame:
        """이미지 유효성 검사: 손상/해상도/채널."""
        valid_indices = []
        corrupt_files = []

        for idx, row in tqdm(df.iterrows(), total=len(df), desc="  이미지 검증"):
            image_path = row.get("image_path", "")
            if not image_path:
                cache_path = Path.home() / ".cache" / "skinai_data" / "images" / row["filename"]
                image_path = str(cache_path)

            try:
                img = Image.open(image_path)
                img.verify()

                img = Image.open(image_path)
                w, h = img.size

                if w < 100 or h < 100:
                    corrupt_files.append((row["filename"], f"해상도 부족: {w}x{h}"))
                    continue

                valid_indices.append(idx)
            except FileNotFoundError:
                valid_indices.append(idx)
            except Exception as e:
                corrupt_files.append((row["filename"], str(e)))

        if corrupt_files:
            corrupt_path = self.output_dir / "corrupt_files.txt"
            with open(corrupt_path, "w") as f:
                for name, reason in corrupt_files:
                    f.write(f"{name}\t{reason}\n")
            print(f"  → 손상 파일 {len(corrupt_files)}건 기록: {corrupt_path}")

        df = df.loc[valid_indices].reset_index(drop=True)
        print(f"  → 유효 이미지: {len(df)}건")
        return df

    def parse_json_meta(self, df: pd.DataFrame) -> pd.DataFrame:
        """JSON 라벨링 파일에서 임상 메타데이터 추출."""
        meta_cols = ["gender", "age_range", "race", "severity", "lesion_type"]
        for col in meta_cols:
            if col not in df.columns:
                df[col] = ""

        json_found = 0
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="  JSON 파싱"):
            json_name = Path(row["filename"]).stem + ".json"

            json_candidates = []
            if "image_path" in row and row["image_path"]:
                img_dir = Path(row["image_path"]).parent
                label_dir = str(img_dir).replace("1.원천데이터", "2.라벨링데이터")
                json_candidates.append(Path(label_dir) / json_name)

            for json_path in json_candidates:
                if json_path.exists():
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)

                        params = data.get("generated_parameters", {})
                        df.at[idx, "gender"] = params.get("gender", "")
                        df.at[idx, "age_range"] = params.get("age_range", "")
                        df.at[idx, "race"] = params.get("race", "")

                        diag_info = data.get("diagnosis_info", {})
                        easi = diag_info.get("easi_score", {})
                        df.at[idx, "severity"] = easi.get("iga_grade", "")

                        bbox = data.get("bbox", {})
                        lesions = bbox.get("lesions", [])
                        if lesions:
                            df.at[idx, "lesion_type"] = lesions[0].get("inflammatory", "")

                        json_found += 1
                    except Exception as e:
                        logger.warning(f"JSON 파싱 실패: {json_path} - {e}")
                    break

        print(f"  → JSON 매칭: {json_found}/{len(df)}건")
        return df

    def encode_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """class_name → class_idx 변환."""
        if "class_idx" not in df.columns or df["class_idx"].isna().any():
            df["class_idx"] = df["class_name"].map(CLASS_MAP)

        unknown = df[df["class_idx"].isna()]
        if len(unknown) > 0:
            print(f"  [경고] 알 수 없는 클래스 {len(unknown)}건 제거")
            df = df.dropna(subset=["class_idx"]).reset_index(drop=True)

        df["class_idx"] = df["class_idx"].astype(int)
        print(f"  → 라벨 인코딩 완료: {df['class_idx'].nunique()}개 클래스")
        return df

    def split_dataset(self, df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """manifest의 split 컬럼 기준으로 분리."""
        split_dfs = {}
        for split_name in ["train", "val", "test"]:
            split_df = df[df["split"] == split_name].reset_index(drop=True)
            split_dfs[split_name] = split_df
            print(f"  → {split_name}: {len(split_df)}건")
        return split_dfs

    def save_csv(self, split_dfs: dict[str, pd.DataFrame]):
        """train/val/test.csv 및 metadata.json 저장."""
        columns = [
            "image_path", "filename", "class_idx", "class_name", "split",
            "gender", "age_range", "race", "severity", "lesion_type",
        ]

        for split_name, split_df in split_dfs.items():
            save_cols = [c for c in columns if c in split_df.columns]
            csv_path = self.output_dir / f"{split_name}.csv"
            split_df[save_cols].to_csv(csv_path, index=False)
            print(f"  → 저장: {csv_path} ({len(split_df)}건)")

        all_df = pd.concat(split_dfs.values(), ignore_index=True)
        metadata = {
            "num_classes": 6,
            "class_map": CLASS_MAP,
            "splits": {name: len(df) for name, df in split_dfs.items()},
            "class_distribution": {
                split: all_df[all_df["split"] == split]["class_name"]
                .value_counts().to_dict()
                for split in ["train", "val", "test"]
            },
            "processed_at": datetime.now().isoformat(),
        }

        meta_path = self.output_dir / "metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"  → 메타데이터: {meta_path}")

    def print_summary(self, split_dfs: dict[str, pd.DataFrame]):
        """클래스별 분포 요약 출력."""
        print("전처리 완료 요약")
        print("=" * 60)
        for split_name, split_df in split_dfs.items():
            print(f"\n[{split_name}] 총 {len(split_df)}건")
            if len(split_df) > 0:
                dist = split_df["class_name"].value_counts()
                for cls_name, count in dist.items():
                    print(f"  {cls_name:12s}: {count:5d}장")


def main():
    parser = argparse.ArgumentParser(description="AI Hub 08-14 전처리")
    parser.add_argument("--data_root", required=True, help="원본 데이터 경로")
    parser.add_argument("--output_dir", default="scin/data/processed_aihub", help="출력 경로")
    args = parser.parse_args()

    preprocessor = AIHubPreprocessor(args.data_root, args.output_dir)
    preprocessor.run()


if __name__ == "__main__":
    main()
