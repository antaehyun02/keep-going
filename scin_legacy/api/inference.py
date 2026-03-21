"""
모델 추론 로직

PyTorch 모델 로드 및 이미지 분류 수행
"""
import sys
from pathlib import Path

# 모델 모듈 임포트를 위한 경로 추가
sys.path.append(str(Path(__file__).resolve().parent.parent / 'model'))

import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
import numpy as np
import json

from config import (
    MODEL_CHECKPOINT_PATH,
    MODEL_TYPE,
    NUM_CLASSES,
    IMAGE_SIZE,
    TOP_K_PREDICTIONS,
    CONFIDENCE_THRESHOLD,
    TEMPERATURE,
    DISEASE_LABELS,
    DISEASE_LABELS_KR,
    DISEASE_RECOMMENDATIONS,
    BASE_DIR
)


class ResNet50Classifier(nn.Module):
    """ResNet50 기반 다중 라벨 분류기 (train.py와 동일한 구조)"""

    def __init__(self, num_classes, pretrained=True, dropout=0.5):
        super(ResNet50Classifier, self).__init__()
        self.backbone = models.resnet50(pretrained=pretrained)
        num_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(num_features, num_classes)
        )

    def forward(self, x):
        return self.backbone(x)




class SkinDiseasePredictor:
    """피부 질환 예측기"""

    def __init__(self):
        """모델 초기화 및 로드"""
        self.device = self._get_device()
        self.model = None
        self.transform = None
        self.idx_to_label = None

        self._load_model()
        self._setup_transform()
        self._load_labels()

        print(f"[INFO] 모델 로드 완료")
        print(f"       모델 타입: {MODEL_TYPE}")
        print(f"       디바이스: {self.device}")
        print(f"       체크포인트: {MODEL_CHECKPOINT_PATH}")

    def _get_device(self):
        """사용 가능한 디바이스 감지"""
        if torch.cuda.is_available():
            device = torch.device('cuda')
            print(f"[INFO] CUDA 사용 가능: {torch.cuda.get_device_name(0)}")
        #elif torch.backends.mps.is_available():
         #   device = torch.device('mps')
          #  print(f"[INFO] Apple MPS 사용 가능")
        else:
            device = torch.device('cpu')
            print(f"[INFO] CPU 사용")

        return device

    def _load_model(self):
        """체크포인트에서 모델 로드"""
        # 모델 생성 (ResNet50만 지원)
        if MODEL_TYPE == 'resnet50':
            self.model = ResNet50Classifier(num_classes=NUM_CLASSES, pretrained=False, dropout=0.6)
        else:
            raise ValueError(f"지원하지 않는 모델 타입: {MODEL_TYPE}. 'resnet50'만 지원됩니다.")

        # 체크포인트 로드
        if not MODEL_CHECKPOINT_PATH.exists():
            raise FileNotFoundError(f"체크포인트 파일 없음: {MODEL_CHECKPOINT_PATH}")

        checkpoint = torch.load(MODEL_CHECKPOINT_PATH, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])

        # 평가 모드 전환
        self.model.to(self.device)
        self.model.eval()

        # 체크포인트 정보 출력
        print(f"[INFO] 체크포인트 로드 완료")
        print(f"       에포크: {checkpoint.get('epoch', 'N/A')}")
        print(f"       최고 검증 손실: {checkpoint.get('best_val_loss', 'N/A'):.4f}")

    def _setup_transform(self):
        """이미지 전처리 Transform 설정"""
        # ImageNet 표준 정규화 (dataset.py와 동일)
        self.transform = transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def _load_labels(self):
        """라벨 매핑 로드"""
        metadata_path = BASE_DIR / 'data' / 'scin_processed' / 'metadata.json'

        if metadata_path.exists():
            # metadata.json에서 라벨 로드
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            self.idx_to_label = {int(k): v for k, v in metadata['idx_to_label'].items()}
            print(f"[INFO] 라벨 매핑 로드 완료: {len(self.idx_to_label)}개 클래스")
        else:
            # metadata.json이 없으면 config.py의 DISEASE_LABELS 사용
            self.idx_to_label = DISEASE_LABELS
            print(f"[WARNING] metadata.json 없음. config.py의 라벨 사용")

    def preprocess_image(self, image_path):
        """
        이미지 전처리

        Args:
            image_path: 이미지 파일 경로 또는 PIL Image 객체

        Returns:
            (1, 3, H, W) 형태의 텐서
        """
        if isinstance(image_path, str) or isinstance(image_path, Path):
            image = Image.open(image_path).convert('RGB')
        elif isinstance(image_path, Image.Image):
            image = image_path.convert('RGB')
        else:
            raise ValueError(f"지원하지 않는 이미지 타입: {type(image_path)}")

        # Transform 적용
        tensor = self.transform(image)

        # 배치 차원 추가 (1, 3, H, W)
        tensor = tensor.unsqueeze(0)

        return tensor

    def predict(self, image_path, top_k=TOP_K_PREDICTIONS, threshold=CONFIDENCE_THRESHOLD):
        """
        이미지 분류 예측

        Args:
            image_path: 이미지 파일 경로
            top_k: 상위 K개 예측 반환
            threshold: 최소 신뢰도 임계값

        Returns:
            예측 결과 리스트 [{disease, confidence, recommendation}]
        """
        # 이미지 전처리
        image_tensor = self.preprocess_image(image_path)
        image_tensor = image_tensor.to(self.device)

        # 추론 (Temperature Scaling 적용)
        with torch.no_grad():
            outputs = self.model(image_tensor)
            # Temperature Scaling: 낮은 temperature로 신뢰도 증가
            probabilities = torch.sigmoid(outputs / TEMPERATURE).cpu().numpy()[0]  # (num_classes,)

        # Top-K 예측 추출
        top_k_indices = np.argsort(probabilities)[::-1][:top_k]
        top_k_probs = probabilities[top_k_indices]

        # 결과 생성
        predictions = []
        for idx, prob in zip(top_k_indices, top_k_probs):
            if prob >= threshold:
                disease_name = self.idx_to_label.get(idx, f"Unknown_{idx}")
                recommendations = DISEASE_RECOMMENDATIONS.get(
                    disease_name,
                    DISEASE_RECOMMENDATIONS.get("default", [])
                )

                # OOD(Out-of-Distribution) 검출: 신뢰도 25% 미만
                is_ood = bool(prob < 0.25)  # numpy.bool_ → Python bool 변환
                prediction = {
                    'disease': disease_name,
                    'disease_ko': DISEASE_LABELS_KR.get(disease_name, disease_name),
                    'confidence': float(prob),
                    'confidence_percent': f"{prob * 100:.1f}%",
                    'recommendations': recommendations,
                    'is_ood': is_ood
                }

                # OOD 경고 메시지 추가
                if is_ood:
                    prediction['warning'] = '신뢰도가 낮습니다. 피부 사진이 아닐 수 있습니다.'

                predictions.append(prediction)

        # 임계값 이상 예측이 없으면 최소 1개는 반환
        if len(predictions) == 0 and len(top_k_indices) > 0:
            idx = top_k_indices[0]
            prob = top_k_probs[0]
            disease_name = self.idx_to_label.get(idx, f"Unknown_{idx}")
            recommendations = DISEASE_RECOMMENDATIONS.get("default", [])

            predictions.append({
                'disease': disease_name,
                'disease_ko': DISEASE_LABELS_KR.get(disease_name, disease_name),
                'confidence': float(prob),
                'confidence_percent': f"{prob * 100:.1f}%",
                'recommendations': recommendations,
                'is_ood': True,  # 임계값 미만은 항상 OOD
                'warning': '신뢰도가 낮습니다. 피부 사진이 아닐 수 있습니다.'
            })

        return predictions

    def predict_with_summary(self, image_path):
        """
        예측 + 요약 정보 생성

        Args:
            image_path: 이미지 파일 경로

        Returns:
            {predictions, summary, top_disease, overall_confidence}
        """
        predictions = self.predict(image_path)

        if len(predictions) == 0:
            return {
                'predictions': [],
                'summary': '피부 질환을 감지하지 못했습니다. 피부과 전문의 상담을 권장합니다.',
                'top_disease': None,
                'overall_confidence': 0.0
            }

        top_disease = predictions[0]['disease']
        top_confidence = predictions[0]['confidence']

        # 요약 생성
        if top_confidence >= 0.7:
            summary = f"{top_disease} 가능성이 높습니다. 정확한 진단을 위해 피부과 전문의 상담을 권장합니다."
        elif top_confidence >= 0.5:
            summary = f"{top_disease} 가능성이 있습니다. 전문의 진료를 통해 정확한 진단을 받으시기 바랍니다."
        else:
            summary = f"여러 피부 질환 가능성이 있습니다. 피부과 전문의 진료가 필요합니다."

        return {
            'predictions': predictions,
            'summary': summary,
            'top_disease': top_disease,
            'overall_confidence': float(top_confidence)
        }


# 전역 인스턴스 (Flask 앱에서 재사용)
_predictor = None


def get_predictor():
    """싱글톤 Predictor 인스턴스 반환"""
    global _predictor
    if _predictor is None:
        _predictor = SkinDiseasePredictor()
    return _predictor
