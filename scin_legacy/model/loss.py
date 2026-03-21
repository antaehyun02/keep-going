"""
손실 함수 (Loss Functions)

Focal Loss 구현 - Multi-label Classification용
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class FocalLoss(nn.Module):
    """
    Focal Loss for Multi-label Classification

    논문: "Focal Loss for Dense Object Detection" (Lin et al., 2017)

    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)

    Args:
        alpha: Weighting factor (0~1), default=0.25
        gamma: Focusing parameter (>=0), default=2.0
        reduction: 'none' | 'mean' | 'sum'

    장점:
        1. 어려운 샘플(misclassified)에 집중
        2. 쉬운 샘플(well-classified)의 가중치 자동 감소
        3. Class imbalance 문제 해결
        4. BCEWithLogitsLoss보다 높은 성능
    """

    def __init__(self, alpha=0.25, gamma=2.0, reduction='mean'):
        super(FocalLoss, self).__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, inputs, targets):
        """
        Args:
            inputs: (N, C) logits (sigmoid 적용 전)
            targets: (N, C) binary labels (0 or 1)

        Returns:
            loss: scalar tensor
        """
        # BCE loss 계산
        bce_loss = F.binary_cross_entropy_with_logits(
            inputs, targets, reduction='none'
        )

        # Probability 계산
        probs = torch.sigmoid(inputs)

        # p_t 계산 (target이 1이면 p, 0이면 1-p)
        p_t = probs * targets + (1 - probs) * (1 - targets)

        # Focal weight 계산: (1 - p_t)^gamma
        focal_weight = (1 - p_t) ** self.gamma

        # Alpha balancing
        alpha_t = self.alpha * targets + (1 - self.alpha) * (1 - targets)

        # Focal Loss = alpha * focal_weight * BCE
        focal_loss = alpha_t * focal_weight * bce_loss

        # Reduction
        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        else:
            return focal_loss


class AsymmetricLoss(nn.Module):
    """
    Asymmetric Loss for Multi-label Classification

    논문: "Asymmetric Loss For Multi-Label Classification" (Ridnik et al., 2021)

    긍정/부정 샘플에 다른 gamma 적용

    Args:
        gamma_pos: Positive samples focusing parameter, default=0
        gamma_neg: Negative samples focusing parameter, default=4
        clip: Clipping value for probabilities, default=0.05
        reduction: 'none' | 'mean' | 'sum'
    """

    def __init__(self, gamma_pos=0, gamma_neg=4, clip=0.05, reduction='mean'):
        super(AsymmetricLoss, self).__init__()
        self.gamma_pos = gamma_pos
        self.gamma_neg = gamma_neg
        self.clip = clip
        self.reduction = reduction

    def forward(self, inputs, targets):
        """
        Args:
            inputs: (N, C) logits
            targets: (N, C) binary labels

        Returns:
            loss: scalar tensor
        """
        # Sigmoid
        probs = torch.sigmoid(inputs)

        # Probability clipping
        probs = torch.clamp(probs, min=self.clip, max=1 - self.clip)

        # Positive loss
        pos_loss = targets * torch.log(probs)
        pos_loss = pos_loss * ((1 - probs) ** self.gamma_pos)

        # Negative loss
        neg_loss = (1 - targets) * torch.log(1 - probs)
        neg_loss = neg_loss * (probs ** self.gamma_neg)

        # Total loss
        loss = -(pos_loss + neg_loss)

        # Reduction
        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'sum':
            return loss.sum()
        else:
            return loss


class WeightedBCEWithLogitsLoss(nn.Module):
    """
    Weighted BCE Loss with class weights

    기존 BCEWithLogitsLoss + pos_weight 조합의 개선 버전
    """

    def __init__(self, pos_weight=None, reduction='mean'):
        super(WeightedBCEWithLogitsLoss, self).__init__()
        self.pos_weight = pos_weight
        self.reduction = reduction

    def forward(self, inputs, targets):
        """
        Args:
            inputs: (N, C) logits
            targets: (N, C) binary labels

        Returns:
            loss: scalar tensor
        """
        loss = F.binary_cross_entropy_with_logits(
            inputs, targets,
            pos_weight=self.pos_weight,
            reduction=self.reduction
        )
        return loss


def get_loss_function(loss_type='focal', **kwargs):
    """
    손실 함수 팩토리 함수

    Args:
        loss_type: 'focal' | 'asymmetric' | 'bce'
        **kwargs: 손실 함수 파라미터

    Returns:
        loss_fn: 손실 함수 인스턴스
    """
    if loss_type == 'focal':
        alpha = kwargs.get('alpha', 0.25)
        gamma = kwargs.get('gamma', 2.0)
        return FocalLoss(alpha=alpha, gamma=gamma)

    elif loss_type == 'asymmetric':
        gamma_pos = kwargs.get('gamma_pos', 0)
        gamma_neg = kwargs.get('gamma_neg', 4)
        clip = kwargs.get('clip', 0.05)
        return AsymmetricLoss(gamma_pos=gamma_pos, gamma_neg=gamma_neg, clip=clip)

    elif loss_type == 'bce':
        pos_weight = kwargs.get('pos_weight', None)
        return WeightedBCEWithLogitsLoss(pos_weight=pos_weight)

    else:
        raise ValueError(f"Unknown loss type: {loss_type}")
