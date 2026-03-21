"""
SCIN 피부 질환 분류 - ResNet50 모델

ResNet50 기반 전이 학습 모델
"""

import torch.nn as nn
from torchvision import models


class ResNet50Classifier(nn.Module):
    """ResNet50 기반 다중 라벨 분류기"""

    def __init__(self, num_classes, pretrained=True, dropout=0.5):
        """
        Args:
            num_classes: 출력 클래스 수
            pretrained: ImageNet pretrained 가중치 사용 여부
            dropout: Dropout 비율
        """
        super(ResNet50Classifier, self).__init__()

        # ResNet50 백본
        self.backbone = models.resnet50(pretrained=pretrained)

        # 마지막 FC 레이어 교체
        num_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(num_features, num_classes)
        )

    def forward(self, x):
        """
        Args:
            x: (B, 3, H, W) 이미지 텐서

        Returns:
            (B, num_classes) 로짓
        """
        return self.backbone(x)
