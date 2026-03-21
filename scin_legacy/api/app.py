"""
Flask AI 서비스 메인 애플리케이션

피부 질환 이미지 분류 API
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import traceback

from config import (
    FLASK_HOST,
    FLASK_PORT,
    DEBUG,
    MAX_CONTENT_LENGTH,
    ALLOWED_EXTENSIONS
)
from inference import get_predictor

# Flask 앱 초기화
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# CORS 설정 (Node.js 백엔드 허용)
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5001",
            "http://127.0.0.1:5001"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# 임시 업로드 디렉토리
UPLOAD_FOLDER = Path(__file__).resolve().parent / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    """허용된 파일 확장자 검사"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/health', methods=['GET'])
def health_check():
    """
    헬스 체크 엔드포인트

    Returns:
        200 OK: 서비스 정상 작동
    """
    return jsonify({
        'status': 'healthy',
        'service': 'SCIN AI Prediction Service',
        'version': '1.0.0'
    }), 200


@app.route('/predict', methods=['POST'])
def predict():
    """
    피부 질환 예측 엔드포인트

    Request:
        - Content-Type: multipart/form-data
        - image: 이미지 파일 (JPG/PNG, 최대 5MB)

    Response:
        200 OK:
        {
            "success": true,
            "data": {
                "predictions": [
                    {
                        "disease": "Acne",
                        "confidence": 0.85,
                        "confidence_percent": "85.0%",
                        "recommendations": ["...", "..."]
                    },
                    ...
                ],
                "summary": "Acne 가능성이 높습니다...",
                "top_disease": "Acne",
                "overall_confidence": 0.85
            }
        }

        400 Bad Request:
        {
            "success": false,
            "message": "에러 메시지"
        }

        500 Internal Server Error:
        {
            "success": false,
            "message": "서버 오류",
            "error": "상세 에러 (DEBUG 모드에서만)"
        }
    """
    print(f"[INFO] /predict 요청 수신")
    print(f"[INFO] Content-Type: {request.content_type}")
    print(f"[INFO] Files: {list(request.files.keys())}")

    try:
        # 파일 검증
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'message': '이미지 파일이 필요합니다'
            }), 400

        file = request.files['image']

        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '파일이 선택되지 않았습니다'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'message': f'허용되지 않은 파일 형식입니다. 허용: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        # 파일 저장 (임시)
        filename = secure_filename(file.filename)
        filepath = app.config['UPLOAD_FOLDER'] / filename
        file.save(filepath)

        # 모델 예측
        predictor = get_predictor()
        result = predictor.predict_with_summary(filepath)

        # 임시 파일 삭제
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"[WARNING] 임시 파일 삭제 실패: {e}")

        return jsonify({
            'success': True,
            'data': result
        }), 200

    except FileNotFoundError as e:
        error_msg = f"모델 파일 없음: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return jsonify({
            'success': False,
            'message': '모델을 로드할 수 없습니다',
            'error': error_msg if DEBUG else None
        }), 500

    except Exception as e:
        error_msg = traceback.format_exc()
        print(f"[ERROR] 예측 실패:\n{error_msg}")
        return jsonify({
            'success': False,
            'message': '이미지 분석 중 오류가 발생했습니다',
            'error': str(e) if DEBUG else None
        }), 500


@app.route('/predict-batch', methods=['POST'])
def predict_batch():
    """
    다중 이미지 예측 엔드포인트 (향후 구현)

    Request:
        - Content-Type: multipart/form-data
        - images[]: 이미지 파일 배열 (최대 3개)

    Response:
        200 OK:
        {
            "success": true,
            "data": {
                "results": [
                    {"image_name": "...", "predictions": [...], "summary": "..."},
                    ...
                ],
                "combined_summary": "종합 분석 결과"
            }
        }
    """
    return jsonify({
        'success': False,
        'message': '배치 예측 기능은 아직 구현되지 않았습니다'
    }), 501


@app.errorhandler(413)
def request_entity_too_large(error):
    """파일 크기 초과 에러 핸들러"""
    return jsonify({
        'success': False,
        'message': f'파일 크기가 너무 큽니다. 최대 크기: {MAX_CONTENT_LENGTH // (1024 * 1024)}MB'
    }), 413


@app.errorhandler(404)
def not_found(error):
    """404 에러 핸들러"""
    return jsonify({
        'success': False,
        'message': '요청한 엔드포인트를 찾을 수 없습니다'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500 에러 핸들러"""
    return jsonify({
        'success': False,
        'message': '서버 내부 오류가 발생했습니다',
        'error': str(error) if DEBUG else None
    }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("SCIN AI Prediction Service")
    print("=" * 60)
    print(f"Host: {FLASK_HOST}")
    print(f"Port: {FLASK_PORT}")
    print(f"Debug: {DEBUG}")
    print(f"Max upload size: {MAX_CONTENT_LENGTH // (1024 * 1024)}MB")
    print("=" * 60)

    # 모델 로드 (서버 시작 시 1회)
    try:
        print("\n[INFO] 모델 로딩 중...")
        get_predictor()
        print("[INFO] 모델 로드 완료!\n")
    except Exception as e:
        print(f"\n[ERROR] 모델 로드 실패: {e}\n")
        print("서버를 시작할 수 없습니다.")
        exit(1)

    # Flask 서버 실행
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=DEBUG,
        threaded=True  # 멀티스레드 지원
    )
