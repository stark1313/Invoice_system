import os

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

from extensions import db
from models import CompanyInfo
from upload_helpers import upload_base

bp = Blueprint("company", __name__)


def _get_company():
    c = CompanyInfo.query.first()
    if not c:
        c = CompanyInfo(id=1)
        db.session.add(c)
        db.session.commit()
    return c


@bp.route("/company", methods=["GET", "POST"])
def company_info():
    company = _get_company()
    if request.method == "POST":
        company.biz_no = request.form.get("biz_no", "").strip() or None
        company.name = request.form.get("name", "").strip() or None
        company.ceo = request.form.get("ceo", "").strip() or None
        company.address = request.form.get("address", "").strip() or None
        company.phone = request.form.get("phone", "").strip() or None
        company.fax = request.form.get("fax", "").strip() or None
        company.account_no = request.form.get("account_no", "").strip() or None
        company.account_holder = request.form.get("account_holder", "").strip() or None
        company.bank = request.form.get("bank", "").strip() or None
        company.business_type = request.form.get("business_type", "").strip() or None
        company.contact = request.form.get("contact", "").strip() or None
        f = request.files.get("stamp")
        if f and f.filename and f.filename.rsplit(".", 1)[-1].lower() in ("png", "jpg", "jpeg", "gif", "webp"):
            upload_dir = os.path.join(upload_base(), "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, secure_filename(f"stamp_{company.id}.png"))
            try:
                from PIL import Image

                img = Image.open(f.stream).convert("RGBA")
                data = img.getdata()
                new_data = []
                for item in data:
                    r, g, b, a = item
                    if r >= 245 and g >= 245 and b >= 245:
                        new_data.append((255, 255, 255, 0))
                    else:
                        new_data.append(item)
                img.putdata(new_data)
                img.save(filepath, "PNG")
                company.stamp_path = filepath
            except Exception:
                f.stream.seek(0)
                f.save(filepath)
                company.stamp_path = filepath
        db.session.commit()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(ok=True)
        flash("회사정보가 저장되었습니다.", "success")
        return redirect(url_for("company.company_info"))
    return render_template("company/form.html", company=company)


@bp.route("/company/stamp")
def company_stamp():
    company = _get_company()
    if not company.stamp_path or not os.path.isfile(company.stamp_path):
        return "", 404
    ext = company.stamp_path.rsplit(".", 1)[-1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/png")
    return send_file(company.stamp_path, mimetype=mime)
