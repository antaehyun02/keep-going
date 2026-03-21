#!/bin/bash

# Flask AI 서비스 개발 서버 실행 스크립트

echo "======================================"
echo "Flask AI Service - Development Mode"
echo "======================================"

# 현재 디렉토리 확인
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "작업 디렉토리: $SCRIPT_DIR"
echo ""

# Python 가상환경 확인
if [ -d "venv" ]; then
    echo "[INFO] 가상환경 활성화 중..."
    source venv/bin/activate
else
    echo "[WARNING] 가상환경이 없습니다. 생성하시겠습니까? (y/n)"
    read -r answer
    if [ "$answer" = "y" ]; then
        echo "[INFO] 가상환경 생성 중..."
        python3 -m venv venv
        source venv/bin/activate
        echo "[INFO] 의존성 설치 중..."
        pip install --upgrade pip
        pip install -r requirements.txt
    else
        echo "[INFO] 시스템 Python 사용"
    fi
fi

# 체크포인트 파일 존재 확인
CHECKPOINT_PATH="../checkpoints_balanced/checkpoint_best.pth"
if [ ! -f "$CHECKPOINT_PATH" ]; then
    echo ""
    echo "[ERROR] 모델 체크포인트 파일이 없습니다:"
    echo "        $CHECKPOINT_PATH"
    echo ""
    echo "모델을 먼저 학습하거나, 체크포인트 파일을 배치하세요."
    echo ""
    exit 1
fi

echo ""
echo "[INFO] 체크포인트 파일 확인됨: $CHECKPOINT_PATH"
echo ""

# Flask 환경 변수 설정
export FLASK_HOST=${FLASK_HOST:-"0.0.0.0"}
export FLASK_PORT=${FLASK_PORT:-5001}
export DEBUG=${DEBUG:-"True"}

echo "설정:"
echo "  - Host: $FLASK_HOST"
echo "  - Port: $FLASK_PORT"
echo "  - Debug: $DEBUG"
echo ""

# Flask 개발 서버 실행
echo "[INFO] Flask 개발 서버 시작..."
echo ""

python app.py
