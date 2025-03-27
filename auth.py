import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Google API 접근 범위 설정
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/forms.body'  # 폼 내용 수정 권한
]

# 환경 변수에서 클라이언트 정보 가져오기
CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

def get_token_path():
    """운영 체제에 따른 토큰 저장 경로 반환"""
    if sys.platform == "win32":
        return os.path.join(os.environ["APPDATA"], "GoogleAPI", "token.json")
    return os.path.join(os.path.expanduser("~"), ".config", "GoogleAPI", "token.json")

def ensure_token_dir():
    """토큰 저장 디렉토리가 없으면 생성"""
    token_dir = os.path.dirname(get_token_path())
    if not os.path.exists(token_dir):
        os.makedirs(token_dir)

def get_credentials():
    """OAuth2 인증을 통해 자격 증명 반환"""
    token_path = get_token_path()
    ensure_token_dir()
    creds = None

    # 토큰 파일이 있으면 불러오기
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            print(f"토큰 파일 로드 중 오류 발생: {e}")
    
    # 토큰이 없거나 유효하지 않은 경우
    if not creds or not creds.valid:
        # 토큰이 만료되었고 갱신이 가능한 경우
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("토큰이 성공적으로 갱신되었습니다.")
            except Exception as e:
                print(f"토큰 갱신 중 오류 발생: {e}")
                creds = None
        
        # 새로운 인증이 필요한 경우
        if not creds:
            print("새로운 인증이 필요합니다. 브라우저가 열리면 Google 계정으로 로그인하여 권한을 승인해주세요.")
            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id": CLIENT_ID,
                        "client_secret": CLIENT_SECRET,
                        "redirect_uris": ["http://localhost"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                },
                SCOPES
            )
            creds = flow.run_local_server(port=0)
            
            # 새로운 토큰 저장
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            print("새로운 인증 토큰이 생성되었습니다.")
    
    return creds
