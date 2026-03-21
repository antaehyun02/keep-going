"""
SCIN 데이터셋 전처리 스크립트

다운로드된 SCIN 데이터를 학습 가능한 형태로 변환합니다:
- 라벨 추출 및 인코딩 (다중 라벨 지원)
- Train/Val/Test 분할 (70/15/15)
- 메타데이터 저장 (label_mapping.json)

사용법:
    python preprocess.py --data_dir ./scin_dataset --output_dir ./scin_processed
"""

import os
import json
import argparse
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MultiLabelBinarizer
from tqdm import tqdm


class SCINDataPreprocessor:
    """SCIN 데이터 전처리기"""

    def __init__(self, min_samples_per_class=10, top_k_classes=50):
        """
        Args:
            min_samples_per_class: 클래스당 최소 샘플 수 (이하는 제외)
            top_k_classes: 상위 K개 클래스만 사용
        """
        self.min_samples_per_class = min_samples_per_class
        self.top_k_classes = top_k_classes
        self.label_encoder = None
        self.label_to_idx = {}
        self.idx_to_label = {}
        self.class_weights = None

    def load_data(self, data_dir):
        """
        다운로드된 데이터 로드

        Args:
            data_dir: 다운로드 디렉토리

        Returns:
            pd.DataFrame: 병합된 데이터프레임
        """
        merged_csv = Path(data_dir) / 'scin_merged.csv'

        if not merged_csv.exists():
            raise FileNotFoundError(
                f"병합된 CSV 파일이 없습니다: {merged_csv}\n"
                f"먼저 download.py를 실행하세요."
            )

        print(f"[INFO] 데이터 로드: {merged_csv}")
        df = pd.read_csv(merged_csv, dtype={'case_id': str})
        print(f"[INFO] 총 {len(df)}개 케이스 로드")

        return df

    def extract_labels(self, df):
        """
        weighted_skin_condition_label에서 라벨 추출

        Args:
            df: 데이터프레임

        Returns:
            list: 각 케이스의 라벨 리스트
        """
        print("\n[STEP 1] 라벨 추출")

        labels_list = []
        condition_counter = Counter()

        for idx, row in tqdm(df.iterrows(), total=len(df), desc="라벨 파싱"):
            weighted_label_str = row['weighted_skin_condition_label']

            if pd.isna(weighted_label_str):
                labels_list.append([])
                continue

            try:
                # 문자열을 딕셔너리로 변환
                weighted_labels = eval(weighted_label_str)

                # 키(질환명) 추출
                conditions = list(weighted_labels.keys())
                labels_list.append(conditions)

                # 전체 질환 카운트
                condition_counter.update(conditions)

            except Exception as e:
                print(f"[WARN] 라벨 파싱 실패 (case_id: {row['case_id']}): {e}")
                labels_list.append([])

        print(f"[INFO] 총 {len(condition_counter)}개 고유 질환 발견")
        print(f"[INFO] 가장 많은 질환 Top 10:")
        for condition, count in condition_counter.most_common(10):
            print(f"       - {condition}: {count}건")

        return labels_list, condition_counter

    def filter_and_encode_labels(self, labels_list, condition_counter):
        """
        라벨 필터링 및 인코딩

        Args:
            labels_list: 각 케이스의 라벨 리스트
            condition_counter: 질환별 카운트

        Returns:
            tuple: (필터링된 라벨 리스트, 라벨 매핑)
        """
        print("\n[STEP 2] 라벨 필터링 및 인코딩")

        # Top K 질환 선택
        top_conditions = [cond for cond, count in condition_counter.most_common(self.top_k_classes)]

        print(f"[INFO] 상위 {len(top_conditions)}개 질환 선택")
        print(f"[INFO] 최소 샘플 수: {self.min_samples_per_class}")

        # 라벨 인덱스 매핑 생성
        self.label_to_idx = {label: idx for idx, label in enumerate(top_conditions)}
        self.idx_to_label = {idx: label for label, idx in self.label_to_idx.items()}

        print(f"[INFO] 라벨 매핑 완료: {len(self.label_to_idx)}개 클래스")

        # 라벨 필터링 (Top K에 포함된 것만)
        filtered_labels = []
        for labels in labels_list:
            filtered = [label for label in labels if label in self.label_to_idx]
            filtered_labels.append(filtered)

        # 유효한 샘플 개수 확인
        valid_count = sum(1 for labels in filtered_labels if len(labels) > 0)
        print(f"[INFO] 유효한 샘플: {valid_count} / {len(filtered_labels)}")

        return filtered_labels, self.label_to_idx

    def create_multilabel_matrix(self, labels_list):
        """
        다중 라벨을 이진 행렬로 변환

        Args:
            labels_list: 라벨 리스트

        Returns:
            np.ndarray: (N, C) 이진 행렬
        """
        print("\n[STEP 3] 다중 라벨 이진 행렬 생성")

        num_classes = len(self.label_to_idx)
        num_samples = len(labels_list)

        # 이진 행렬 초기화
        label_matrix = np.zeros((num_samples, num_classes), dtype=np.float32)

        for i, labels in enumerate(labels_list):
            for label in labels:
                if label in self.label_to_idx:
                    idx = self.label_to_idx[label]
                    label_matrix[i, idx] = 1.0

        # 통계
        samples_with_labels = np.sum(label_matrix.sum(axis=1) > 0)
        avg_labels_per_sample = label_matrix.sum() / samples_with_labels if samples_with_labels > 0 else 0

        print(f"[INFO] 행렬 크기: {label_matrix.shape}")
        print(f"[INFO] 라벨이 있는 샘플: {samples_with_labels} / {num_samples}")
        print(f"[INFO] 샘플당 평균 라벨 수: {avg_labels_per_sample:.2f}")

        return label_matrix

    def calculate_class_weights(self, label_matrix):
        """
        클래스 불균형을 위한 가중치 계산

        Args:
            label_matrix: 다중 라벨 이진 행렬

        Returns:
            dict: 클래스별 가중치
        """
        print("\n[STEP 4] 클래스 가중치 계산")

        # 각 클래스의 샘플 수
        class_counts = label_matrix.sum(axis=0)

        # 가중치 계산 (역빈도)
        total_samples = len(label_matrix)
        class_weights = {}

        for idx, count in enumerate(class_counts):
            if count > 0:
                weight = total_samples / (len(class_counts) * count)
                class_weights[idx] = weight
            else:
                class_weights[idx] = 1.0

        # 빈 데이터셋 체크
        if len(class_weights) == 0:
            raise ValueError(
                "클래스 가중치 계산 실패: 유효한 샘플이 없습니다.\n"
                "이미지 검증 단계에서 모든 케이스가 필터링되었을 가능성이 있습니다.\n"
                "데이터 경로와 이미지 파일 존재 여부를 확인하세요."
            )

        print(f"[INFO] 가중치 범위: {min(class_weights.values()):.2f} ~ {max(class_weights.values()):.2f}")

        return class_weights

    def validate_images(self, df, image_root):
        """
        이미지 파일 존재 여부 검증 및 경로 수정

        Args:
            df: 데이터프레임
            image_root: 이미지 루트 디렉토리

        Returns:
            pd.DataFrame: 검증된 데이터프레임
        """
        print("\n[STEP] 이미지 파일 존재 확인")

        image_root_path = Path(image_root)
        image_cols = ['image_1_path', 'image_2_path', 'image_3_path']
        valid_rows = []
        removed_count = 0
        fixed_count = 0

        for idx, row in tqdm(df.iterrows(), total=len(df), desc="이미지 검증"):
            # 유효한 이미지 경로 수집
            valid_images = []
            for col in image_cols:
                if col in row and pd.notna(row[col]):
                    # CSV 경로에서 "dataset/images/" 접두사 제거 (중복 방지)
                    path_str = str(row[col])
                    if path_str.startswith('dataset/images/'):
                        path_str = path_str.replace('dataset/images/', '', 1)

                    full_path = image_root_path / path_str
                    if full_path.exists():
                        valid_images.append(row[col])

            if len(valid_images) > 0:
                # 적어도 하나의 이미지가 있으면 경로 재배치
                original_images = [row[col] for col in image_cols if col in row and pd.notna(row[col])]
                if valid_images != original_images:
                    fixed_count += 1

                # 경로 재할당
                row['image_1_path'] = valid_images[0] if len(valid_images) > 0 else None
                row['image_2_path'] = valid_images[1] if len(valid_images) > 1 else None
                row['image_3_path'] = valid_images[2] if len(valid_images) > 2 else None
                valid_rows.append(row)
            else:
                # 모든 이미지가 없으면 제외
                removed_count += 1

        validated_df = pd.DataFrame(valid_rows).reset_index(drop=True)

        print(f"[INFO] 검증 완료:")
        print(f"       경로 수정: {fixed_count}건")
        print(f"       제외된 케이스: {removed_count}건")
        print(f"       유효한 케이스: {len(validated_df)}건")

        return validated_df

    def split_data(self, df, label_matrix, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, random_state=42):
        """
        데이터를 Train/Val/Test로 분할

        Args:
            df: 원본 데이터프레임
            label_matrix: 라벨 행렬
            train_ratio: 학습 데이터 비율
            val_ratio: 검증 데이터 비율
            test_ratio: 테스트 데이터 비율
            random_state: 랜덤 시드

        Returns:
            dict: 분할된 데이터 정보
        """
        print(f"\n[STEP 5] 데이터 분할 (Train: {train_ratio*100:.0f}%, Val: {val_ratio*100:.0f}%, Test: {test_ratio*100:.0f}%)")

        # 유효한 샘플 인덱스 (라벨이 있는 것만)
        valid_indices = np.where(label_matrix.sum(axis=1) > 0)[0]
        print(f"[INFO] 유효한 샘플: {len(valid_indices)} / {len(df)}")

        valid_df = df.iloc[valid_indices].reset_index(drop=True)
        valid_labels = label_matrix[valid_indices]

        # Train + Val / Test 분할
        train_val_df, test_df, train_val_labels, test_labels = train_test_split(
            valid_df, valid_labels,
            test_size=test_ratio,
            random_state=random_state
        )

        # Train / Val 분할
        val_ratio_adjusted = val_ratio / (train_ratio + val_ratio)
        train_df, val_df, train_labels, val_labels = train_test_split(
            train_val_df, train_val_labels,
            test_size=val_ratio_adjusted,
            random_state=random_state
        )

        print(f"[INFO] Train: {len(train_df)} 샘플")
        print(f"[INFO] Val:   {len(val_df)} 샘플")
        print(f"[INFO] Test:  {len(test_df)} 샘플")

        return {
            'train': {'df': train_df, 'labels': train_labels},
            'val': {'df': val_df, 'labels': val_labels},
            'test': {'df': test_df, 'labels': test_labels}
        }

    def save_processed_data(self, split_data, output_dir, label_to_idx, class_weights):
        """
        전처리된 데이터 저장

        Args:
            split_data: 분할된 데이터
            output_dir: 저장 디렉토리
            label_to_idx: 라벨 매핑
            class_weights: 클래스 가중치
        """
        print(f"\n[STEP 6] 전처리 데이터 저장: {output_dir}")
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 1. 메타데이터 저장
        metadata = {
            'num_classes': int(len(label_to_idx)),
            'label_to_idx': label_to_idx,
            'idx_to_label': self.idx_to_label,
            'class_weights': {str(k): float(v) for k, v in class_weights.items()},
            'train_samples': int(len(split_data['train']['df'])),
            'val_samples': int(len(split_data['val']['df'])),
            'test_samples': int(len(split_data['test']['df']))
        }

        metadata_path = output_path / 'metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"[INFO] 메타데이터 저장: {metadata_path}")

        # 2. 분할 데이터 저장
        for split_name, split_info in split_data.items():
            # CSV 저장
            csv_path = output_path / f'{split_name}.csv'
            split_info['df'].to_csv(csv_path, index=False)

            # 라벨 행렬 저장
            labels_path = output_path / f'{split_name}_labels.npy'
            np.save(labels_path, split_info['labels'])

            print(f"[INFO] {split_name.upper()} 저장: {csv_path}, {labels_path}")

        print(f"\n{'='*60}")
        print("전처리 완료!")
        print(f"{'='*60}")
        print(f"저장 위치: {output_dir}")
        print(f"클래스 수: {len(label_to_idx)}")
        print(f"Train: {metadata['train_samples']} 샘플")
        print(f"Val:   {metadata['val_samples']} 샘플")
        print(f"Test:  {metadata['test_samples']} 샘플")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description='SCIN 데이터 전처리')
    parser.add_argument(
        '--data_dir',
        type=str,
        required=True,
        help='다운로드된 데이터 디렉토리'
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        default='./scin_processed',
        help='전처리 데이터 저장 디렉토리'
    )
    parser.add_argument(
        '--top_k_classes',
        type=int,
        default=50,
        help='상위 K개 클래스 사용 (기본값: 50)'
    )
    parser.add_argument(
        '--min_samples',
        type=int,
        default=10,
        help='클래스당 최소 샘플 수 (기본값: 10)'
    )
    parser.add_argument(
        '--train_ratio',
        type=float,
        default=0.7,
        help='학습 데이터 비율 (기본값: 0.7)'
    )
    parser.add_argument(
        '--val_ratio',
        type=float,
        default=0.15,
        help='검증 데이터 비율 (기본값: 0.15)'
    )
    parser.add_argument(
        '--test_ratio',
        type=float,
        default=0.15,
        help='테스트 데이터 비율 (기본값: 0.15)'
    )

    args = parser.parse_args()

    # 전처리기 초기화
    preprocessor = SCINDataPreprocessor(
        min_samples_per_class=args.min_samples,
        top_k_classes=args.top_k_classes
    )

    # 1. 데이터 로드
    df = preprocessor.load_data(args.data_dir)

    # 2. 이미지 파일 존재 확인 및 검증
    image_root = Path(args.data_dir) / 'dataset' / 'images'
    df = preprocessor.validate_images(df, image_root)

    # 3. 라벨 추출
    labels_list, condition_counter = preprocessor.extract_labels(df)

    # 4. 라벨 필터링 및 인코딩
    filtered_labels, label_to_idx = preprocessor.filter_and_encode_labels(labels_list, condition_counter)

    # 5. 다중 라벨 행렬 생성
    label_matrix = preprocessor.create_multilabel_matrix(filtered_labels)

    # 6. 클래스 가중치 계산
    class_weights = preprocessor.calculate_class_weights(label_matrix)

    # 7. 데이터 분할
    split_data = preprocessor.split_data(
        df, label_matrix,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio
    )

    # 8. 저장
    preprocessor.save_processed_data(split_data, args.output_dir, label_to_idx, class_weights)

    print(f"✅ 전처리 성공!")
    print(f"다음 단계: python ../model/train.py --data_dir {args.output_dir}")


if __name__ == '__main__':
    main()
