"""
SCIN 데이터셋 다운로드 스크립트

Google Cloud Storage에서 SCIN 데이터셋을 다운로드합니다.
- CSV 파일 (cases, labels)
- 이미지 파일

**지원하는 다운로드 방식**:
1. Public URL 방식 (권장): 인증 불필요, curl 기반
2. GCS SDK 방식: Google Cloud Storage API 사용, 인증 필요

사용법:
    # Public URL 방식 (인증 불필요) > README.md 데이터 다운로드(방법 A) 참고
    python download.py --use_public_url --output_dir ./scin_dataset --max_images 1000

    # GCS SDK 방식 (인증 필요)
    python download.py --output_dir ./scin_dataset --max_images 1000
"""

import io
import os
import argparse
import subprocess
import time
from pathlib import Path
import pandas as pd
from tqdm import tqdm


class SCINDataDownloader:
    """SCIN 데이터셋 다운로더 (Public URL 및 GCS SDK 지원)"""

    def __init__(self, use_public_url=False, gcp_project='dx-scin-public', bucket_name='dx-scin-public-data'):
        """
        Args:
            use_public_url: Public URL 방식 사용 여부 (기본값: False)
            gcp_project: GCP 프로젝트 이름
            bucket_name: GCS 버킷 이름
        """
        self.use_public_url = use_public_url
        self.gcp_project = gcp_project
        self.bucket_name = bucket_name
        self.base_url = f"https://storage.googleapis.com/{bucket_name}/"
        self.storage_client = None
        self.bucket = None

    def initialize(self):
        """GCS 클라이언트 초기화 (Public URL 방식에서는 스킵)"""
        if self.use_public_url:
            print(f"[INFO] Public URL 방식 사용 (인증 불필요)")
            print(f"[INFO] Base URL: {self.base_url}")
            return

        # GCS SDK 방식
        try:
            from google.cloud import storage
            self.storage_client = storage.Client(self.gcp_project)
            self.bucket = self.storage_client.bucket(self.bucket_name)
            print(f"[INFO] GCS 버킷 '{self.bucket_name}' 연결 성공")
        except Exception as e:
            print(f"[ERROR] GCS 연결 실패: {e}")
            print("[TIP] Google Cloud 인증이 필요합니다:")
            print("  1. gcloud auth login")
            print("  2. gcloud auth application-default login")
            print("\n또는 Public URL 방식을 사용하세요:")
            print("  python download.py --use_public_url")
            raise

    def download_csv(self, csv_path, output_dir):
        """
        CSV 파일 다운로드

        Args:
            csv_path: GCS 내 CSV 경로 (예: 'dataset/scin_cases.csv')
            output_dir: 저장 디렉토리

        Returns:
            pd.DataFrame: 로드된 데이터프레임
        """
        if self.use_public_url:
            return self._download_csv_public(csv_path, output_dir)
        else:
            return self._download_csv_gcs(csv_path, output_dir)

    def _download_csv_public(self, csv_path, output_dir):
        """Public URL로 CSV 다운로드"""
        try:
            full_url = self.base_url + csv_path
            output_path = Path(output_dir) / Path(csv_path).name
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # curl로 다운로드
            result = subprocess.run(
                ['curl', '-s', '-f', '-L', '-o', str(output_path), full_url],
                capture_output=True,
                timeout=60
            )

            if result.returncode != 0:
                raise Exception(f"curl 실패 (exit code: {result.returncode})")

            # CSV 로드
            df = pd.read_csv(output_path, dtype={'case_id': str})
            df['case_id'] = df['case_id'].astype(str)

            print(f"[INFO] CSV 다운로드 완료: {csv_path} → {output_path}")
            print(f"       총 {len(df)}개 레코드")
            return df

        except Exception as e:
            print(f"[ERROR] CSV 다운로드 실패: {csv_path}")
            print(f"        {e}")
            raise

    def _download_csv_gcs(self, csv_path, output_dir):
        """GCS SDK로 CSV 다운로드"""
        try:
            blob = self.bucket.blob(csv_path)
            content = blob.download_as_string()
            df = pd.read_csv(io.BytesIO(content), dtype={'case_id': str})
            df['case_id'] = df['case_id'].astype(str)

            # 로컬에 저장
            output_path = Path(output_dir) / Path(csv_path).name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_path, index=False)

            print(f"[INFO] CSV 다운로드 완료: {csv_path} → {output_path}")
            print(f"       총 {len(df)}개 레코드")
            return df

        except Exception as e:
            print(f"[ERROR] CSV 다운로드 실패: {csv_path}")
            print(f"        {e}")
            raise

    def download_image(self, image_path, output_dir):
        """
        단일 이미지 다운로드

        Args:
            image_path: GCS 내 이미지 경로
            output_dir: 저장 디렉토리

        Returns:
            str: 저장된 로컬 경로 (실패 시 None)
        """
        if self.use_public_url:
            return self._download_image_public(image_path, output_dir)
        else:
            return self._download_image_gcs(image_path, output_dir)

    def _download_image_public(self, image_path, output_dir):
        """Public URL로 이미지 다운로드 (재시도 포함)"""
        full_url = self.base_url + image_path
        local_path = Path(output_dir) / image_path
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # 이미 다운로드된 경우 스킵
        if local_path.exists() and local_path.stat().st_size > 0:
            return str(local_path)

        # 최대 3회 재시도
        for attempt in range(3):
            try:
                result = subprocess.run(
                    ['curl', '-s', '-f', '-L', '-o', str(local_path), full_url],
                    capture_output=True,
                    timeout=30
                )

                if result.returncode == 0 and local_path.exists() and local_path.stat().st_size > 0:
                    return str(local_path)
                else:
                    if attempt == 2:  # 마지막 시도 실패
                        if local_path.exists():
                            local_path.unlink()
                        return None
                    else:
                        time.sleep(1)  # 재시도 전 대기

            except Exception as e:
                if attempt == 2:  # 마지막 시도 실패
                    if local_path.exists():
                        local_path.unlink()
                    return None
                else:
                    time.sleep(1)

        return None

    def _download_image_gcs(self, image_path, output_dir):
        """GCS SDK로 이미지 다운로드"""
        try:
            blob = self.bucket.blob(image_path)

            # 로컬 경로 생성 (원본 구조 유지)
            local_path = Path(output_dir) / image_path
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # 이미 다운로드된 경우 스킵
            if local_path.exists():
                return str(local_path)

            # 다운로드
            blob.download_to_filename(str(local_path))
            return str(local_path)

        except Exception as e:
            return None

    def download_images_from_dataframe(self, df, output_dir, max_images=None):
        """
        데이터프레임에서 이미지 경로를 추출하여 다운로드

        Args:
            df: cases_and_labels_df (image_1_path, image_2_path, image_3_path 컬럼 필요)
            output_dir: 저장 디렉토리
            max_images: 최대 다운로드 이미지 수 (None이면 전체)

        Returns:
            dict: 다운로드 통계
        """
        image_columns = ['image_1_path', 'image_2_path', 'image_3_path']

        # 모든 이미지 경로 수집
        image_paths = []
        for col in image_columns:
            if col in df.columns:
                paths = df[col].dropna().tolist()
                image_paths.extend(paths)

        # 중복 제거
        image_paths = list(set(image_paths))

        if max_images:
            image_paths = image_paths[:max_images]

        print(f"\n[INFO] 다운로드할 이미지: {len(image_paths)}개")

        # 다운로드 진행
        success_count = 0
        failed_count = 0

        for image_path in tqdm(image_paths, desc="이미지 다운로드"):
            result = self.download_image(image_path, output_dir)
            if result:
                success_count += 1
            else:
                failed_count += 1

        stats = {
            'total': len(image_paths),
            'success': success_count,
            'failed': failed_count
        }

        print(f"\n[INFO] 다운로드 완료:")
        print(f"       성공: {success_count}개")
        print(f"       실패: {failed_count}개")

        return stats

    def download_full_dataset(self, output_dir, max_images=None):
        """
        전체 SCIN 데이터셋 다운로드

        Args:
            output_dir: 저장 디렉토리
            max_images: 최대 다운로드 이미지 수 (None이면 전체)

        Returns:
            dict: 다운로드된 데이터 정보
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"SCIN 데이터셋 다운로드 시작")
        print(f"저장 경로: {output_dir}")
        if self.use_public_url:
            print(f"다운로드 방식: Public URL (인증 불필요)")
        else:
            print(f"다운로드 방식: Google Cloud Storage SDK")
        print(f"{'='*60}\n")

        # 1. CSV 다운로드
        print("[STEP 1] CSV 파일 다운로드")
        cases_df = self.download_csv('dataset/scin_cases.csv', output_dir)
        labels_df = self.download_csv('dataset/scin_labels.csv', output_dir)

        # 2. 데이터 병합
        print("\n[STEP 2] 데이터 병합")
        merged_df = pd.merge(cases_df, labels_df, on='case_id')
        print(f"[INFO] 병합 완료: {len(merged_df)}개 케이스")

        # 병합된 데이터 저장
        merged_path = output_path / 'scin_merged.csv'
        merged_df.to_csv(merged_path, index=False)
        print(f"[INFO] 병합 데이터 저장: {merged_path}")

        # 3. 이미지 다운로드
        print("\n[STEP 3] 이미지 다운로드")
        image_stats = self.download_images_from_dataframe(merged_df, output_dir, max_images)

        # 4. 요약 정보
        print(f"\n{'='*60}")
        print("다운로드 완료!")
        print(f"{'='*60}")
        print(f"케이스 수: {len(merged_df)}")
        print(f"이미지 수: {image_stats['success']} / {image_stats['total']}")
        print(f"저장 위치: {output_dir}")
        print(f"{'='*60}\n")

        return {
            'cases_count': len(merged_df),
            'images_downloaded': image_stats['success'],
            'images_total': image_stats['total'],
            'output_dir': str(output_dir)
        }


def main():
    parser = argparse.ArgumentParser(
        description='SCIN 데이터셋 다운로드 (Public URL 또는 GCS SDK 지원)'
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        default='./scin_dataset',
        help='다운로드 저장 디렉토리 (기본값: ./scin_dataset)'
    )
    parser.add_argument(
        '--max_images',
        type=int,
        default=None,
        help='최대 다운로드 이미지 수 (기본값: 전체)'
    )
    parser.add_argument(
        '--use_public_url',
        action='store_true',
        help='Public URL 방식 사용 (인증 불필요, 권장)'
    )
    parser.add_argument(
        '--gcp_project',
        type=str,
        default='dx-scin-public',
        help='GCP 프로젝트 이름 (GCS SDK 사용 시)'
    )
    parser.add_argument(
        '--bucket_name',
        type=str,
        default='dx-scin-public-data',
        help='GCS 버킷 이름 (GCS SDK 사용 시)'
    )

    args = parser.parse_args()

    # 다운로더 초기화
    downloader = SCINDataDownloader(
        use_public_url=args.use_public_url,
        gcp_project=args.gcp_project,
        bucket_name=args.bucket_name
    )

    # 초기화
    downloader.initialize()

    # 데이터셋 다운로드
    result = downloader.download_full_dataset(
        output_dir=args.output_dir,
        max_images=args.max_images
    )

    print(f"✅ 다운로드 성공!")
    print(f"다음 단계: python preprocess.py --data_dir {args.output_dir}")


if __name__ == '__main__':
    main()
