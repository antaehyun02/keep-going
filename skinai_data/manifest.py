"""로컬 manifest_zips.csv 로드."""

# ── 표준 라이브러리 ──────────────────────────────────────────────
import logging
import os
from pathlib import Path

# ── 서드파티 ─────────────────────────────────────────────────────
import pandas as pd

logger = logging.getLogger(__name__)

# ── 상수 ─────────────────────────────────────────────────────────
# build_manifest.py 가 skinai_data/scripts/manifest_zips.csv 에 저장하므로 동일 경로 사용
_DEFAULT_MANIFEST_PATH = Path(__file__).resolve().parent / "scripts" / "manifest_zips.csv"

REQUIRED_COLUMNS = [
    "file_id", "zip_name", "class_name", "class_idx",
    "split", "direction", "label_zip_name", "label_file_id",
]


# ── 헬퍼 ─────────────────────────────────────────────────────────

def _resolve_manifest_path() -> Path:
    """manifest CSV 경로 결정.

    우선순위:
        1. 환경변수 MANIFEST_CSV_PATH
        2. 프로젝트 루트 manifest_zips.csv

    Returns:
        Path: CSV 파일 경로
    """
    env_path = os.environ.get("MANIFEST_CSV_PATH")
    if env_path:
        return Path(env_path)
    return _DEFAULT_MANIFEST_PATH


# ── 공개 API ─────────────────────────────────────────────────────

def load_manifest() -> pd.DataFrame:
    """manifest_zips.csv를 로드하여 DataFrame으로 반환.

    로드 순서:
        1. 환경변수 MANIFEST_CSV_PATH가 있으면 해당 경로
        2. 없으면 프로젝트 루트 manifest_zips.csv

    Returns:
        pd.DataFrame: manifest 데이터
            컬럼: file_id, zip_name, class_name, class_idx,
                   split, direction, label_zip_name, label_file_id

    Raises:
        FileNotFoundError: CSV 파일이 존재하지 않을 때
        ValueError: 필수 컬럼 누락 시
    """
    csv_path = _resolve_manifest_path()

    if not csv_path.exists():
        raise FileNotFoundError(
            f"[ERROR] manifest CSV를 찾을 수 없습니다: {csv_path}\n"
            "skinai_data/scripts/build_manifest.py를 먼저 실행하세요."
        )

    df = pd.read_csv(csv_path)
    logger.debug(f"manifest 로드: {csv_path} ({len(df)}건)")

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"[ERROR] manifest 필수 컬럼 누락: {missing}")

    return df
