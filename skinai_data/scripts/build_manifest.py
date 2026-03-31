"""Drive에 업로드된 AI Hub ZIP 파일을 탐색해 manifest_zips.csv를 생성하고 Drive에 업로드.

사용법:
    python skinai_data/scripts/build_manifest.py

필수 환경변수:
    SKINAI_DRIVE_FOLDER_ID  Drive 루트 폴더 ID
    GOOGLE_APPLICATION_CREDENTIALS  Service Account JSON 경로 (서버) 또는
                                    OAuth2 인증 (~/.config/skinai_data/credentials.json)

출력:
    skinai_data/scripts/manifest_zips.csv (로컬 저장)
"""

# ── 표준 라이브러리 ──────────────────────────────────────────────
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# ── 서드파티 ─────────────────────────────────────────────────────
import pandas as pd
from googleapiclient.errors import HttpError

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
CLASS_MAP = {
    "건선": 0,
    "아토피피부염": 1,
    "여드름": 2,
    "주사": 3,
    "지루피부염": 4,
    "정상": 5,
}

# 파일명에서 나타나는 단축 클래스명 → 정식 클래스명 정규화
CLASS_NAME_ALIASES = {
    "아토피": "아토피피부염",
    "지루": "지루피부염",
}

# 파일명 접두사 첫 글자 → split
SPLIT_PREFIX_MAP = {
    "T": "train",
    "V": "val",
    "E": "test",
}

# 파일명 방향 세그먼트 → 영문
DIRECTION_MAP = {
    "정면": "front",
    "측면": "side",
}

MANIFEST_FILENAME = "manifest_zips.csv"
DRIVE_LIST_PAGE_SIZE = 1000


# ── 헬퍼 ─────────────────────────────────────────────────────────

def _list_files_in_folder(service, folder_id: str) -> list[dict]:
    """특정 Drive 폴더의 파일 목록을 반환 (페이지네이션 처리).

    Args:
        service: Drive API 서비스 객체
        folder_id: 조회할 폴더 ID

    Returns:
        list[dict]: 파일 메타데이터 리스트 (id, name, mimeType)

    Raises:
        HttpError: Drive API 호출 실패 시
    """
    files = []
    page_token = None

    while True:
        try:
            response = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="nextPageToken, files(id, name, mimeType)",
                pageSize=DRIVE_LIST_PAGE_SIZE,
                pageToken=page_token,
            ).execute()
        except HttpError as e:
            logger.error(f"[ERROR] 폴더 목록 조회 실패: folder_id={folder_id}, error={e}")
            raise

        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return files


def _walk_folder(service, folder_id: str, depth: int = 0) -> list[dict]:
    """Drive 폴더를 재귀 탐색하여 모든 파일을 반환.

    Args:
        service: Drive API 서비스 객체
        folder_id: 탐색 시작 폴더 ID
        depth: 현재 탐색 깊이 (로깅용)

    Returns:
        list[dict]: 하위 모든 파일 메타데이터 리스트
    """
    items = _list_files_in_folder(service, folder_id)
    all_files = []

    for item in items:
        if item["mimeType"] == "application/vnd.google-apps.folder":
            logger.debug(f"{'  ' * depth}폴더 진입: {item['name']}")
            all_files.extend(_walk_folder(service, item["id"], depth + 1))
        else:
            all_files.append(item)

    return all_files


def _normalize_class_name(raw: str) -> str:
    """파일명에서 추출한 클래스명을 CLASS_MAP 키로 정규화.

    Args:
        raw: 파일명에서 추출한 클래스명 (예: '아토피', '지루')

    Returns:
        str: 정규화된 클래스명 (예: '아토피피부염', '지루피부염')
    """
    return CLASS_NAME_ALIASES.get(raw, raw)


def _parse_zip_name(zip_name: str) -> Optional[dict]:
    """ZIP 파일명에서 split, 파일유형, 클래스, 방향 정보를 추출.

    파일명 형식: {접두사}_{클래스명}_{방향}.zip
    예) TS_건선_정면.zip, TL_아토피_측면.zip

    Args:
        zip_name: ZIP 파일명 (확장자 포함)

    Returns:
        dict | None: 파싱 결과 또는 형식 불일치 시 None
            - split: 'train' | 'val' | 'test'
            - file_type: 'source' | 'label'
            - class_name: 정규화된 클래스명
            - direction: 'front' | 'side'
    """
    if not zip_name.lower().endswith(".zip"):
        return None

    stem = zip_name[:-4]  # 확장자 제거
    parts = stem.split("_")

    if len(parts) < 3:
        return None

    prefix = parts[0]
    if len(prefix) < 2:
        return None

    split_char = prefix[0].upper()
    type_char = prefix[1].upper()

    split = SPLIT_PREFIX_MAP.get(split_char)
    if split is None:
        return None

    file_type = "source" if type_char == "S" else "label" if type_char == "L" else None
    if file_type is None:
        return None

    raw_class = parts[1]
    class_name = _normalize_class_name(raw_class)
    if class_name not in CLASS_MAP:
        logger.warning(f"[WARN] 알 수 없는 클래스명: '{raw_class}' (파일: {zip_name})")
        return None

    raw_direction = parts[2]
    direction = DIRECTION_MAP.get(raw_direction)
    if direction is None:
        logger.warning(f"[WARN] 알 수 없는 방향: '{raw_direction}' (파일: {zip_name})")
        return None

    return {
        "split": split,
        "file_type": file_type,
        "class_name": class_name,
        "direction": direction,
    }


