import csv
import io
import os

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename
from sqlalchemy import or_

from codegen import next_item_code
from extensions import db
from models import Item
from upload_helpers import upload_base

bp = Blueprint("items", __name__)


def _save_item_image(item, req):
    f = req.files.get("image")
    if f and f.filename and f.filename.rsplit(".", 1)[-1].lower() in ("png", "jpg", "jpeg", "gif", "webp"):
        upload_dir = os.path.join(upload_base(), "uploads", "items")
        os.makedirs(upload_dir, exist_ok=True)
        ext = f.filename.rsplit(".", 1)[-1].lower()
        if ext == "jpg":
            ext = "jpeg"
        filepath = os.path.join(upload_dir, secure_filename(f"item_{item.id}.{ext}"))
        try:
            f.save(filepath)
            item.image_path = filepath
        except Exception:
            pass


@bp.route("/items")
def item_list():
    q = request.args.get("q", "").strip()
    query = Item.query.filter(Item.code != "DIRECT")
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Item.name.ilike(like),
                Item.unit.ilike(like),
            )
        )
    items = query.order_by(Item.name).all()
    return render_template("items/list.html", items=items, q=q)


@bp.route("/items/add", methods=["GET", "POST"])
def item_add():
    if request.method == "POST":
        price = request.form.get("unit_price", "0").replace(",", "")
        try:
            price = int(price)
        except ValueError:
            price = 0
        item = Item(
            code=next_item_code(),
            name=request.form.get("name", "").strip(),
            spec=request.form.get("spec", "").strip() or None,
            unit=request.form.get("unit", "EA").strip() or "EA",
            unit_price=price,
        )
        db.session.add(item)
        db.session.flush()
        _save_item_image(item, request)
        db.session.commit()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(ok=True)
        flash("품목이 등록되었습니다.", "success")
        return redirect(url_for("items.item_list"))
    return render_template("items/form.html", item=None, has_image=False)


@bp.route("/items/<int:id>/edit", methods=["GET", "POST"])
def item_edit(id):
    item = Item.query.get_or_404(id)
    if item.code == "DIRECT":
        flash("직접입력 품목은 수정할 수 없습니다.", "danger")
        return redirect(url_for("items.item_list"))
    if request.method == "POST":
        item.name = request.form.get("name", "").strip()
        item.spec = request.form.get("spec", "").strip() or None
        item.unit = request.form.get("unit", "EA").strip() or "EA"
        price = request.form.get("unit_price", "0").replace(",", "")
        try:
            item.unit_price = int(price)
        except ValueError:
            item.unit_price = 0
        if request.form.get("remove_image") == "1":
            item.image_path = None
        _save_item_image(item, request)
        db.session.commit()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(ok=True)
        flash("품목이 수정되었습니다.", "success")
        return redirect(url_for("items.item_list"))
    return render_template("items/form.html", item=item, has_image=item.image_path and os.path.isfile(item.image_path) if item else False)


@bp.route("/items/<int:id>/image")
def item_image(id):
    item = Item.query.get_or_404(id)
    if not item.image_path or not os.path.isfile(item.image_path):
        return "", 404
    ext = item.image_path.rsplit(".", 1)[-1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/png")
    return send_file(item.image_path, mimetype=mime)


@bp.route("/items/<int:id>/delete", methods=["POST"])
def item_delete(id):
    item = Item.query.get_or_404(id)
    if item.code == "DIRECT":
        flash("직접입력 품목은 삭제할 수 없습니다.", "danger")
        return redirect(url_for("items.item_list"))
    db.session.delete(item)
    db.session.commit()
    flash("품목이 삭제되었습니다.", "success")
    return redirect(url_for("items.item_list"))


@bp.route("/items/upload", methods=["GET", "POST"])
def item_upload():
    if request.method == "POST":
        f = request.files.get("file")
        if not f or not f.filename or not f.filename.lower().endswith((".csv", ".txt")):
            flash("CSV 파일을 선택해 주세요.", "danger")
            return redirect(url_for("items.item_upload"))
        try:
            stream = io.StringIO(f.stream.read().decode("utf-8-sig"))
            reader = csv.reader(stream)
            header = next(reader, None)
            if not header:
                flash("파일 내용이 비어 있습니다.", "danger")
                return redirect(url_for("items.item_upload"))
            r = db.session.query(db.func.max(Item.code)).filter(Item.code.like("P%")).scalar()
            start = int(r[1:]) + 1 if r and len(r) > 1 and r[1:].isdigit() else 1
            count = 0
            for row in reader:
                if len(row) < 1 or not (row[0] or "").strip():
                    continue
                name = (row[0] or "").strip()
                if not name:
                    continue
                spec = (row[1] if len(row) > 1 else "").strip() or None
                unit = (row[2] if len(row) > 2 else "EA").strip() or "EA"
                try:
                    unit_price = int((row[3] if len(row) > 3 else "0").replace(",", ""))
                except ValueError:
                    unit_price = 0
                item = Item(code=f"P{start + count:06d}", name=name, spec=spec, unit=unit, unit_price=unit_price)
                db.session.add(item)
                count += 1
            db.session.commit()
            flash(f"품목 {count}건이 일괄 등록되었습니다.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"업로드 실패: {e}", "danger")
        return redirect(url_for("items.item_list"))
    return render_template("items/upload.html")


@bp.route("/items/sample-csv")
def item_sample_csv():
    si = io.StringIO()
    w = csv.writer(si)
    w.writerow(["품목명", "규격", "단위", "단가"])
    w.writerow(["상품A", "#6, 100*100", "EA", "1100"])
    w.writerow(["상품B", "", "BOX", "5500"])
    data = si.getvalue().encode("utf-8-sig")
    buf = io.BytesIO(data)
    return send_file(buf, mimetype="text/csv", as_attachment=True, download_name="items_sample.csv")


@bp.route("/inventory")
def inventory_list():
    items = Item.query.filter(Item.code != "DIRECT").order_by(Item.name).all()
    return render_template("inventory/list.html", items=items)


@bp.route("/api/item/<int:id>")
def api_item(id):
    item = Item.query.get_or_404(id)
    return {"id": item.id, "name": item.name, "spec": item.spec or "", "unit": item.unit, "unit_price": item.unit_price}
