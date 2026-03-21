"""
Flask AI 서비스 테스트 스크립트

서비스가 정상적으로 작동하는지 확인하는 자동화 테스트
"""
import requests
import json
import sys
from pathlib import Path

# 테스트할 Flask 서비스 URL
SERVICE_URL = 'http://localhost:5001'


def test_health_check():
    """헬스 체크 테스트"""
    print("\n" + "=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)

    try:
        response = requests.get(f"{SERVICE_URL}/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        if response.status_code == 200 and response.json().get('status') == 'healthy':
            print("✅ PASSED: Flask 서비스가 정상 작동 중입니다.")
            return True
        else:
            print("❌ FAILED: 예상하지 못한 응답")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ FAILED: Flask 서비스에 연결할 수 없습니다.")
        print(f"   서비스가 {SERVICE_URL}에서 실행 중인지 확인하세요.")
        print(f"   실행: cd scin/api && ./start.sh")
        return False

    except requests.exceptions.Timeout:
        print("❌ FAILED: 요청 시간 초과")
        return False

    except Exception as e:
        print(f"❌ FAILED: 예상치 못한 에러 - {e}")
        return False


def test_predict_api():
    """이미지 예측 API 테스트"""
    print("\n" + "=" * 60)
    print("TEST 2: Predict API (샘플 이미지 업로드)")
    print("=" * 60)

    # 샘플 이미지 찾기
    sample_image_paths = [
        Path("../data/downloaded/images").glob("*.jpg"),
        Path("../data/processed/images").glob("*.jpg"),
        Path("../../backend/uploads").glob("*.jpg"),
        Path("../../backend/uploads").glob("*.JPG"),
    ]

    sample_image = None
    for path_glob in sample_image_paths:
        for img_path in path_glob:
            if img_path.is_file():
                sample_image = img_path
                break
        if sample_image:
            break

    if not sample_image or not sample_image.exists():
        print("⚠️ WARNING: 샘플 이미지를 찾을 수 없어 테스트를 건너뜁니다.")
        print("   업로드된 이미지가 있는 경로:")
        print("   - scin/data/downloaded/images/")
        print("   - backend/uploads/")
        return None

    print(f"샘플 이미지: {sample_image}")

    try:
        with open(sample_image, 'rb') as f:
            files = {'image': (sample_image.name, f, 'image/jpeg')}
            response = requests.post(
                f"{SERVICE_URL}/predict",
                files=files,
                timeout=60  # AI 추론 시간 고려
            )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        if response.status_code == 200:
            data = response.json()
            if data.get('success') and 'predictions' in data.get('data', {}):
                predictions = data['data']['predictions']
                print(f"\n✅ PASSED: AI 예측 성공!")
                print(f"   Top Disease: {data['data'].get('top_disease')}")
                print(f"   Confidence: {data['data'].get('overall_confidence', 0) * 100:.1f}%")
                print(f"   Predictions Count: {len(predictions)}")
                return True
            else:
                print("❌ FAILED: 응답 형식이 올바르지 않습니다.")
                return False
        elif response.status_code == 403:
            print("❌ FAILED: 403 Forbidden - CORS 설정 문제")
            print("   해결 방법:")
            print("   1. Flask 서비스를 재시작하세요")
            print("   2. app.py의 CORS 설정을 확인하세요")
            return False
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print("❌ FAILED: 요청 시간 초과 (60초)")
        print("   모델 로딩이 느린 경우 정상입니다. 재시도하세요.")
        return False

    except Exception as e:
        print(f"❌ FAILED: 예상치 못한 에러 - {e}")
        return False


def test_cors_headers():
    """CORS 헤더 확인"""
    print("\n" + "=" * 60)
    print("TEST 3: CORS Headers Check")
    print("=" * 60)

    try:
        response = requests.options(
            f"{SERVICE_URL}/predict",
            headers={
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            },
            timeout=5
        )

        print(f"Status Code: {response.status_code}")
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
        }
        print(f"CORS Headers: {json.dumps(cors_headers, indent=2)}")

        if response.headers.get('Access-Control-Allow-Origin'):
            print("✅ PASSED: CORS 헤더가 올바르게 설정되어 있습니다.")
            return True
        else:
            print("❌ FAILED: CORS 헤더가 없습니다.")
            return False

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("Flask AI Service Test Suite")
    print("=" * 60)
    print(f"Service URL: {SERVICE_URL}")

    results = {
        'health_check': test_health_check(),
        'cors_headers': test_cors_headers(),
        'predict_api': test_predict_api(),
    }

    # 결과 요약
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)

    for test_name, result in results.items():
        status = "✅ PASSED" if result is True else ("❌ FAILED" if result is False else "⚠️ SKIPPED")
        print(f"{test_name:20s}: {status}")

    print(f"\nTotal: {len(results)} tests")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Skipped: {skipped}")

    # 모든 필수 테스트 통과 여부
    critical_tests = ['health_check', 'cors_headers']
    all_critical_passed = all(results.get(t) is True for t in critical_tests)

    if all_critical_passed:
        print("\n✅ 모든 필수 테스트 통과!")
        print("   Flask AI 서비스가 정상 작동 중입니다.")
        return 0
    else:
        print("\n❌ 일부 필수 테스트 실패")
        print("   위 에러 메시지를 참고하여 문제를 해결하세요.")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