def _make_label_zip_name(source_zip_name: str) -> str:
    """원천 ZIP 파일명에서 라벨 ZIP 파일명으로 변환 (접두사의 S→L).

    Args:
        source_zip_name: 원천 ZIP 파일명 (예: TS_건선_정면.zip)

    Returns:
        str: 라벨 ZIP 파일명 (예: TL_건선_정면.zip)
    """
    # 두 번째 글자(S)를 L로 치환
    return source_zip_name[0] + "L" + source_zip_name[2:]


# ── 메인 ─────────────────────────────────────────────────────────

def build_manifest(folder_id: str) -> pd.DataFrame:
    """Drive 폴더를 탐색해 원천 ZIP 목록을 구성하고 DataFrame 반환.

    Args:
        folder_id: Drive 루트 폴더 ID

    Returns:
        pd.DataFrame: manifest_zips 데이터
    """
    service = get_drive_service()

    logger.info(f"[INFO] Drive 폴더 탐색 시작: {folder_id}")
    all_files = _walk_folder(service, folder_id)
    logger.info(f"[INFO] 탐색된 전체 파일 수: {len(all_files)}")

    # file_id 인덱스 구성 (name → file_id 빠른 조회용)
    name_to_id: dict[str, str] = {f["name"]: f["id"] for f in all_files}

    # 원천 ZIP만 필터링
    source_zips = [
        f for f in all_files
        if f["name"].lower().endswith(".zip") and "_S_" not in f["name"]
        and len(f["name"]) >= 4 and f["name"][1].upper() == "S"
    ]
    logger.info(f"[INFO] 원천 ZIP 수: {len(source_zips)}")

    records = []

    for file_info in source_zips:
        zip_name = file_info["name"]
        parsed = _parse_zip_name(zip_name)
        if parsed is None:
            logger.warning(f"[WARN] 파싱 실패, 건너뜀: {zip_name}")
            continue

        label_zip_name = _make_label_zip_name(zip_name)
        label_file_id = name_to_id.get(label_zip_name)

        if label_file_id is None:
            logger.warning(f"[WARN] 라벨 ZIP 없음: {label_zip_name} (원천: {zip_name})")

        records.append({
            "file_id": file_info["id"],
            "zip_name": zip_name,
            "class_name": parsed["class_name"],
            "class_idx": CLASS_MAP[parsed["class_name"]],
            "split": parsed["split"],
            "direction": parsed["direction"],
            "label_zip_name": label_zip_name,
            "label_file_id": label_file_id or "",
        })

    return pd.DataFrame(records)


def main():
    folder_id = os.environ.get("SKINAI_DRIVE_FOLDER_ID")
    if not folder_id:
        logger.error(
            "[ERROR] SKINAI_DRIVE_FOLDER_ID 환경변수가 설정되지 않았습니다.\n"
            "  export SKINAI_DRIVE_FOLDER_ID='your_folder_id_here'"
        )
        sys.exit(1)

    df = build_manifest(folder_id)

    if df.empty:
        logger.error("[ERROR] 수집된 ZIP 파일이 없습니다. Drive 폴더 구조를 확인하세요.")
        sys.exit(1)

    # 로컬 저장 — 스크립트와 같은 디렉토리 (skinai_data/scripts/)
    output_path = Path(__file__).parent / "manifest_zips.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    # 통계 집계
    split_counts = df.groupby("split").size().to_dict()
    train_n = split_counts.get("train", 0)
    val_n = split_counts.get("val", 0)
    test_n = split_counts.get("test", 0)

    print()
    print(f"✅ {MANIFEST_FILENAME} 생성 완료")
    print(f"총 {len(df)}개 ZIP (train: {train_n} / val: {val_n} / test: {test_n})")
    print(f"저장 경로: {output_path.resolve()}")


if __name__ == "__main__":
    main()
