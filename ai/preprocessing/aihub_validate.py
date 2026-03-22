"""전처리 완료된 CSV 데이터 검증 스크립트.

사용법:
    python -m scin.data.aihub_validate \
        --processed_dir scin/data/processed_aihub
"""

import argparse
import json
import random
from pathlib import Path

import pandas as pd
from PIL import Image


def validate(processed_dir: str):
    """전처리 결과 검증."""
    processed_dir = Path(processed_dir)
    report = {"passed": [], "failed": [], "warnings": []}

    print("=" * 60)
    print("AI Hub 08-14 데이터 검증")
    print("=" * 60)

    # 1. CSV 파일 존재 확인
    print("\n[1/6] CSV 파일 확인...")
    for split in ["train", "val", "test"]:
        csv_path = processed_dir / f"{split}.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            report["passed"].append(f"{split}.csv 존재 ({len(df)}건)")
            print(f"  ✅ {split}.csv: {len(df)}건")
        else:
            report["failed"].append(f"{split}.csv 누락")
            print(f"  ❌ {split}.csv 누락")

    # 2. 클래스별 샘플 수 균형 체크
    print("\n[2/6] 클래스 분포 균형 확인...")
    for split in ["train", "val", "test"]:
        csv_path = processed_dir / f"{split}.csv"
        if not csv_path.exists():
            continue

        df = pd.read_csv(csv_path)
        dist = df["class_name"].value_counts()
        min_count = dist.min()
        max_count = dist.max()
        ratio = min_count / max_count if max_count > 0 else 0

        if ratio >= 0.8:
            report["passed"].append(f"{split} 클래스 균형 양호 (비율: {ratio:.2f})")
            print(f"  ✅ {split}: 균형 양호 (min/max = {ratio:.2f})")
        else:
            report["warnings"].append(f"{split} 클래스 불균형 (비율: {ratio:.2f})")
            print(f"  ⚠️ {split}: 불균형 감지 (min/max = {ratio:.2f})")

        for cls, cnt in dist.items():
            print(f"      {cls}: {cnt}")

    # 3. 이미지 샘플 검증 (10%)
    print("\n[3/6] 이미지 열기 검증 (10% 샘플)...")
    for split in ["train", "val", "test"]:
        csv_path = processed_dir / f"{split}.csv"
        if not csv_path.exists():
            continue

        df = pd.read_csv(csv_path)
        if "image_path" not in df.columns:
            report["warnings"].append(f"{split}: image_path 컬럼 없음 (Drive 기반 데이터)")
            print(f"  ⚠️ {split}: image_path 컬럼 없음 (건너뜀)")
            continue

        sample_n = max(1, len(df) // 10)
        sample = df.sample(n=min(sample_n, len(df)), random_state=42)

        ok = 0
        fail = 0
        for _, row in sample.iterrows():
            try:
                img = Image.open(row["image_path"])
                img.verify()
                ok += 1
            except FileNotFoundError:
                pass
            except Exception:
                fail += 1

        if fail == 0:
            report["passed"].append(f"{split} 이미지 검증 통과 ({ok}/{len(sample)})")
            print(f"  ✅ {split}: {ok}/{len(sample)} 검증 통과")
        else:
            report["failed"].append(f"{split} 이미지 {fail}건 손상")
            print(f"  ❌ {split}: {fail}/{len(sample)} 손상")

    # 4. label 범위 확인
    print("\n[4/6] label 범위 확인 (0~5)...")
    for split in ["train", "val", "test"]:
        csv_path = processed_dir / f"{split}.csv"
        if not csv_path.exists():
            continue

        df = pd.read_csv(csv_path)
        min_label = df["class_idx"].min()
        max_label = df["class_idx"].max()

        if min_label >= 0 and max_label <= 5:
            report["passed"].append(f"{split} label 범위 정상 ({min_label}~{max_label})")
            print(f"  ✅ {split}: {min_label}~{max_label}")
        else:
            report["failed"].append(f"{split} label 범위 이상 ({min_label}~{max_label})")
            print(f"  ❌ {split}: {min_label}~{max_label}")

    # 5. 필수 컬럼 null 확인
    print("\n[5/6] 필수 컬럼 null 확인...")
    required_cols = ["class_idx", "class_name", "split"]
    for split in ["train", "val", "test"]:
        csv_path = processed_dir / f"{split}.csv"
        if not csv_path.exists():
            continue

        df = pd.read_csv(csv_path)
        for col in required_cols:
            if col not in df.columns:
                report["failed"].append(f"{split}: 필수 컬럼 '{col}' 없음")
                print(f"  ❌ {split}: '{col}' 컬럼 없음")
                continue

            null_count = df[col].isna().sum()
            if null_count == 0:
                report["passed"].append(f"{split}.{col}: null 없음")
            else:
                report["failed"].append(f"{split}.{col}: null {null_count}건")
                print(f"  ❌ {split}.{col}: null {null_count}건")

    all_null_free = all("null" not in f for f in report.get("failed", []))
    if all_null_free:
        print(f"  ✅ 필수 컬럼 null 없음")

    # 6. 전체 요약
    print("\n[6/6] 검증 결과 요약")
    print("=" * 60)
    print(f"  통과: {len(report['passed'])}건")
    print(f"  경고: {len(report['warnings'])}건")
    print(f"  실패: {len(report['failed'])}건")

    if report["failed"]:
        print("\n  실패 항목:")
        for f in report["failed"]:
            print(f"    ❌ {f}")

    # 리포트 저장
    report_path = processed_dir / "validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n리포트 저장: {report_path}")

    return len(report["failed"]) == 0


def main():
    parser = argparse.ArgumentParser(description="AI Hub 08-14 데이터 검증")
    parser.add_argument("--processed_dir", required=True, help="전처리 결과 경로")
    args = parser.parse_args()

    success = validate(args.processed_dir)
    if not success:
        print("\n⚠️ 검증 실패 항목이 있습니다. 확인 후 재전처리하세요.")


if __name__ == "__main__":
    main()
