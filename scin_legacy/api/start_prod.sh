#!/bin/bash

# Flask AI 서비스 프로덕션 서버 실행 스크립트 (Gunicorn)

echo "======================================"
echo "Flask AI Service - Production Mode"
echo "======================================"

# 현재 디렉토리 확인
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "작업 디렉토리: $SCRIPT_DIR"
echo ""

# Python 가상환경 확인 및 활성화
if [ -d "venv" ]; then
    echo "[INFO] 가상환경 활성화 중..."
    source venv/bin/activate
else
    echo "[ERROR] 가상환경이 없습니다. 먼저 생성하세요:"
    echo "        python3 -m venv venv"
    echo "        source venv/bin/activate"
    echo "        pip install -r requirements.txt"
    exit 1
fi

# 체크포인트 파일 존재 확인
CHECKPOINT_PATH="../checkpoints_balanced/checkpoint_best.pth"
if [ ! -f "$CHECKPOINT_PATH" ]; then
    echo ""
    echo "[ERROR] 모델 체크포인트 파일이 없습니다:"
    echo "        $CHECKPOINT_PATH"
    echo ""
    exit 1
fi

echo "[INFO] 체크포인트 파일 확인됨: $CHECKPOINT_PATH"
echo ""

# Flask 환경 변수 설정
export FLASK_HOST=${FLASK_HOST:-"0.0.0.0"}
export FLASK_PORT=${FLASK_PORT:-5001}
export DEBUG="False"

# Gunicorn 설정
WORKERS=${WORKERS:-2}  # CPU 코어 수에 따라 조정
TIMEOUT=${TIMEOUT:-120}  # AI 추론 시간 고려하여 긴 타임아웃
BIND="$FLASK_HOST:$FLASK_PORT"

echo "설정:"
echo "  - Bind: $BIND"
echo "  - Workers: $WORKERS"
echo "  - Timeout: ${TIMEOUT}s"
echo "  - Debug: $DEBUG"
echo ""

# Gunicorn 프로덕션 서버 실행
echo "[INFO] Gunicorn 프로덕션 서버 시작..."
echo ""

gunicorn \
    --bind "$BIND" \
    --workers "$WORKERS" \
    --timeout "$TIMEOUT" \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --worker-class sync \
    app:app
