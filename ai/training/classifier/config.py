"""AI Hub 08-14 학습 설정.

AI Hub 08-14 활용 가이드라인(서울대학교 산학협력단, 2025.01) 공식 학습 조건 기반.
"""

from dataclasses import dataclass, field

# backbone별 기본 해상도 — 공식 입력 크기 기준
_BACKBONE_DEFAULTS = {
    "densenet121": {"image_size": 256, "crop_size": 224, "batch_size": 32, "learning_rate": 0.001, "warmup_epochs": 3},
    "efficientnet_b3": {"image_size": 320, "crop_size": 300, "batch_size": 16, "learning_rate": 0.0005, "warmup_epochs": 5},
}


@dataclass
class ClassifyConfig:
    """분류 모델 학습 설정.

    공식 벤치마크: DenseNet121 Top-1 Accuracy 85.17% (목표 80%)
    backbone을 변경하면 apply_backbone_defaults()로 해상도·배치 크기 자동 분기.
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

    # ── 학습 조건 (가이드라인 공식 값 — DenseNet121 기준) ──────────
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

    def apply_backbone_defaults(self) -> None:
        """backbone에 따라 image_size, crop_size, batch_size, lr, warmup을 자동 설정.

        CLI에서 명시적으로 값을 지정한 경우 그 값이 우선하므로,
        이 메서드는 CLI 파싱 전에 호출해야 한다.
        """
        defaults = _BACKBONE_DEFAULTS.get(self.backbone)
        if defaults is None:
            return
        for key, value in defaults.items():
            setattr(self, key, value)


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
