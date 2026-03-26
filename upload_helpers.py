import os

from flask import current_app

from config import UPLOAD_BASE_PATH


def upload_base():
    """업로드 파일 영구 저장 경로. UPLOAD_PATH 미설정 시 instance_path 사용."""
    return UPLOAD_BASE_PATH or current_app.instance_path
