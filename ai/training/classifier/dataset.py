"""AI Hub 08-14 PyTorch Dataset 클래스."""

import logging
from pathlib import Path

import pandas as pd
from PIL import Image
import torch
from torch.utils.data import Dataset
from torchvision import transforms

logger = logging.getLogger(__name__)

CLASS_MAP = {
    "건선": 0, "아토피피부염": 1, "여드름": 2,
    "주사": 3, "지루피부염": 4, "정상": 5,
}
IDX_TO_CLASS = {v: k for k, v in CLASS_MAP.items()}

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def get_transforms(split: str, config=None, task: str = "classify"):
    """split과 task에 따른 transform 반환."""
    image_size = config.image_size if config else 256
    crop_size = config.crop_size if config else 224

    if task == "classify":
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
        else:
            return transforms.Compose([
                transforms.Resize(image_size),
                transforms.CenterCrop(crop_size),
                transforms.ToTensor(),
                transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            ])

    elif task == "segment":
        try:
            import albumentations as A
            from albumentations.pytorch import ToTensorV2
        except ImportError:
            raise ImportError("pip install albumentations 필요")

        if split == "train":
            return A.Compose([
                A.Resize(image_size, image_size),
                A.RandomCrop(crop_size, crop_size),
                A.HorizontalFlip(p=0.5),
                A.ColorJitter(brightness=0.2, contrast=0.2, p=0.5),
                A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
                ToTensorV2(),
            ])
        else:
            return A.Compose([
                A.Resize(image_size, image_size),
                A.CenterCrop(crop_size, crop_size),
                A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
                ToTensorV2(),
            ])

    raise ValueError(f"Unknown task: {task}")


class AihubFacialDataset(Dataset):
    """AI Hub 08-14 안면부 피부질환 분류 Dataset.

    Args:
        csv_path: 전처리된 CSV 경로 (train.csv, val.csv, test.csv)
        transform: torchvision transform
    """

    def __init__(self, csv_path: str, transform=None):
        self.df = pd.read_csv(csv_path)
        self.transform = transform

        if "class_idx" not in self.df.columns:
            self.df["class_idx"] = self.df["class_name"].map(CLASS_MAP)

        logger.info(f"Dataset 로드: {csv_path} ({len(self.df)}건)")

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int):
        row = self.df.iloc[idx]
        label = int(row["class_idx"])

        image_path = row.get("image_path", "")
        if not image_path or not Path(image_path).exists():
            cache_dir = Path.home() / ".cache" / "skinai_data" / "images"
            image_path = str(cache_dir / row["filename"])

        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as e:
            logger.warning(f"이미지 로드 실패 [{image_path}]: {e}")
            return self._get_next_valid(idx)

        if self.transform:
            image = self.transform(image)

        return image, label

    def _get_next_valid(self, idx: int):
        """손상 이미지 건너뛰기."""
        for offset in range(1, min(10, len(self.df))):
            next_idx = (idx + offset) % len(self.df)
            try:
                row = self.df.iloc[next_idx]
                image_path = row.get("image_path", "")
                if not image_path or not Path(image_path).exists():
                    cache_dir = Path.home() / ".cache" / "skinai_data" / "images"
                    image_path = str(cache_dir / row["filename"])

                image = Image.open(image_path).convert("RGB")
                if self.transform:
                    image = self.transform(image)
                return image, int(row["class_idx"])
            except Exception:
                continue

        return torch.zeros(3, 224, 224), 0


class AihubSegDataset(Dataset):
    """아토피피부염 병변 세그멘테이션 Dataset.

    Args:
        csv_path: 전처리된 CSV (아토피만 필터링됨)
        mask_dir: lesion_area 마스크 PNG 디렉토리
        transform: albumentations transform
    """

    def __init__(self, csv_path: str, mask_dir: str, transform=None):
        self.df = pd.read_csv(csv_path)
        self.df = self.df[self.df["class_name"] == "아토피피부염"].reset_index(drop=True)
        self.mask_dir = Path(mask_dir)
        self.transform = transform

        logger.info(f"SegDataset 로드: {len(self.df)}건 (아토피)")

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int):
        row = self.df.iloc[idx]

        image_path = row.get("image_path", "")
        if not image_path or not Path(image_path).exists():
            cache_dir = Path.home() / ".cache" / "skinai_data" / "images"
            image_path = str(cache_dir / row["filename"])

        mask_name = Path(row["filename"]).stem + "_mask.png"
        mask_path = self.mask_dir / mask_name

        try:
            import numpy as np
            image = np.array(Image.open(image_path).convert("RGB"))

            if mask_path.exists():
                mask = np.array(Image.open(mask_path).convert("L"))
                mask = (mask > 127).astype(np.uint8)
            else:
                mask = np.zeros(image.shape[:2], dtype=np.uint8)

            if self.transform:
                transformed = self.transform(image=image, mask=mask)
                image = transformed["image"]
                mask = transformed["mask"]
            else:
                image = torch.from_numpy(image).permute(2, 0, 1).float() / 255.0
                mask = torch.from_numpy(mask)

            return image, mask.long()
        except Exception as e:
            logger.warning(f"세그멘테이션 데이터 로드 실패 [{idx}]: {e}")
            return torch.zeros(3, 224, 224), torch.zeros(224, 224, dtype=torch.long)
