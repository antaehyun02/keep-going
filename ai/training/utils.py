"""AI 모델 공통 유틸리티.

DRY 원칙에 따라 여러 학습 스크립트에서 공용으로 사용하는 함수를 모음.
"""

import logging
import os

import torch

logger = logging.getLogger(__name__)


def get_device() -> torch.device:
    """CUDA → MPS → CPU 순서로 사용 가능한 디바이스 자동 선택.

    환경변수 DEVICE가 'auto'가 아닌 경우 강제 지정 가능.

    Returns:
        torch.device: 선택된 디바이스
    """
    device_env = os.environ.get("DEVICE", "auto")

    if device_env != "auto":
        logger.info(f"[INFO] 디바이스 강제 지정: {device_env}")
        return torch.device(device_env)

    if torch.cuda.is_available():
        logger.info("[INFO] CUDA 사용")
        return torch.device("cuda")

    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        # MPS는 멀티프로세스 DataLoader와 호환되지 않으므로 num_workers=0 필요
        logger.info("[INFO] MPS (Apple Silicon) 사용")
        return torch.device("mps")

    logger.info("[INFO] CPU 사용")
    return torch.device("cpu")


def resolve_num_workers(device: torch.device, requested: int = 4) -> int:
    """MPS 환경에서는 num_workers=0 강제.

    MPS는 멀티프로세스 DataLoader 지원 불가로 인해
    num_workers > 0 시 데드락이 발생할 수 있음.

    Args:
        device: 현재 사용 디바이스
        requested: 요청한 워커 수

    Returns:
        int: 실제 사용할 워커 수
    """
    if device.type == "mps":
        return 0
    return requested


def topk_accuracy(output: torch.Tensor, target: torch.Tensor, topk: tuple = (1, 3)) -> list:
    """Top-k Accuracy 계산.

    Args:
        output: 모델 출력 (logits), shape (N, C)
        target: 정답 라벨, shape (N,)
        topk: 계산할 k 값 튜플

    Returns:
        list[Tensor]: 각 k에 대한 accuracy 스칼라 텐서 목록
    """
    with torch.no_grad():
        maxk = max(topk)
        batch_size = target.size(0)
        _, pred = output.topk(maxk, dim=1, largest=True, sorted=True)
        pred = pred.t()
        correct = pred.eq(target.view(1, -1).expand_as(pred))

        results = []
        for k in topk:
            correct_k = correct[:k].reshape(-1).float().sum(0)
            results.append(correct_k / batch_size)
        return results
