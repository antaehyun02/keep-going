"""manifest_zips.csv를 읽어 Drive에서 ZIP을 다운로드하고 압축을 해제.

사용법:
    # 정면 원천데이터 ZIP 저장 (전처리기용 기본 모드)
    python skinai_data/scripts/download_dataset.py --save-zip

    # ZIP 압축 해제 (data/raw/ 아래 PNG로 저장)
    python skinai_data/scripts/download_dataset.py

    # 특정 split만
    python skinai_data/scripts/download_dataset.py --split train

    # 정면+측면 모두
    python skinai_data/scripts/download_dataset.py --direction all

    # 라벨(JSON) ZIP도 함께 다운로드
    python skinai_data/scripts/download_dataset.py --include-labels

    # 이미 다운로드된 항목 건너뜀 (재실행 안전)
    python skinai_data/scripts/download_dataset.py --resume

--save-zip 모드: ZIP을 data/dataset_14/ 구조에 그대로 저장 → aihub_preprocessor 와 직접 호환
기본 모드: ZIP을 다운로드 후 압축 해제 → data/raw/{split}/ 아래 PNG 저장
"""

# ── 표준 라이브러리 ──────────────────────────────────────────────
import argparse
import io
import logging
import sys
import zipfile
from pathlib import Path
from typing import Optional

# ── 서드파티 ─────────────────────────────────────────────────────
import pandas as pd
from googleapiclient.errors import HttpError
from tqdm import tqdm

# ── 로컬 ─────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from skinai_data.auth import get_drive_service

# ── 로거 설정 ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── 상수 ─────────────────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent          # skinai_data/scripts/
PROJECT_ROOT = _SCRIPT_DIR.parents[1]                   # 프로젝트 루트
DEFAULT_MANIFEST_PATH = _SCRIPT_DIR / "manifest_zips.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_DATASET14_DIR = PROJECT_ROOT / "data" / "dataset_14"
VALID_SPLITS = {"train", "val", "test"}
VALID_DIRECTIONS = {"front", "side"}

# ZIP 파일명 접두사 → dataset_14 내 서브디렉토리 매핑
ZIP_PREFIX_TO_SUBDIR = {
    "TS": "Training/01_raw",
    "TL": "Training/02_label",
    "VS": "Validation/01_raw",
    "VL": "Validation/02_label",
}


# ── 헬퍼 ─────────────────────────────────────────────────────────

def _download_zip(service, file_id: str, zip_name: str) -> bytes:
    """Drive에서 ZIP 파일을 다운로드하여 bytes 반환.

    Args:
        service: Drive API 서비스 객체
        file_id: Drive 파일 ID
        zip_name: 파일명 (로그 출력용)

    Returns:
        bytes: ZIP 파일 내용

    Raises:
        HttpError: Drive API 호출 실패 시
    """
    try:
        request = service.files().get_media(fileId=file_id)
        return request.execute()
    except HttpError as e:
        logger.error(f"[ERROR] 다운로드 실패: {zip_name} (id={file_id}), error={e}")
        raise


def _save_zip(content: bytes, dataset14_dir: Path, zip_name: str) -> Path:
    """ZIP bytes를 dataset_14 구조에 그대로 저장.

    ZIP 파일명 접두사로 대상 서브디렉토리를 결정:
        TS_* → Training/01_raw/
        TL_* → Training/02_label/
        VS_* → Validation/01_raw/
        VL_* → Validation/02_label/

    Args:
        content: ZIP 파일 바이트 내용
        dataset14_dir: data/dataset_14/ 루트 경로
        zip_name: ZIP 파일명 (예: TS_건선_정면.zip)

    Returns:
        Path: 저장된 ZIP 파일 경로

    Raises:
        ValueError: 알 수 없는 ZIP 접두사인 경우
    """
    prefix = zip_name[:2].upper()
    subdir = ZIP_PREFIX_TO_SUBDIR.get(prefix)
    if subdir is None:
        raise ValueError(f"[ERROR] ZIP 접두사 인식 불가: '{prefix}' (파일: {zip_name})")

    target_dir = dataset14_dir / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / zip_name
    target_path.write_bytes(content)
    return target_path


