"""
Flask AI 서비스 설정 파일
"""
import os
from pathlib import Path

# 프로젝트 루트 디렉토리
BASE_DIR = Path(__file__).resolve().parent.parent
API_DIR = Path(__file__).resolve().parent

# 모델 설정
MODEL_CHECKPOINT_PATH = BASE_DIR / 'checkpoints_balanced' / 'checkpoint_best.pth'
MODEL_TYPE = 'resnet50'  # ResNet50만 지원
NUM_CLASSES = 50

# 이미지 전처리 설정
IMAGE_SIZE = 224  # ResNet50 입력 크기

# Flask 서버 설정
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', 5001))  # 포트 5000 충돌로 5001 사용
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# 디바이스 설정 (GPU/MPS/CPU 자동 감지)
DEVICE = 'auto'  # inference.py에서 자동 감지

# 업로드 파일 설정
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

# 추론 설정
TOP_K_PREDICTIONS = 5  # Top-K 예측 개수
CONFIDENCE_THRESHOLD = 0.15  # 최소 신뢰도 임계값 (OOD 검출) - 15%로 낮춤
TEMPERATURE = 0.7  # Temperature Scaling (0.5~0.8 권장, 낮을수록 신뢰도 증가)

# 50개 피부 질환 한국어 번역 사전
DISEASE_LABELS_KR = {
    "Eczema": "습진",
    "Allergic Contact Dermatitis": "알레르기성 접촉 피부염",
    "Insect Bite": "벌레 물림",
    "Urticaria": "두드러기",
    "Psoriasis": "건선",
    "Folliculitis": "모낭염",
    "Irritant Contact Dermatitis": "자극성 접촉 피부염",
    "Tinea": "백선 (무좀)",
    "Drug Rash": "약진",
    "Herpes Zoster": "대상포진",
    "Herpes Simplex": "단순포진",
    "Acute dermatitis, NOS": "급성 피부염",
    "Impetigo": "농가진",
    "Hypersensitivity": "과민성 피부염",
    "Leukocytoclastic Vasculitis": "백혈구 파괴성 혈관염",
    "Acne": "여드름",
    "Pigmented purpuric eruption": "색소성 자반",
    "Lichen planus/lichenoid eruption": "편평태선",
    "Viral Exanthem": "바이러스성 발진",
    "Pityriasis rosea": "장미색 비강진",
    "Lichen Simplex Chronicus": "만성 단순태선",
    "Stasis Dermatitis": "울혈성 피부염",
    "CD - Contact dermatitis": "접촉 피부염",
    "Scabies": "옴",
    "Molluscum Contagiosum": "전염성 연속종",
    "Keratosis pilaris": "모공성 각화증",
    "Granuloma annulare": "환상 육아종",
    "Tinea Versicolor": "어루러기",
    "Rosacea": "주사",
    "O/E - ecchymoses present": "반상 출혈",
    "Abrasion, scrape, or scab": "찰과상/딱지",
    "Acute and chronic dermatitis": "급만성 피부염",
    "Seborrheic Dermatitis": "지루성 피부염",
    "Photodermatitis": "광피부염",
    "Abscess": "농양",
    "Verruca vulgaris": "사마귀",
    "Cellulitis": "봉와직염",
    "SCC/SCCIS": "편평세포암/상피내암",
    "Purpura": "자반증",
    "Miliaria": "한진 (땀띠)",
    "Erythema multiforme": "다형홍반",
    "Syphilis": "매독",
    "Cutaneous lupus": "피부 루푸스",
    "Intertrigo": "간찰진",
    "Inflicted skin lesions": "인위적 피부 병변",
    "Post-Inflammatory hyperpigmentation": "염증 후 과색소침착",
    "Pityriasis lichenoides": "유건선",
    "Prurigo nodularis": "결절성 양진",
    "Lichen nitidus": "광택태선",
    "Chronic dermatitis, NOS": "만성 피부염"
}

# SCIN 데이터셋 라벨 (50개 피부 질환)
# 주의: 실제 라벨은 scin/data/scin_labels.csv 파일에서 로드해야 함
# 여기서는 인덱스 → 라벨 매핑을 위한 플레이스홀더
DISEASE_LABELS = {
    0: "Acne",
    1: "Actinic Keratosis",
    2: "Atopic Dermatitis",
    3: "Bullous Pemphigoid",
    4: "Contact Dermatitis",
    5: "Cutaneous Horn",
    6: "Dermatofibroma",
    7: "Eczema",
    8: "Folliculitis",
    9: "Hemangioma",
    # ... 나머지 40개 라벨은 실제 데이터셋에서 로드
}

# 질환별 추천 사항 (간단한 매핑)
DISEASE_RECOMMENDATIONS = {
    "Acne": [
        "피부과 전문의 상담을 권장합니다",
        "유분기 적은 화장품을 사용하세요",
        "정기적인 클렌징이 중요합니다",
        "손으로 만지지 마세요"
    ],
    "Atopic Dermatitis": [
        "보습제를 자주 발라주세요",
        "피부과 전문의 진료가 필요합니다",
        "자극적인 세제 사용을 피하세요",
        "긁지 않도록 주의하세요"
    ],
    "Contact Dermatitis": [
        "알레르기 유발 물질을 파악하세요",
        "피부과 진료를 받으세요",
        "해당 물질과의 접촉을 피하세요",
        "스테로이드 연고가 필요할 수 있습니다"
    ],
    # 기본 추천 사항
    "default": [
        "피부과 전문의 상담을 권장합니다",
        "정확한 진단을 위해 병원 방문이 필요합니다",
        "자외선 차단제를 매일 사용하세요",
        "충분한 수분 공급을 유지하세요"
    ]
}
