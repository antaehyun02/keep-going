"""Google Drive API v3 인증 처리.

로컬 환경: OAuth2 브라우저 인증 → ~/.config/skinai_data/token.json 자동 저장·갱신
서버 환경: GOOGLE_APPLICATION_CREDENTIALS 환경변수로 Service Account 인증
"""

# ── 표준 라이브러리 ──────────────────────────────────────────────
import logging
import os
import sys
from pathlib import Path

# ── 서드파티 ─────────────────────────────────────────────────────
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# ── 상수 ─────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

CONFIG_DIR = Path.home() / ".config" / "skinai_data"
TOKEN_PATH = CONFIG_DIR / "token.json"
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"


# ── 헬퍼 ─────────────────────────────────────────────────────────

def _authenticate_oauth2() -> Credentials:
    """OAuth2 브라우저 인증 (로컬 개발용).

    Returns:
        Credentials: 유효한 OAuth2 자격증명

    Raises:
        SystemExit: credentials.json 미존재 시 설치 안내 후 종료
    """
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not CREDENTIALS_PATH.exists():
            print("[1/3] Google Cloud Console에서 OAuth2 자격증명을 생성하세요.")
            print(f"[2/3] credentials.json을 {CONFIG_DIR}/ 에 저장하세요.")
            print("[3/3] 브라우저 인증창이 열립니다...")
            sys.exit(1)

        print("[3/3] 브라우저 인증창이 열립니다...")
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
        creds = flow.run_local_server(port=0)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    logger.info(f"[INFO] 인증 완료. 토큰 저장: {TOKEN_PATH}")

    return creds


def _authenticate_service_account() -> Credentials:
    """Service Account 인증 (서버/headless 환경용).

    Returns:
        Credentials: Service Account 자격증명
    """
    sa_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    return service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)


# ── 공개 API ─────────────────────────────────────────────────────

def get_drive_service():
    """Google Drive API v3 서비스 객체 반환.

    GOOGLE_APPLICATION_CREDENTIALS 환경변수가 있으면 Service Account,
    없으면 OAuth2 브라우저 인증을 사용합니다.

    Returns:
        googleapiclient.discovery.Resource: Drive API 서비스
    """
    sa_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if sa_path and Path(sa_path).exists():
        creds = _authenticate_service_account()
    else:
        creds = _authenticate_oauth2()

    return build("drive", "v3", credentials=creds)


def main():
    """CLI 인증 엔트리포인트: python -m skinai_data.auth"""
    print("[skinai_data] Google Drive 인증을 시작합니다...")
    service = get_drive_service()
    about = service.about().get(fields="user").execute()
    email = about["user"]["emailAddress"]
    print(f"[skinai_data] 인증 성공! 계정: {email}")


if __name__ == "__main__":
    main()
