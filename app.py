import os
from flask import Flask
from sqlalchemy import text
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY, UPLOAD_BASE_PATH
from extensions import db

def create_app():
    app = Flask(__name__)
    os.makedirs(os.path.join(os.path.dirname(__file__), "instance"), exist_ok=True)
    # 영구 저장 경로 사용 시 업로드 디렉터리 미리 생성 (슬립 후에도 직인/첨부파일 유지)
    if UPLOAD_BASE_PATH:
        for sub in ("uploads", "uploads/documents", "uploads/items"):
            os.makedirs(os.path.join(UPLOAD_BASE_PATH, sub), exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["SECRET_KEY"] = SECRET_KEY
    db.init_app(app)
    with app.app_context():
        from blueprints import register_blueprints
        register_blueprints(app)
        db.create_all()
        # documents 테이블 마이그레이션 (기존 DB용)
        try:
            tables = [r[0] for r in db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")).fetchall()]
            if tables:
                result = db.session.execute(text("PRAGMA table_info(documents)"))
                columns = [row[1] for row in result]
                if "file_path" not in columns:
                    db.session.execute(text("ALTER TABLE documents ADD COLUMN file_path VARCHAR(500)"))
                if "file_name" not in columns:
                    db.session.execute(text("ALTER TABLE documents ADD COLUMN file_name VARCHAR(255)"))
                if "updated_at" not in columns:
                    db.session.execute(text("ALTER TABLE documents ADD COLUMN updated_at DATETIME"))
                db.session.commit()
        except Exception:
            db.session.rollback()
    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
