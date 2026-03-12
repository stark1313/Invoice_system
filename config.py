import os

# .env 파일 로드 (선택, pip install python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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
