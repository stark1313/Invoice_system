import os

# .env 파일 로드 (선택, pip install python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 업로드 파일(직인, 문서, 품목 이미지) 영구 저장 경로.
# 슬립/재부팅 후에도 유지되려면 디스크 기반 경로를 지정하세요.
# 예: /var/lib/invoice_system, ~/invoice_data
# 미설정 시 instance_path 사용 (기존 동작 유지)
_upload_path = os.environ.get("UPLOAD_PATH")
UPLOAD_BASE_PATH = os.path.expanduser(_upload_path) if _upload_path else None

SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'invoice.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# 공급자(본인 사업장) 정보
SUPPLIER_NAME = os.environ.get("SUPPLIER_NAME", "")
SUPPLIER_BIZ_NO = os.environ.get("SUPPLIER_BIZ_NO", "")
SUPPLIER_ADDRESS = os.environ.get("SUPPLIER_ADDRESS", "")
SUPPLIER_PHONE = os.environ.get("SUPPLIER_PHONE", "")
SUPPLIER_FAX = os.environ.get("SUPPLIER_FAX", "")
SUPPLIER_CONTACT = os.environ.get("SUPPLIER_CONTACT", "")  # 담당자/인수자
