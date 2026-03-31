"""manifest_zips.csv를 읽어 Drive에서 ZIP을 다운로드하고 압축을 해제.

사용법:
    # 정면 원천데이터만 (기본값 — 학습에 필요한 최소 범위)
    python scripts/download_dataset.py

    # 특정 split만
    python scripts/download_dataset.py --split train

    # 정면+측면 모두
    python scripts/download_dataset.py --direction all

    # 라벨(JSON) ZIP도 함께 다운로드
    python scripts/download_dataset.py --include-labels

    # 이미 다운로드된 ZIP 건너뜀 (재실행 안전)
    python scripts/download_dataset.py --resume

출력 디렉토리 기본값: data/raw/  (프로젝트 루트 기준)
"""

# ── 표준 라이브러리 ──────────────────────────────────────────────
import argparse
import io
import logging
import sys
import zipfile
from pathlib import Path

# ── 서드파티 ─────────────────────────────────────────────────────
import pandas as pd
from googleapiclient.errors import HttpError
from tqdm import tqdm

# ── 로컬 ─────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from skinai_data.auth import get_drive_service

# ── 로거 설정 ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── 상수 ─────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = PROJECT_ROOT / "manifest_zips.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "raw"
VALID_SPLITS = {"train", "val", "test"}
VALID_DIRECTIONS = {"front", "side"}


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
    split: str | None,
    direction: str | None,
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
    split: str | None,
    direction: str | None,
    include_labels: bool,
    resume: bool,
) -> None:
    """manifest_zips.csv에서 ZIP을 다운로드하고 압축 해제.

    Args:
        manifest_path: manifest_zips.csv 경로
        output_dir: 압축 해제 루트 디렉토리
        split: 특정 split만 처리 (None이면 전체)
        direction: 'front', 'side', 'all' (None이면 front)
        include_labels: 라벨 ZIP 포함 여부
        resume: True이면 이미 다운로드된 항목 건너뜀
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
        subdir = output_dir / target["output_subdir"]
        # ZIP 이름에서 확장자를 뺀 디렉토리가 이미 존재하면 skip
        extract_marker = subdir / zip_name.replace(".zip", "")

        if resume and extract_marker.exists():
            logger.debug(f"건너뜀 (이미 존재): {zip_name}")
            skipped += 1
            continue

        try:
            content = _download_zip(service, target["file_id"], zip_name)
            count = _extract_zip(content, subdir, zip_name)
            # 압축 해제 완료 표시 디렉토리 생성 (resume 기준점)
            extract_marker.mkdir(parents=True, exist_ok=True)
            logger.debug(f"완료: {zip_name} ({count}개 파일)")
            success += 1
        except (HttpError, zipfile.BadZipFile, OSError) as e:
            logger.error(f"[ERROR] 처리 실패: {zip_name}, error={e}")
            failed += 1

    print()
    print(f"✅ 완료: 성공 {success} / 건너뜀 {skipped} / 실패 {failed}")
    print(f"   저장 위치: {output_dir.resolve()}")
    print()
    print("다음 단계 — 전처리 실행:")
    print(f"  python -m ai.preprocessing.aihub_preprocessor \\")
    print(f"      --data_root {output_dir.resolve()} \\")
    print(f"      --output_dir ai/preprocessing/processed_aihub")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="manifest_zips.csv 기반 Drive ZIP 다운로드 + 압축 해제"
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
        help="이미 압축 해제된 ZIP 건너뜀",
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
    )
