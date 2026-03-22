"""AI Hub 08-14 데이터를 Google Drive에 업로드하고 manifest.csv를 생성하는 스크립트.

사용법:
    python scripts/upload_to_drive.py \
        --local_dir data/raw/aihub_08_14 \
        --drive_folder_name SkinAI-Dataset \
        --resume
"""

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from skinai_data.auth import get_drive_service

CLASS_MAP = {
    "건선": 0, "아토피피부염": 1, "여드름": 2,
    "주사": 3, "지루피부염": 4, "정상": 5,
}

SPLIT_MAP = {
    "1.Training": "train",
    "2.Validation": "val",
    "3.Test": "test",
}

DIRECTION_MAP = {
    "정면": "front",
    "측면": "side",
}


def find_or_create_folder(service, name: str, parent_id: str | None = None) -> str:
    """Drive 폴더 찾기 또는 생성, 폴더 ID 반환."""
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_file(service, local_path: Path, parent_id: str, existing_files: dict) -> str | None:
    """파일 업로드. 이미 존재하면 skip. 업로드된 file_id 반환."""
    filename = local_path.name

    if filename in existing_files:
        return existing_files[filename]

    from googleapiclient.http import MediaFileUpload

    metadata = {"name": filename, "parents": [parent_id]}
    media = MediaFileUpload(str(local_path), resumable=True)
    file = service.files().create(body=metadata, media_body=media, fields="id").execute()
    return file["id"]


def list_existing_files(service, folder_id: str) -> dict:
    """폴더 내 기존 파일 목록 {filename: file_id}."""
    files = {}
    page_token = None
    while True:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name)",
            pageToken=page_token,
        ).execute()
        for f in results.get("files", []):
            files[f["name"]] = f["id"]
        page_token = results.get("nextPageToken")
        if not page_token:
            break
    return files


def parse_json_meta(json_path: Path) -> dict:
    """JSON 라벨링 파일에서 임상 메타데이터 추출."""
    meta = {
        "gender": "",
        "age_range": "",
        "race": "",
        "severity": "",
        "lesion_type": "",
    }

    if not json_path.exists():
        return meta

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        params = data.get("generated_parameters", {})
        meta["gender"] = params.get("gender", "")
        meta["age_range"] = params.get("age_range", "")
        meta["race"] = params.get("race", "")

        diag_info = data.get("diagnosis_info", {})
        easi = diag_info.get("easi_score", {})
        meta["severity"] = easi.get("iga_grade", "")

        bbox = data.get("bbox", {})
        lesions = bbox.get("lesions", [])
        if lesions:
            meta["lesion_type"] = lesions[0].get("inflammatory", "")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  [경고] JSON 파싱 실패: {json_path} - {e}")

    return meta


def detect_direction(filename: str, dir_name: str) -> str:
    """파일명/디렉토리명에서 촬영 방향 추출."""
    if "P2" in filename:
        return "front"
    if "P1" in filename:
        return "side"
    return DIRECTION_MAP.get(dir_name, "unknown")


def collect_files(local_dir: Path) -> list[dict]:
    """로컬 데이터 디렉토리를 순회하여 업로드 대상 파일 목록 생성."""
    records = []

    for split_dir in sorted(local_dir.iterdir()):
        if not split_dir.is_dir():
            continue

        split_name = None
        for key, val in SPLIT_MAP.items():
            if key in split_dir.name:
                split_name = val
                break
        if not split_name:
            continue

        source_dir = split_dir / "1.원천데이터"
        label_dir = split_dir / "2.라벨링데이터"

        if not source_dir.exists():
            continue

        for class_dir in sorted(source_dir.iterdir()):
            if not class_dir.is_dir():
                continue

            class_name = class_dir.name
            if class_name not in CLASS_MAP:
                print(f"  [경고] 알 수 없는 클래스: {class_name}, 건너뜀")
                continue

            for direction_dir in sorted(class_dir.iterdir()):
                if not direction_dir.is_dir():
                    continue

                direction_kr = direction_dir.name

                for png_path in sorted(direction_dir.glob("*.png")):
                    json_name = png_path.stem + ".json"
                    json_path = label_dir / class_name / direction_kr / json_name

                    meta = parse_json_meta(json_path)
                    direction = detect_direction(png_path.name, direction_kr)

                    records.append({
                        "local_path": str(png_path),
                        "filename": png_path.name,
                        "storage_path": f"{split_name}/{class_name}/{direction_kr}/{png_path.name}",
                        "class_name": class_name,
                        "class_idx": CLASS_MAP[class_name],
                        "split": split_name,
                        "direction": direction,
                        **meta,
                    })

    return records


