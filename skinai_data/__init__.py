"""skinai-data: AI Hub 08-14 안면부 피부질환 데이터셋 PyTorch DataLoader 패키지."""

from .dataset import SkinAIDataset, CLASS_MAP, IDX_TO_CLASS
from .loader import get_dataloader, prefetch
from .manifest import load_manifest

__version__ = "0.1.0"

__all__ = [
    "SkinAIDataset",
    "CLASS_MAP",
    "IDX_TO_CLASS",
    "get_dataloader",
    "prefetch",
    "load_manifest",
]
