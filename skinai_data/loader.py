"""DataLoader 팩토리 및 프리페치 유틸리티."""

# ── 표준 라이브러리 ──────────────────────────────────────────────
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

# ── 서드파티 ─────────────────────────────────────────────────────
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

# ── 로컬 ─────────────────────────────────────────────────────────
from .manifest import load_manifest
from .dataset import SkinAIDataset

logger = logging.getLogger(__name__)


# ── 헬퍼 ─────────────────────────────────────────────────────────

def _meta_collate_fn(batch):
    """(image, label, meta) 배치를 텐서 + dict 형태로 변환.

    Args:
        batch: list of (image_tensor, label_int, meta_dict)

    Returns:
        tuple: (images_tensor, labels_tensor, meta_dict_of_lists)
    """
    images = torch.stack([item[0] for item in batch])
    labels = torch.tensor([item[1] for item in batch])
    meta_keys = batch[0][2].keys()
    meta = {key: [item[2][key] for item in batch] for key in meta_keys}
    return images, labels, meta


# ── 공개 API ─────────────────────────────────────────────────────

def get_dataloader(
    split: str,
    batch_size: int = 32,
    num_workers: int = 4,
    transform=None,
    use_cache: bool = True,
    **kwargs,
) -> DataLoader:
    """split에 대한 DataLoader 반환.

    Args:
        split: 'train', 'val', 'test'
        batch_size: 배치 크기
        num_workers: 데이터 로딩 워커 수
        transform: 커스텀 transform (None이면 기본값 사용)
        use_cache: 이미지 캐시 사용 여부
        **kwargs: DataLoader 추가 인자

    Returns:
        DataLoader: (images, labels, meta) 튜플을 반환하는 DataLoader
    """
    manifest_df = load_manifest()
    dataset = SkinAIDataset(
        manifest_df=manifest_df,
        split=split,
        transform=transform,
        use_cache=use_cache,
    )

    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=(split == "train"),
        num_workers=num_workers,
        pin_memory=True,
        collate_fn=_meta_collate_fn,
        **kwargs,
    )


def prefetch(split: Optional[str] = None, max_workers: int = 8) -> None:
    """이미지를 백그라운드에서 캐시에 미리 다운로드.

    Args:
        split: 특정 split만 프리페치. None이면 train/val/test 전체.
        max_workers: 다운로드 스레드 수
    """
    manifest_df = load_manifest()

    if split:
        df = manifest_df[
            (manifest_df["split"] == split) & (manifest_df["direction"] == "front")
        ]
    else:
        df = manifest_df[manifest_df["direction"] == "front"]

    # _load_image 접근을 위해 SkinAIDataset 인스턴스 생성 (split은 무관)
    dataset = SkinAIDataset(manifest_df, split=split or "train", use_cache=True)
    rows = [df.iloc[i] for i in range(len(df))]

    def _fetch_one(row):
        # _load_image는 내부에서 모든 예외를 처리하고 None 반환 — 여기서는 row 접근 오류만 처리
        try:
            file_id = row["file_id"]
            filename = row["filename"]
        except KeyError as e:
            logger.warning(f"프리페치 실패: manifest 컬럼 누락={e}")
            return False
        dataset._load_image(file_id, filename)
        return True

    logger.info(f"프리페치 시작: {len(rows)}장 (split={split or '전체'})")

    success = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_one, row): row for row in rows}
        for future in tqdm(futures, desc="프리페치", unit="장", total=len(rows)):
            if future.result():
                success += 1
            else:
                failed += 1

    logger.info(f"프리페치 완료: 성공 {success}장, 실패 {failed}장")
