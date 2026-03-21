"""
SCIN 데이터셋 클래스

PyTorch Dataset 구현 - 다중 라벨 분류 지원
"""

import os
import json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
import torch
from torch.utils.data import Dataset
from torchvision import transforms


class SCINDataset(Dataset):
    """SCIN 피부 질환 데이터셋"""

    def __init__(self, data_dir, image_root, split='train', transform=None, augment=True):
        """
        Args:
            data_dir: 전처리된 데이터 디렉토리 (metadata.json, train.csv 등이 있는 곳)
            image_root: 이미지 루트 디렉토리
            split: 'train', 'val', 'test' 중 하나
            transform: 커스텀 transform (None이면 기본 transform 사용)
            augment: 학습 시 데이터 증강 여부
        """
        self.data_dir = Path(data_dir)
        self.image_root = Path(image_root)
        self.split = split
        self.augment = augment and (split == 'train')

        # 메타데이터 로드
        self.metadata = self._load_metadata()
        self.num_classes = self.metadata['num_classes']
        self.label_to_idx = self.metadata['label_to_idx']
        self.idx_to_label = {int(k): v for k, v in self.metadata['idx_to_label'].items()}

        # CSV 및 라벨 로드
        self.df = pd.read_csv(self.data_dir / f'{split}.csv', dtype={'case_id': str})
        self.labels = np.load(self.data_dir / f'{split}_labels.npy')

        # Transform 설정
        if transform is not None:
            self.transform = transform
        else:
            self.transform = self._get_default_transform()

        print(f"[INFO] {split.upper()} 데이터셋 로드 완료")
        print(f"       샘플 수: {len(self.df)}")
        print(f"       클래스 수: {self.num_classes}")
        print(f"       증강: {self.augment}")

    def _load_metadata(self):
        """메타데이터 JSON 로드"""
        metadata_path = self.data_dir / 'metadata.json'
        if not metadata_path.exists():
            raise FileNotFoundError(f"메타데이터 파일 없음: {metadata_path}")

        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        return metadata

    def _get_default_transform(self):
        """기본 Transform 생성"""
        if self.augment:
            # 학습 시 증강 (ResNet50: 224x224)
            return transforms.Compose([
                transforms.Resize((256, 256)),
                transforms.RandomCrop((224, 224)),
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
                transforms.RandomRotation(degrees=15),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
        else:
            # 검증/테스트 시 (ResNet50: 224x224)
            return transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])

    def _load_image(self, image_path):
        """
        이미지 로드 및 전처리

        Args:
            image_path: 이미지 경로 (상대 경로)

        Returns:
            PIL.Image: RGB 이미지
        """
        full_path = self.image_root / image_path

        if not full_path.exists():
            raise FileNotFoundError(f"이미지 없음: {full_path}")

        try:
            image = Image.open(full_path).convert('RGB')
            return image
        except Exception as e:
            raise IOError(f"이미지 로드 실패: {full_path} - {e}")

    def __len__(self):
        """데이터셋 크기 반환"""
        return len(self.df)

    def __getitem__(self, idx):
        """
        샘플 반환

        Args:
            idx: 인덱스

        Returns:
            dict: {
                'image': Tensor (C, H, W),
                'label': Tensor (num_classes,),
                'case_id': str,
                'image_path': str
            }
        """
        row = self.df.iloc[idx]

        # 이미지 로드 (fallback 지원: image_1 → image_2 → image_3)
        image = None
        image_path = None

        for col in ['image_1_path', 'image_2_path', 'image_3_path']:
            if col in row and pd.notna(row[col]):
                candidate_path = row[col]
                full_path = self.image_root / candidate_path

                # 파일 존재 확인
                if full_path.exists():
                    try:
                        # 이미지 로드 시도
                        image = Image.open(full_path).convert('RGB')
                        image_path = candidate_path
                        break
                    except Exception as e:
                        # 로드 실패 시 경고 출력하고 다음 이미지로 fallback
                        print(f"[WARN] 이미지 로드 실패 ({candidate_path}): {e}")
                        continue

        if image is None or image_path is None:
            raise ValueError(f"케이스 {row['case_id']}에 유효한 이미지 없음")

        # Transform 적용
        image_tensor = self.transform(image)

        # 라벨 로드
        label = torch.tensor(self.labels[idx], dtype=torch.float32)

        return {
            'image': image_tensor,
            'label': label,
            'case_id': row['case_id'],
            'image_path': image_path
        }

    def get_class_name(self, idx):
        """클래스 인덱스를 클래스명으로 변환"""
        return self.idx_to_label.get(idx, 'Unknown')

    def get_class_weights(self):
        """클래스 가중치 반환 (학습 시 사용)"""
        weights = self.metadata.get('class_weights', {})
        weight_tensor = torch.tensor([weights.get(str(i), 1.0) for i in range(self.num_classes)])
        return weight_tensor


