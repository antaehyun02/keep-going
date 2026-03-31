"""AI Hub 08-14 학습 설정.

AI Hub 08-14 활용 가이드라인(서울대학교 산학협력단, 2025.01) 공식 학습 조건 기반.
"""

from dataclasses import dataclass, field


@dataclass
class ClassifyConfig:
    """분류 모델 학습 설정.

    공식 벤치마크: DenseNet121 Top-1 Accuracy 85.17% (목표 80%)
    """

    # ── 데이터 ──────────────────────────────────────────────────
    data_dir: str = "data/processed"
    num_classes: int = 6
    class_names: list = field(default_factory=lambda: [
        "건선", "아토피피부염", "여드름", "주사", "지루피부염", "정상"
    ])

    # ── 모델 ────────────────────────────────────────────────────
    backbone: str = "densenet121"
    pretrained: bool = True

    # ── 학습 조건 (가이드라인 공식 값) ────────────────────────────
    image_size: int = 256
    crop_size: int = 224
    batch_size: int = 32
    num_workers: int = 4
    learning_rate: float = 0.001
    weight_decay: float = 1e-4
    dropout_rate: float = 0.5
    num_epochs: int = 30
    optimizer: str = "adam"

    # ── 스케줄러 ────────────────────────────────────────────────
    scheduler: str = "cosine"
    warmup_epochs: int = 3

    # ── 저장 ────────────────────────────────────────────────────
    checkpoint_dir: str = "ai/checkpoints/aihub"
    best_metric: str = "val_top1_acc"
    early_stopping_patience: int = 10
    save_every_n_epochs: int = 5

    # ── 로깅 ────────────────────────────────────────────────────
    log_dir: str = "ai/logs/aihub"
    experiment_name: str = "densenet121_baseline"

    # ── 성능 목표 ────────────────────────────────────────────────
    target_top1_acc: float = 0.80
    stretch_top1_acc: float = 0.85


@dataclass
class SegmentConfig:
    """아토피피부염 병변 경계 검출 (DeeplabV3+) 설정.

    공식 벤치마크: IoU 0.9210 (목표 0.70)
    """

    data_dir: str = "data/processed"
    target_class: str = "아토피피부염"
    num_epochs: int = 30
    batch_size: int = 32
    learning_rate: float = 0.001
    weight_decay: float = 1e-4
    image_size: int = 256
    crop_size: int = 224
    num_workers: int = 4
    checkpoint_dir: str = "ai/checkpoints/aihub_seg"
    log_dir: str = "ai/logs/aihub_seg"
    target_iou: float = 0.70
    stretch_iou: float = 0.85
