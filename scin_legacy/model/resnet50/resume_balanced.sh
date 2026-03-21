#!/bin/bash

# Balanced Focal Loss 학습 재개 (Early stopping patience 증가)
# Epoch 14에서 중단된 학습을 patience=20으로 재개

echo "========================================"
echo "ResNet50 학습 재개 - Balanced Focal Loss"
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

# 체크포인트 디렉토리 (기존과 동일)
CHECKPOINT_DIR="../../checkpoints_balanced"
RESUME_CHECKPOINT="$CHECKPOINT_DIR/checkpoint_latest.pth"

# 체크포인트 확인
if [ ! -f "$RESUME_CHECKPOINT" ]; then
  echo "[ERROR] 재개할 체크포인트가 없습니다: $RESUME_CHECKPOINT"
  echo "[INFO] 먼저 ./retrain_balanced.sh를 실행해주세요"
  exit 1
fi

echo "[INFO] 재개할 체크포인트: $RESUME_CHECKPOINT"
echo ""

# 학습 재개
echo "========================================"
echo "학습 재개 시작"
echo "========================================"
echo ""
echo "최적화 설정 (변경사항):"
echo "  - 손실 함수: Focal Loss (alpha=0.5, gamma=1.5)"
echo "  - Learning Rate: 0.00005"
echo "  - Batch Size: 32"
echo "  - Dropout: 0.3"
echo "  - Weight Decay: 1e-4"
echo "  - Epochs: 80 (현재 Epoch 14에서 재개)"
echo "  - Patience: 20 (증가: 10 → 20)"
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
  --patience 20 \
  --num_workers 0 \
  --augment \
  --resume "$RESUME_CHECKPOINT"

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
echo "     - Balanced (새로): ./evaluation_results_balanced"
echo ""
