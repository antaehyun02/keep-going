"""원본 1,024px ZIP을 지정 크기 JPEG ZIP으로 사전 변환.

이슈 3 (1,024px 전체 로드 후 즉시 축소)과 이슈 2 (ZIP 반복 개방)의 장기 해결책.
원본 9.78GB → 약 2GB (256px JPEG Q85 기준).
DataLoader 로딩 속도 3~5배 향상 예상.

변환 후 aihub_preprocessor 를 --data_root data/dataset_256 으로 재실행하면
변환 이미지를 가리키는 train.csv / val.csv 가 새로 생성됨.

사용법:
    python -m ai.preprocessing.resize_zips
    python -m ai.preprocessing.resize_zips --src data/dataset_14 --dst data/dataset_256
    python -m ai.preprocessing.resize_zips --size 320 --quality 90   # EfficientNet-B3용
    python -m ai.preprocessing.resize_zips --resume                  # 이미 존재하는 ZIP 건너뜀
"""

# ── 표준 라이브러리 ──────────────────────────────────────────────
import argparse
import io
import logging
import shutil
import zipfile
from pathlib import Path

# ── 서드파티 ─────────────────────────────────────────────────────
from PIL import Image
from tqdm import tqdm

logger = logging.getLogger(__name__)

# ── 상수 ─────────────────────────────────────────────────────────
RAW_SUBDIR = "01_raw"
LABEL_SUBDIR = "02_label"
SPLIT_DIRS = ["Training", "Validation"]


# ── 헬퍼 ─────────────────────────────────────────────────────────

def _encode_jpeg(img: Image.Image, size: int, quality: int) -> bytes:
    """PIL 이미지를 지정 크기 JPEG 바이트로 인코딩.

    Args:
        img: PIL RGB 이미지
        size: 목표 크기 (px) — 정방형 리사이즈
        quality: JPEG 품질 (0~95)

    Returns:
        bytes: JPEG 인코딩 바이트
    """
    img_resized = img.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img_resized.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def _convert_raw_zip(
    src_zip: Path,
    dst_zip: Path,
    size: int,
    quality: int,
    resume: bool,
) -> int:
    """원천 ZIP 1개를 리사이즈 JPEG ZIP으로 변환.

    ZIP 내부 파일명은 `.png` → `.jpg` 로 변경해 저장.
    (aihub_preprocessor 는 .jpg 확장자도 수집함)

    Args:
        src_zip: 원본 원천 ZIP 경로
        dst_zip: 출력 ZIP 경로
        size: 목표 이미지 크기
        quality: JPEG 품질
        resume: True 이면 dst_zip 존재 시 건너뜀

    Returns:
        int: 변환된 이미지 수 (건너뛴 경우 0)
    """
    if resume and dst_zip.exists():
        logger.debug(f"[SKIP] {dst_zip.name}")
        return 0

    dst_zip.parent.mkdir(parents=True, exist_ok=True)
    count = 0

    try:
        with (
            zipfile.ZipFile(src_zip, "r") as zf_in,
            zipfile.ZipFile(dst_zip, "w", zipfile.ZIP_STORED) as zf_out,
        ):
            img_names = [
                n for n in zf_in.namelist()
                if n.lower().endswith(".png") or n.lower().endswith(".jpg")
            ]

            for raw_name in img_names:
                # leading slash 제거 후 확장자를 .jpg 로 교체
                clean_stem = Path(raw_name.lstrip("/")).stem
                out_name = clean_stem + ".jpg"

                try:
                    with zf_in.open(raw_name) as f:
                        img = Image.open(io.BytesIO(f.read())).convert("RGB")
                    jpeg_bytes = _encode_jpeg(img, size, quality)
                    zf_out.writestr(out_name, jpeg_bytes)
                    count += 1
                except Exception as e:
                    logger.warning(f"[WARN] 변환 실패: {raw_name} — {e}")

    except zipfile.BadZipFile as e:
        logger.error(f"[ERROR] ZIP 손상: {src_zip.name} — {e}")
        if dst_zip.exists():
            dst_zip.unlink()
        return 0

    logger.info(f"[OK] {dst_zip.name}: {count}장 변환")
    return count


