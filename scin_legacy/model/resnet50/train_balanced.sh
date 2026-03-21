#!/bin/bash

# Focal Loss 하이퍼파라미터 최적화 - 균형잡힌 학습
# 문제: 기존 alpha=0.25, gamma=2.0이 major class에 과적합 유발
# 해결: alpha 증가 (minor class 보호), gamma 감소 (쉬운 샘플 무시 완화)

echo "========================================"
echo "ResNet50 재학습 - Balanced Focal Loss"
echo "========================================"
echo ""

# 환경 변수 설정 (Apple Silicon 최적화)
export PYTORCH_ENABLE_MPS_FALLBACK=1

# 작업 디렉토리
cd "$(dirname "$0")"

# Python 경로 확인
echo "[INFO] Python: $(which python3)"
echo "[INFO] PyTorch 버전: $(python3 -c 'import torch; print(torch.__version__)')"
echo ""

# 체크포인트 디렉토리 생성
CHECKPOINT_DIR="../../checkpoints_balanced"
mkdir -p "$CHECKPOINT_DIR"

echo "[INFO] 체크포인트 디렉토리: $CHECKPOINT_DIR"
echo ""

# 학습 시작
echo "========================================"
echo "학습 시작"
echo "========================================"
echo ""
echo "최적화 설정 (변경사항):"
echo "  - 손실 함수: Focal Loss (alpha=0.5 ↑, gamma=1.5 ↓)"
echo "  - alpha 증가: minor class 보호 강화"
echo "  - gamma 감소: major class 과적합 방지"
echo "  - Learning Rate: 0.00005 (더 낮게)"
echo "  - Batch Size: 32 (더 크게)"
echo "  - Dropout: 0.3 (낮춤)"
echo "  - Weight Decay: 1e-4 (약하게)"
echo "  - Epochs: 80"
echo "  - Patience: 10"
echo ""

python3 train.py \
  --data_dir ../../data/scin_processed \
  --image_root ../../data/scin_dataset \
  --checkpoint_dir "$CHECKPOINT_DIR" \
  --log_dir ./logs_balanced \
  --loss_type focal \
  --focal_alpha 0.5 \
  --focal_gamma 1.5 \
  --batch_size 32 \
  --num_epochs 80 \
  --lr 0.00005 \
  --weight_decay 1e-4 \
  --dropout 0.3 \
  --patience 10 \
  --num_workers 0 \
  --augment

echo ""
echo "========================================"
echo "학습 완료!"
echo "========================================"
echo ""
echo "다음 단계:"
echo "  1. 모델 평가:"
echo "     python evaluate.py --checkpoint $CHECKPOINT_DIR/checkpoint_best.pth --output_dir ./evaluation_results_balanced"
echo ""
echo "  2. 기존 모델들과 비교:"
echo "     - 기존: ./evaluation_results_old (F1=0.160)"
echo "     - Focal (실패): ./evaluation_results_focal (F1=0.085)"
echo "     - Balanced (새로): ./evaluation_results_balanced"
echo ""