def main():
    parser = argparse.ArgumentParser(description="AI Hub 08-14 데이터 → Google Drive 업로드")
    parser.add_argument("--local_dir", required=True, help="로컬 데이터 경로")
    parser.add_argument("--drive_folder_name", default="SkinAI-Dataset", help="Drive 루트 폴더명")
    parser.add_argument("--resume", action="store_true", help="이어서 업로드")
    args = parser.parse_args()

    local_dir = Path(args.local_dir)
    if not local_dir.exists():
        print(f"[오류] 경로가 존재하지 않습니다: {local_dir}")
        sys.exit(1)

    print("[1/4] 파일 목록 수집 중...")
    records = collect_files(local_dir)
    print(f"  → {len(records)}개 파일 발견")

    if not records:
        print("[오류] 업로드할 파일이 없습니다.")
        sys.exit(1)

    print("[2/4] Google Drive 인증...")
    service = get_drive_service()

    root_folder_id = os.environ.get("SKINAI_DRIVE_FOLDER_ID")
    if not root_folder_id:
        print("[3/4] Drive 폴더 생성 중...")
        root_folder_id = find_or_create_folder(service, args.drive_folder_name)
        print(f"  → SKINAI_DRIVE_FOLDER_ID={root_folder_id}")
    else:
        print(f"[3/4] 기존 Drive 폴더 사용: {root_folder_id}")

    aihub_folder_id = find_or_create_folder(service, "aihub_08_14", root_folder_id)

    folder_cache = {}
    manifest_records = []

    print("[4/4] 업로드 중...")
    for record in tqdm(records, desc="업로드", unit="파일"):
        storage_path = record["storage_path"]
        parts = storage_path.split("/")

        parent_id = aihub_folder_id
        for part in parts[:-1]:
            cache_key = f"{parent_id}/{part}"
            if cache_key not in folder_cache:
                folder_cache[cache_key] = find_or_create_folder(service, part, parent_id)
            parent_id = folder_cache[cache_key]

        existing = list_existing_files(service, parent_id) if args.resume else {}
        file_id = upload_file(service, Path(record["local_path"]), parent_id, existing)

        if file_id:
            manifest_records.append({
                "file_id": file_id,
                "filename": record["filename"],
                "storage_path": record["storage_path"],
                "class_name": record["class_name"],
                "class_idx": record["class_idx"],
                "split": record["split"],
                "direction": record["direction"],
                "gender": record["gender"],
                "age_range": record["age_range"],
                "race": record["race"],
                "severity": record["severity"],
                "lesion_type": record["lesion_type"],
            })

    print("\n[완료] manifest.csv 생성 중...")
    manifest_df = pd.DataFrame(manifest_records)

    local_manifest = local_dir.parent / "manifest.csv"
    manifest_df.to_csv(local_manifest, index=False)
    print(f"  → 로컬 저장: {local_manifest}")

    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(str(local_manifest), mimetype="text/csv")
    manifest_file = service.files().create(
        body={"name": "manifest.csv", "parents": [root_folder_id]},
        media_body=media,
        fields="id",
    ).execute()

    manifest_file_id = manifest_file["id"]
    print(f"  → Drive 업로드 완료")
    print(f"\n{'='*60}")
    print(f"  MANIFEST_FILE_ID={manifest_file_id}")
    print(f"  위 값을 환경변수에 설정하세요:")
    print(f"  export MANIFEST_FILE_ID=\"{manifest_file_id}\"")
    print(f"{'='*60}")
    print(f"\n총 {len(manifest_records)}개 파일 업로드 완료.")


if __name__ == "__main__":
    main()