def _copy_label_zip(src_zip: Path, dst_zip: Path, resume: bool) -> None:
    """라벨 ZIP (JSON만 포함)을 변환 없이 복사.

    Args:
        src_zip: 원본 라벨 ZIP
        dst_zip: 출력 경로
        resume: True 이면 dst_zip 존재 시 건너뜀
    """
    if resume and dst_zip.exists():
        return
    dst_zip.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_zip, dst_zip)
    logger.debug(f"[COPY] {dst_zip.name}")


# ── 메인 함수 ─────────────────────────────────────────────────────

def run(src_root: Path, dst_root: Path, size: int, quality: int, resume: bool) -> None:
    """전체 변환 파이프라인 실행.

    dataset_14/ 구조를 그대로 유지하면서 원천 이미지만 리사이즈 변환.
    라벨 ZIP(JSON)은 변경 없이 복사.

    Args:
        src_root: 원본 dataset_14/ 경로
        dst_root: 출력 경로 (dataset_256/ 등)
        size: 목표 이미지 크기
        quality: JPEG 품질
        resume: 이미 존재하는 ZIP 건너뜀
    """
    print("=" * 60)
    print(f"ZIP 사전 리사이즈 — {size}px JPEG (quality={quality})")
    print(f"  원본: {src_root.resolve()}")
    print(f"  출력: {dst_root.resolve()}")
    print("=" * 60)

    total_images = 0
    total_zips = 0

    for split_dir in SPLIT_DIRS:
        raw_dir = src_root / split_dir / RAW_SUBDIR
        label_dir = src_root / split_dir / LABEL_SUBDIR

        if not raw_dir.exists():
            logger.warning(f"[WARN] 원천 디렉토리 없음: {raw_dir}")
            continue

        raw_zips = sorted(raw_dir.glob("*.zip"))
        print(f"\n[{split_dir}] 원천 ZIP {len(raw_zips)}개 변환 중...")

        for src_zip in tqdm(raw_zips, unit="ZIP"):
            dst_zip = dst_root / split_dir / RAW_SUBDIR / src_zip.name
            count = _convert_raw_zip(src_zip, dst_zip, size, quality, resume)
            total_images += count
            total_zips += 1

        # 라벨 ZIP은 JSON만 포함 — 복사만
        if label_dir.exists():
            label_zips = sorted(label_dir.glob("*.zip"))
            print(f"  라벨 ZIP {len(label_zips)}개 복사 중...")
            for src_zip in tqdm(label_zips, unit="ZIP", leave=False):
                dst_zip = dst_root / split_dir / LABEL_SUBDIR / src_zip.name
                _copy_label_zip(src_zip, dst_zip, resume)

    print(f"\n완료: {total_zips}개 ZIP, {total_images}장 변환")
    print(f"\n다음 단계 — 전처리 재실행:")
    print(f"  python -m ai.preprocessing.aihub_preprocessor --data_root {dst_root}")


# ── 진입점 ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="1,024px 원천 ZIP → 지정 크기 JPEG ZIP 변환")
    parser.add_argument("--src", default="data/dataset_14", help="원본 dataset_14/ 경로")
    parser.add_argument("--dst", default="data/dataset_256", help="출력 경로 (기본: data/dataset_256)")
    parser.add_argument("--size", type=int, default=256, help="목표 이미지 크기 px (기본: 256)")
    parser.add_argument("--quality", type=int, default=85, help="JPEG 품질 0-95 (기본: 85)")
    parser.add_argument("--resume", action="store_true", help="이미 존재하는 ZIP 건너뜀")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run(
        src_root=Path(args.src),
        dst_root=Path(args.dst),
        size=args.size,
        quality=args.quality,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
