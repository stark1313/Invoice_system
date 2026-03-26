import os

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename
from sqlalchemy import or_

from codegen import next_document_code
from extensions import db
from models import Document, DocumentFile
from upload_helpers import upload_base

bp = Blueprint("documents", __name__)


def _save_document_files(doc, req):
    upload_dir = os.path.join(upload_base(), "uploads", "documents")
    os.makedirs(upload_dir, exist_ok=True)
    for i, f in enumerate(req.files.getlist("file")):
        if f and f.filename:
            safe_name = secure_filename(f"{doc.id}_{doc.code or 'doc'}_{i}_{f.filename}")
            filepath = os.path.join(upload_dir, safe_name)
            try:
                f.save(filepath)
                df = DocumentFile(document_id=doc.id, file_path=filepath, file_name=f.filename)
                db.session.add(df)
            except Exception:
                pass


@bp.route("/documents")
def document_list():
    q = request.args.get("q", "").strip()
    query = Document.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Document.name.ilike(like),
                Document.memo.ilike(like),
            )
        )
    documents = query.order_by(Document.name).all()
    return render_template("documents/list.html", documents=documents, q=q)


@bp.route("/documents/add", methods=["GET", "POST"])
def document_add():
    if request.method == "POST":
        doc = Document(
            code=next_document_code(),
            name=request.form.get("name", "").strip(),
            memo=request.form.get("memo", "").strip() or None,
        )
        db.session.add(doc)
        db.session.flush()
        _save_document_files(doc, request)
        db.session.commit()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(ok=True)
        flash("자료가 등록되었습니다.", "success")
        return redirect(url_for("documents.document_list"))
    return render_template("documents/form.html", document=None)


@bp.route("/documents/<int:id>/edit", methods=["GET", "POST"])
def document_edit(id):
    doc = Document.query.get_or_404(id)
    if request.method == "POST":
        doc.name = request.form.get("name", "").strip()
        doc.memo = request.form.get("memo", "").strip() or None
        remove_ids = request.form.getlist("remove_file_id", type=int)
        for fid in remove_ids:
            df = DocumentFile.query.filter(DocumentFile.id == fid, DocumentFile.document_id == doc.id).first()
            if df:
                if df.file_path and os.path.isfile(df.file_path):
                    try:
                        os.remove(df.file_path)
                    except Exception:
                        pass
                db.session.delete(df)
        if request.form.get("remove_legacy_file") == "1" and doc.file_path:
            if os.path.isfile(doc.file_path):
                try:
                    os.remove(doc.file_path)
                except Exception:
                    pass
            doc.file_path = None
            doc.file_name = None
        _save_document_files(doc, request)
        db.session.commit()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(ok=True)
        flash("자료가 수정되었습니다.", "success")
        return redirect(url_for("documents.document_list"))
    return render_template("documents/form.html", document=doc)


@bp.route("/documents/<int:id>/download")
def document_file_download_legacy(id):
    """기존 단일 파일(doc.file_path) 다운로드 - 하위 호환"""
    doc = Document.query.get_or_404(id)
    if not doc.file_path or not os.path.isfile(doc.file_path):
        flash("첨부파일이 없습니다.", "danger")
        return redirect(url_for("documents.document_list"))
    return send_file(
        doc.file_path,
        as_attachment=True,
        download_name=doc.file_name or os.path.basename(doc.file_path),
    )


@bp.route("/documents/<int:doc_id>/file/<int:file_id>/download")
def document_file_download(doc_id, file_id):
    df = DocumentFile.query.filter(DocumentFile.id == file_id, DocumentFile.document_id == doc_id).first_or_404()
    if not df.file_path or not os.path.isfile(df.file_path):
        flash("첨부파일이 없습니다.", "danger")
        return redirect(url_for("documents.document_list"))
    return send_file(
        df.file_path,
        as_attachment=True,
        download_name=df.file_name or os.path.basename(df.file_path),
    )


@bp.route("/documents/<int:id>/delete", methods=["POST"])
def document_delete(id):
    doc = Document.query.get_or_404(id)
    for df in doc.files:
        if df.file_path and os.path.isfile(df.file_path):
            try:
                os.remove(df.file_path)
            except Exception:
                pass
    if doc.file_path and os.path.isfile(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass
    db.session.delete(doc)
    db.session.commit()
    flash("자료가 삭제되었습니다.", "success")
    return redirect(url_for("documents.document_list"))