class MultiImageSCINDataset(SCINDataset):
    """
    복수 이미지를 사용하는 SCIN 데이터셋
    케이스당 최대 3개 이미지 사용
    """

    def __init__(self, data_dir, image_root, split='train', transform=None, augment=True, max_images=3):
        """
        Args:
            max_images: 케이스당 최대 이미지 개수 (1~3)
        """
        super().__init__(data_dir, image_root, split, transform, augment)
        self.max_images = max_images

    def __getitem__(self, idx):
        """
        복수 이미지를 포함한 샘플 반환

        Returns:
            dict: {
                'images': List[Tensor],  # 최대 max_images 개
                'label': Tensor (num_classes,),
                'case_id': str,
                'num_images': int
            }
        """
        row = self.df.iloc[idx]

        # 모든 이미지 로드
        images = []
        image_paths = []

        for col in ['image_1_path', 'image_2_path', 'image_3_path']:
            if col in row and pd.notna(row[col]):
                image_path = row[col]
                try:
                    image = self._load_image(image_path)
                    image_tensor = self.transform(image)
                    images.append(image_tensor)
                    image_paths.append(image_path)

                    if len(images) >= self.max_images:
                        break
                except Exception as e:
                    print(f"[WARN] 이미지 로드 실패 ({image_path}): {e}")

        if len(images) == 0:
            raise ValueError(f"케이스 {row['case_id']}에 유효한 이미지 없음")

        # 라벨 로드
        label = torch.tensor(self.labels[idx], dtype=torch.float32)

        return {
            'images': images,
            'label': label,
            'case_id': row['case_id'],
            'image_paths': image_paths,
            'num_images': len(images)
        }


def get_data_loaders(data_dir, image_root, batch_size=32, num_workers=4, augment=True, multi_image=False):
    """
    Train/Val/Test DataLoader 생성

    Args:
        data_dir: 전처리된 데이터 디렉토리
        image_root: 이미지 루트 디렉토리
        batch_size: 배치 크기
        num_workers: DataLoader 워커 수
        augment: 학습 시 증강 여부
        multi_image: 복수 이미지 사용 여부

    Returns:
        dict: {'train': DataLoader, 'val': DataLoader, 'test': DataLoader}
    """
    from torch.utils.data import DataLoader

    dataset_class = MultiImageSCINDataset if multi_image else SCINDataset

    # 데이터셋 생성
    train_dataset = dataset_class(data_dir, image_root, split='train', augment=augment)
    val_dataset = dataset_class(data_dir, image_root, split='val', augment=False)
    test_dataset = dataset_class(data_dir, image_root, split='test', augment=False)

    # DataLoader 생성
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=True
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )

    print(f"\n[INFO] DataLoader 생성 완료")
    print(f"       배치 크기: {batch_size}")
    print(f"       워커 수: {num_workers}")
    print(f"       Train batches: {len(train_loader)}")
    print(f"       Val batches: {len(val_loader)}")
    print(f"       Test batches: {len(test_loader)}")

    return {
        'train': train_loader,
        'val': val_loader,
        'test': test_loader
    }


if __name__ == '__main__':
    # 테스트 코드
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--data_dir', type=str, required=True, help='전처리 데이터 디렉토리')
    parser.add_argument('--image_root', type=str, required=True, help='이미지 루트 디렉토리')
    args = parser.parse_args()

    # 데이터셋 테스트
    print("\n" + "="*60)
    print("SCIN Dataset 테스트")
    print("="*60)

    dataset = SCINDataset(args.data_dir, args.image_root, split='train', augment=True)

    print(f"\n샘플 확인:")
    sample = dataset[0]
    print(f"  이미지 shape: {sample['image'].shape}")
    print(f"  라벨 shape: {sample['label'].shape}")
    print(f"  Case ID: {sample['case_id']}")
    print(f"  이미지 경로: {sample['image_path']}")
    print(f"  라벨 (상위 5개 클래스):")

    # 라벨이 있는 클래스 출력
    label_indices = torch.where(sample['label'] == 1)[0]
    for idx in label_indices[:5]:
        print(f"    - {dataset.get_class_name(idx.item())}")

    print("\n✅ 데이터셋 테스트 성공!")
