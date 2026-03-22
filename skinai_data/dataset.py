"""AI Hub 08-14 안면부 피부질환 PyTorch Dataset."""

# ── 표준 라이브러리 ──────────────────────────────────────────────
import io
import logging
import os
from pathlib import Path

# ── 서드파티 ─────────────────────────────────────────────────────
import pandas as pd
import torch
from PIL import Image, UnidentifiedImageError
from torch.utils.data import Dataset
from torchvision import transforms
from googleapiclient.errors import HttpError

# ── 로컬 ─────────────────────────────────────────────────────────
from .auth import get_drive_service

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
IDX_TO_CLASS = {v: k for k, v in CLASS_MAP.items()}

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

_DEFAULT_CACHE_ROOT = str(Path.home() / ".cache" / "skinai_data")
CACHE_DIR = Path(os.environ.get("SKINAI_CACHE_DIR", _DEFAULT_CACHE_ROOT))
IMAGE_CACHE_DIR = CACHE_DIR / "images"
CORRUPT_LOG_PATH = CACHE_DIR / "corrupt_files.txt"

META_FIELDS = ("gender", "age_range", "severity", "lesion_type")


# ── 헬퍼 ─────────────────────────────────────────────────────────

def get_default_transforms(split: str, image_size: int = 256, crop_size: int = 224):
    """split에 따른 기본 transform 반환.

    Args:
        split: 'train', 'val', 'test'
        image_size: Resize 목표 크기
        crop_size: Crop 목표 크기

    Returns:
        torchvision.transforms.Compose
    """
    if split == "train":
        return transforms.Compose([
            transforms.Resize(image_size),
            transforms.RandomCrop(crop_size),
            transforms.RandomHorizontalFlip(0.5),
            transforms.ColorJitter(0.2, 0.2, 0.2, 0.1),
            transforms.RandomRotation(15),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ])
    return transforms.Compose([
        transforms.Resize(image_size),
        transforms.CenterCrop(crop_size),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


def _record_corrupt(filename: str) -> None:
    """손상 파일명을 corrupt_files.txt에 기록.

    Args:
        filename: 손상된 파일명
    """
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CORRUPT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(filename + "\n")
    except OSError as e:
        logger.warning(f"corrupt_files.txt 기록 실패: {e}")


# ── 공개 API ─────────────────────────────────────────────────────

class SkinAIDataset(Dataset):
    """AI Hub 08-14 안면부 피부질환 데이터셋.

    Args:
        manifest_df: load_manifest()로 얻은 DataFrame
        split: 'train', 'val', 'test'
        transform: torchvision transform (None이면 기본 transform 사용)
        use_cache: True이면 로컬 이미지 캐시 사용
    """

    def __init__(
        self,
        manifest_df: pd.DataFrame,
        split: str = "train",
        transform=None,
        use_cache: bool = True,
    ):
        self.split = split
        self.use_cache = use_cache
        self.transform = transform or get_default_transforms(split)
        self._service = None

        # 정면(front) + split 필터 — 1차 개발: 정면만 사용
        mask = (manifest_df["split"] == split) & (manifest_df["direction"] == "front")
        self.df = manifest_df[mask].reset_index(drop=True)

        if len(self.df) == 0:
            logger.warning(f"split='{split}', direction='front' 데이터가 없습니다.")

        IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def service(self):
        """Drive 서비스 지연 초기화 — 필요한 시점에만 인증 실행."""
        if self._service is None:
            self._service = get_drive_service()
        return self._service

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int):
        row = self.df.iloc[idx]
        file_id = row["file_id"]
        filename = row["filename"]
        label = int(row["class_idx"])

        image = self._load_image(file_id, filename)
        if image is None:
            return self._get_fallback(idx)

        if self.transform:
            image = self.transform(image)

        meta = {field: row.get(field, "") for field in META_FIELDS}
        meta["class_name"] = row["class_name"]

        return image, label, meta

    def _load_image(self, file_id: str, filename: str) -> "Image.Image | None":
        """이미지를 로컬 캐시 또는 Drive에서 로드.

        로드 순서:
            1. 로컬 캐시 히트 → PIL 반환
            2. 캐시 미스 → Drive 스트리밍 fetch → 캐시 저장 → PIL 반환

        Args:
            file_id: Drive 파일 ID
            filename: 로컬 캐시 파일명

        Returns:
            PIL.Image.Image | None: 로드 성공 시 RGB 이미지, 실패 시 None
        """
        cache_path = IMAGE_CACHE_DIR / filename

        if self.use_cache and cache_path.exists():
            try:
                return Image.open(cache_path).convert("RGB")
            except (OSError, UnidentifiedImageError):
                # 캐시 손상 — 삭제 후 Drive 재다운로드
                logger.warning(f"캐시 파일 손상, 재다운로드: {filename}")
                cache_path.unlink(missing_ok=True)
                _record_corrupt(filename)

        try:
            request = self.service.files().get_media(fileId=file_id)
            content = request.execute()
            image = Image.open(io.BytesIO(content)).convert("RGB")

            if self.use_cache:
                image.save(cache_path)

            return image
        except (HttpError, OSError, UnidentifiedImageError) as e:
            logger.error(f"이미지 로드 실패: filename={filename}, error={e}")
            _record_corrupt(filename)
            return None

    def _get_fallback(self, idx: int):
        """이미지 로드 실패 시 인접 유효 샘플 반환.

        Args:
            idx: 실패한 인덱스

        Returns:
            tuple: (image_tensor, label, meta_dict) — 유효한 샘플 또는 더미
        """
        for offset in range(1, min(10, len(self.df))):
            next_idx = (idx + offset) % len(self.df)
            row = self.df.iloc[next_idx]
            try:
                image = self._load_image(row["file_id"], row["filename"])
                if image is None:
                    continue
                if self.transform:
                    image = self.transform(image)
                meta = {field: row.get(field, "") for field in META_FIELDS}
                meta["class_name"] = row["class_name"]
                return image, int(row["class_idx"]), meta
            except (OSError, UnidentifiedImageError):
                continue

        # 모든 fallback 실패 시 더미 반환 (배치 크기 유지용)
        dummy = torch.zeros(3, 224, 224)
        empty_meta = {field: "" for field in META_FIELDS}
        empty_meta["class_name"] = ""
        return dummy, 0, empty_meta