def _extract_zip(content: bytes, output_dir: Path, zip_name: str) -> int:
    """ZIP bytes를 output_dir에 압축 해제.

    Args:
        content: ZIP 파일 바이트 내용
        output_dir: 압축 해제 대상 디렉토리
        zip_name: 파일명 (로그 출력용)

    Returns:
        int: 압축 해제된 파일 수

    Raises:
        zipfile.BadZipFile: 손상된 ZIP 파일인 경우
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        zf.extractall(output_dir)
        return len(zf.namelist())


def _build_target_rows(
    df: pd.DataFrame,
    split: Optional[str],
    direction: Optional[str],
    include_labels: bool,
) -> list[dict]:
    """다운로드 대상 행 목록 구성.

    Args:
        df: manifest DataFrame
        split: 특정 split 필터 (None이면 전체)
        direction: 특정 방향 필터 (None이면 front만)
        include_labels: True이면 라벨 ZIP도 포함

    Returns:
        list[dict]: 다운로드 대상 정보 (file_id, zip_name, output_subdir)
    """
    mask = pd.Series([True] * len(df), index=df.index)

    if split:
        mask &= df["split"] == split

    if direction == "all":
        pass  # 필터 없음
    else:
        target_dir = direction or "front"
        mask &= df["direction"] == target_dir

    filtered = df[mask]
    rows = []

    for _, row in filtered.iterrows():
        # 원천 ZIP
        rows.append({
            "file_id": row["file_id"],
            "zip_name": row["zip_name"],
            "output_subdir": row["split"],
        })
        # 라벨 ZIP (선택)
        if include_labels and row.get("label_file_id"):
            rows.append({
                "file_id": row["label_file_id"],
                "zip_name": row["label_zip_name"],
                "output_subdir": row["split"],
            })

    return rows


# ── 메인 ─────────────────────────────────────────────────────────

def download_dataset(
    manifest_path: Path,
    output_dir: Path,
    split: Optional[str],
    direction: Optional[str],
    include_labels: bool,
    resume: bool,
    save_zip: bool,
) -> None:
    """manifest_zips.csv에서 ZIP을 다운로드.

    두 가지 저장 모드:
        save_zip=True  → data/dataset_14/ 구조에 ZIP 그대로 저장 (전처리기 직접 호환)
        save_zip=False → ZIP 압축 해제 후 data/raw/{split}/ 아래 PNG 저장

    Args:
        manifest_path: manifest_zips.csv 경로
        output_dir: 압축 해제 루트 디렉토리 (save_zip=False 시 사용)
        split: 특정 split만 처리 (None이면 전체)
        direction: 'front', 'side', 'all' (None이면 front)
        include_labels: 라벨 ZIP 포함 여부
        resume: True이면 이미 존재하는 항목 건너뜀
        save_zip: True이면 ZIP 파일 자체를 data/dataset_14/에 저장
    """
    if not manifest_path.exists():
        logger.error(
            f"[ERROR] manifest CSV 없음: {manifest_path}\n"
            "  scripts/build_manifest.py를 먼저 실행하세요."
        )
        sys.exit(1)

    df = pd.read_csv(manifest_path)
    logger.info(f"manifest 로드: {len(df)}건")

    targets = _build_target_rows(df, split, direction, include_labels)
    logger.info(f"다운로드 대상: {len(targets)}개 ZIP")

    if not targets:
        logger.warning("[WARN] 조건에 맞는 ZIP이 없습니다. --split / --direction 옵션을 확인하세요.")
        return

    service = get_drive_service()
    success = 0
    skipped = 0
    failed = 0

    for target in tqdm(targets, desc="다운로드", unit="ZIP"):
        zip_name = target["zip_name"]

        if save_zip:
            # ZIP 저장 모드: data/dataset_14/ 구조에 그대로 저장
            prefix = zip_name[:2].upper()
            subdir_rel = ZIP_PREFIX_TO_SUBDIR.get(prefix, "")
            zip_path = DEFAULT_DATASET14_DIR / subdir_rel / zip_name
            if resume and zip_path.exists():
                logger.debug(f"건너뜀 (이미 존재): {zip_name}")
                skipped += 1
                continue
            try:
                content = _download_zip(service, target["file_id"], zip_name)
                saved = _save_zip(content, DEFAULT_DATASET14_DIR, zip_name)
                logger.debug(f"완료: {zip_name} → {saved}")
                success += 1
            except (HttpError, ValueError, OSError) as e:
                logger.error(f"[ERROR] 처리 실패: {zip_name}, error={e}")
                failed += 1
        else:
            # 압축 해제 모드: data/raw/{split}/ 아래 PNG 저장
            subdir = output_dir / target["output_subdir"]
            extract_marker = subdir / zip_name.replace(".zip", "")
            if resume and extract_marker.exists():
                logger.debug(f"건너뜀 (이미 존재): {zip_name}")
                skipped += 1
                continue
            try:
                content = _download_zip(service, target["file_id"], zip_name)
                count = _extract_zip(content, subdir, zip_name)
                extract_marker.mkdir(parents=True, exist_ok=True)
                logger.debug(f"완료: {zip_name} ({count}개 파일)")
                success += 1
            except (HttpError, zipfile.BadZipFile, OSError) as e:
                logger.error(f"[ERROR] 처리 실패: {zip_name}, error={e}")
                failed += 1

    print()
    print(f"✅ 완료: 성공 {success} / 건너뜀 {skipped} / 실패 {failed}")
    if save_zip:
        print(f"   저장 위치: {DEFAULT_DATASET14_DIR.resolve()}")
        print()
        print("다음 단계 — 전처리 실행:")
        print("  python -m ai.preprocessing.aihub_preprocessor")
    else:
        print(f"   저장 위치: {output_dir.resolve()}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="manifest_zips.csv 기반 Drive ZIP 다운로드 (ZIP 저장 또는 압축 해제)"
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST_PATH),
        help=f"manifest_zips.csv 경로 (기본: {DEFAULT_MANIFEST_PATH})",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"압축 해제 루트 디렉토리 (기본: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--split",
        choices=["train", "val", "test"],
        default=None,
        help="특정 split만 다운로드 (기본: 전체)",
    )
    parser.add_argument(
        "--direction",
        choices=["front", "side", "all"],
        default="front",
        help="이미지 방향 필터 (기본: front — 학습에 필요한 정면만)",
    )
    parser.add_argument(
        "--include-labels",
        action="store_true",
        help="라벨(JSON) ZIP도 함께 다운로드",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="이미 존재하는 파일 건너뜀",
    )
    parser.add_argument(
        "--save-zip",
        action="store_true",
        help=(
            "ZIP 파일 자체를 data/dataset_14/ 구조에 저장 (전처리기 직접 호환).\n"
            "미지정 시 압축 해제하여 data/raw/{split}/ 아래 PNG로 저장."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    download_dataset(
        manifest_path=Path(args.manifest),
        output_dir=Path(args.output_dir),
        split=args.split,
        direction=args.direction,
        include_labels=args.include_labels,
        resume=args.resume,
        save_zip=args.save_zip,
    )
