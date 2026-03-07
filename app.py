import os
from flask import Flask
from sqlalchemy import text
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY
from extensions import db

def create_app():
    app = Flask(__name__)
    os.makedirs(os.path.join(os.path.dirname(__file__), "instance"), exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["SECRET_KEY"] = SECRET_KEY
    db.init_app(app)
    with app.app_context():
        from routes import register_routes
        register_routes(app)
        db.create_all()
        # documents 테이블에 file_path, file_name 컬럼 추가 (기존 DB 마이그레이션)
        try:
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
