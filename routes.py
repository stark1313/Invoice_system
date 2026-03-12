import csv
import io
import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, send_file, current_app, jsonify
from werkzeug.utils import secure_filename
from sqlalchemy import or_, extract
from extensions import db
from models import Customer, Item, Transaction, TransactionItem, CompanyInfo, Document, DocumentFile
from utils import amount_to_korean_won
from config import (
    SUPPLIER_NAME,
    SUPPLIER_BIZ_NO,
    SUPPLIER_ADDRESS,
    SUPPLIER_PHONE,
    SUPPLIER_FAX,
    SUPPLIER_CONTACT,
)


def _transaction_rows(t):
    rows = []
    for ti in t.items:
        spec = ti.spec_custom or (ti.item.spec if ti.item else None) or "-"
        unit = ti.unit_custom or (ti.item.unit if ti.item else "EA") or "EA"
        rows.append({
            "name": (ti.item_name_custom or ti.item.name) if ti.item else (ti.item_name_custom or "-"),
            "spec": spec,
            "unit": unit,
            "quantity": ti.quantity,
            "unit_price": ti.unit_price,
            "supply_amount": ti.supply_amount,
            "vat": ti.vat,
            "total": ti.total,
        })
    return rows


def _totals(rows):
    total_supply = sum(r["supply_amount"] for r in rows)
    total_vat = sum(r["vat"] for r in rows)
    total_amount = sum(r["total"] for r in rows)
    return total_supply, total_vat, total_amount


def _next_customer_code():
    r = db.session.query(db.func.max(Customer.code)).filter(Customer.code.like("C%")).scalar()
    n = int(r[1:]) + 1 if r and len(r) > 1 and r[1:].isdigit() else 1
    return f"C{n:06d}"


def _next_transaction_code():
    r = db.session.query(db.func.max(Transaction.code)).filter(Transaction.code.like("B%")).scalar()
    n = int(r[1:]) + 1 if r and len(r) > 1 and r[1:].isdigit() else 1
    return f"B{n:06d}"


def _direct_input_item():
    """직접입력용 placeholder Item (없으면 생성)"""
    item = Item.query.filter(Item.code == "DIRECT").first()
    if not item:
        item = Item(code="DIRECT", name="직접입력", unit="EA", unit_price=0)
        db.session.add(item)
        db.session.commit()
    return item


def _next_item_code():
    r = db.session.query(db.func.max(Item.code)).filter(Item.code.like("P%")).scalar()
    n = int(r[1:]) + 1 if r and len(r) > 1 and r[1:].isdigit() else 1
    return f"P{n:06d}"


def _parse_int_list(request, name, default=0):
    out = []
    for v in request.form.getlist(name):
        try:
            out.append(int(v) if v else default)
        except (ValueError, TypeError):
            out.append(default)
    return out


def register_routes(app):
    @app.route("/")
    def index():
        return redirect(url_for("transaction_list"))

    @app.route("/health")
    def health():
        return "ok", 200

    # ----- 회사정보 -----
    def _get_company():
        c = CompanyInfo.query.first()
        if not c:
            c = CompanyInfo(id=1)
            db.session.add(c)
            db.session.commit()
        return c

    @app.route("/company", methods=["GET", "POST"])
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
                upload_dir = os.path.join(current_app.instance_path, "uploads")
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
            return redirect(url_for("company_info"))
        return render_template("company/form.html", company=company)

    @app.route("/company/stamp")
    def company_stamp():
        company = _get_company()
        if not company.stamp_path or not os.path.isfile(company.stamp_path):
            return "", 404
        ext = company.stamp_path.rsplit(".", 1)[-1].lower()
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/png")
        return send_file(company.stamp_path, mimetype=mime)

    # ----- 자료실 -----
    def _next_document_code():
        r = db.session.query(db.func.max(Document.code)).filter(Document.code.like("D%")).scalar()
        n = int(r[1:]) + 1 if r and len(r) > 1 and r[1:].isdigit() else 1
        return f"D{n:06d}"

    @app.route("/documents")
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

    def _save_document_files(doc, request):
        upload_dir = os.path.join(current_app.instance_path, "uploads", "documents")
        os.makedirs(upload_dir, exist_ok=True)
        for i, f in enumerate(request.files.getlist("file")):
            if f and f.filename:
                safe_name = secure_filename(f"{doc.id}_{doc.code or 'doc'}_{i}_{f.filename}")
                filepath = os.path.join(upload_dir, safe_name)
                try:
                    f.save(filepath)
                    df = DocumentFile(document_id=doc.id, file_path=filepath, file_name=f.filename)
                    db.session.add(df)
                except Exception:
                    pass

    @app.route("/documents/add", methods=["GET", "POST"])
    def document_add():
        if request.method == "POST":
            doc = Document(
                code=_next_document_code(),
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
            return redirect(url_for("document_list"))
        return render_template("documents/form.html", document=None)

    @app.route("/documents/<int:id>/edit", methods=["GET", "POST"])
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
            return redirect(url_for("document_list"))
        return render_template("documents/form.html", document=doc)

    @app.route("/documents/<int:id>/download")
    def document_file_download_legacy(id):
        """기존 단일 파일(doc.file_path) 다운로드 - 하위 호환"""
        doc = Document.query.get_or_404(id)
        if not doc.file_path or not os.path.isfile(doc.file_path):
            flash("첨부파일이 없습니다.", "danger")
            return redirect(url_for("document_list"))
        return send_file(
            doc.file_path,
            as_attachment=True,
            download_name=doc.file_name or os.path.basename(doc.file_path),
        )

    @app.route("/documents/<int:doc_id>/file/<int:file_id>/download")
    def document_file_download(doc_id, file_id):
        df = DocumentFile.query.filter(DocumentFile.id == file_id, DocumentFile.document_id == doc_id).first_or_404()
        if not df.file_path or not os.path.isfile(df.file_path):
            flash("첨부파일이 없습니다.", "danger")
            return redirect(url_for("document_list"))
        return send_file(
            df.file_path,
            as_attachment=True,
            download_name=df.file_name or os.path.basename(df.file_path),
        )

    @app.route("/documents/<int:id>/delete", methods=["POST"])
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
        return redirect(url_for("document_list"))

    # ----- Customers -----
    @app.route("/customers")
    def customer_list():
        q = request.args.get("q", "").strip()
        query = Customer.query
        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(
                    Customer.name.ilike(like),
                    Customer.biz_no.ilike(like),
                    Customer.business_type.ilike(like),
                    Customer.business_item.ilike(like),
                    Customer.phone.ilike(like),
                    Customer.ceo.ilike(like),
                )
            )
        customers = query.order_by(Customer.name).all()
        return render_template("customers/list.html", customers=customers, q=q)

    @app.route("/customers/add", methods=["GET", "POST"])
    def customer_add():
        if request.method == "POST":
            gubun = request.form.get("gubun", "").strip() or "일반"
            if gubun not in ("일반", "관급"):
                gubun = "일반"
            c = Customer(
                code=_next_customer_code(),
                gubun=gubun,
                name=request.form.get("name", "").strip(),
                biz_no=request.form.get("biz_no", "").strip() or "",
                business_type=request.form.get("business_type", "").strip() or "",
                business_item=request.form.get("business_item", "").strip() or "",
                phone=request.form.get("phone", "").strip() or "",
                address=request.form.get("address", "").strip() or "",
                ceo=request.form.get("ceo", "").strip() or "",
            )
            db.session.add(c)
            db.session.commit()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify(ok=True)
            flash("거래처가 등록되었습니다.", "success")
            return redirect(url_for("customer_list"))
        return render_template("customers/form.html", customer=None)

    @app.route("/customers/<int:id>/edit", methods=["GET", "POST"])
    def customer_edit(id):
        customer = Customer.query.get_or_404(id)
        if request.method == "POST":
            gubun = request.form.get("gubun", "").strip() or "일반"
            if gubun not in ("일반", "관급"):
                gubun = "일반"
            customer.gubun = gubun
            customer.name = request.form.get("name", "").strip()
            customer.biz_no = request.form.get("biz_no", "").strip() or ""
            customer.business_type = request.form.get("business_type", "").strip() or ""
            customer.business_item = request.form.get("business_item", "").strip() or ""
            customer.phone = request.form.get("phone", "").strip() or ""
            customer.address = request.form.get("address", "").strip() or ""
            customer.ceo = request.form.get("ceo", "").strip() or ""
            db.session.commit()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify(ok=True)
            flash("거래처가 수정되었습니다.", "success")
            return redirect(url_for("customer_list"))
        return render_template("customers/form.html", customer=customer)

    @app.route("/customers/<int:id>/delete", methods=["POST"])
    def customer_delete(id):
        customer = Customer.query.get_or_404(id)
        db.session.delete(customer)
        db.session.commit()
        flash("거래처가 삭제되었습니다.", "success")
        return redirect(url_for("customer_list"))

    @app.route("/customers/upload", methods=["GET", "POST"])
    def customer_upload():
        if request.method == "POST":
            f = request.files.get("file")
            if not f or not f.filename or not f.filename.lower().endswith((".csv", ".txt")):
                flash("CSV 파일을 선택해 주세요.", "danger")
                return redirect(url_for("customer_upload"))
            try:
                stream = io.StringIO(f.stream.read().decode("utf-8-sig"))
                reader = csv.reader(stream)
                header = next(reader, None)
                if not header:
                    flash("파일 내용이 비어 있습니다.", "danger")
                    return redirect(url_for("customer_upload"))
                r = db.session.query(db.func.max(Customer.code)).filter(Customer.code.like("C%")).scalar()
                start = int(r[1:]) + 1 if r and len(r) > 1 and r[1:].isdigit() else 1
                count = 0
                for row in reader:
                    if len(row) < 1 or not (row[0] or "").strip():
                        continue
                    name = (row[0] or "").strip()
                    if not name:
                        continue
                    c = Customer(
                        code=f"C{start + count:06d}",
                        gubun="일반",
                        name=name,
                        biz_no=(row[1] if len(row) > 1 else "").strip() or "",
                        business_type=(row[2] if len(row) > 2 else "").strip() or "",
                        business_item=(row[3] if len(row) > 3 else "").strip() or "",
                        phone=(row[4] if len(row) > 4 else "").strip() or "",
                        ceo=(row[5] if len(row) > 5 else "").strip() or "",
                        address=(row[6] if len(row) > 6 else "").strip() or "",
                    )
                    db.session.add(c)
                    count += 1
                db.session.commit()
                flash(f"거래처 {count}건이 일괄 등록되었습니다.", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"업로드 실패: {e}", "danger")
            return redirect(url_for("customer_list"))
        return render_template("customers/upload.html")

    @app.route("/customers/sample-csv")
    def customer_sample_csv():
        si = io.StringIO()
        w = csv.writer(si)
        w.writerow(["거래처명", "사업자등록번호", "업태", "종목", "전화번호", "대표자", "주소"])
        w.writerow(["(주)예시회사", "123-45-67890", "제조업", "전자제품", "02-1234-5678", "홍길동", "서울시 강남구"])
        data = si.getvalue().encode("utf-8-sig")
        buf = io.BytesIO(data)
        return send_file(buf, mimetype="text/csv", as_attachment=True, download_name="customers_sample.csv")

    # ----- Items -----
    @app.route("/items")
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

    @app.route("/items/add", methods=["GET", "POST"])
    def item_add():
        if request.method == "POST":
            price = request.form.get("unit_price", "0").replace(",", "")
            try:
                price = int(price)
            except ValueError:
                price = 0
            item = Item(
                code=_next_item_code(),
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
            return redirect(url_for("item_list"))
        return render_template("items/form.html", item=None, has_image=False)

    @app.route("/items/<int:id>/edit", methods=["GET", "POST"])
    def item_edit(id):
        item = Item.query.get_or_404(id)
        if item.code == "DIRECT":
            flash("직접입력 품목은 수정할 수 없습니다.", "danger")
            return redirect(url_for("item_list"))
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
            return redirect(url_for("item_list"))
        return render_template("items/form.html", item=item, has_image=item.image_path and os.path.isfile(item.image_path) if item else False)

    def _save_item_image(item, request):
        f = request.files.get("image")
        if f and f.filename and f.filename.rsplit(".", 1)[-1].lower() in ("png", "jpg", "jpeg", "gif", "webp"):
            upload_dir = os.path.join(current_app.instance_path, "uploads", "items")
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

    @app.route("/items/<int:id>/image")
    def item_image(id):
        item = Item.query.get_or_404(id)
        if not item.image_path or not os.path.isfile(item.image_path):
            return "", 404
        ext = item.image_path.rsplit(".", 1)[-1].lower()
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/png")
        return send_file(item.image_path, mimetype=mime)

    @app.route("/items/<int:id>/delete", methods=["POST"])
    def item_delete(id):
        item = Item.query.get_or_404(id)
        if item.code == "DIRECT":
            flash("직접입력 품목은 삭제할 수 없습니다.", "danger")
            return redirect(url_for("item_list"))
        db.session.delete(item)
        db.session.commit()
        flash("품목이 삭제되었습니다.", "success")
        return redirect(url_for("item_list"))

    @app.route("/items/upload", methods=["GET", "POST"])
    def item_upload():
        if request.method == "POST":
            f = request.files.get("file")
            if not f or not f.filename or not f.filename.lower().endswith((".csv", ".txt")):
                flash("CSV 파일을 선택해 주세요.", "danger")
                return redirect(url_for("item_upload"))
            try:
                stream = io.StringIO(f.stream.read().decode("utf-8-sig"))
                reader = csv.reader(stream)
                header = next(reader, None)
                if not header:
                    flash("파일 내용이 비어 있습니다.", "danger")
                    return redirect(url_for("item_upload"))
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
            return redirect(url_for("item_list"))
        return render_template("items/upload.html")

    @app.route("/items/sample-csv")
    def item_sample_csv():
        si = io.StringIO()
        w = csv.writer(si)
        w.writerow(["품목명", "규격", "단위", "단가"])
        w.writerow(["상품A", "#6, 100*100", "EA", "1100"])
        w.writerow(["상품B", "", "BOX", "5500"])
        data = si.getvalue().encode("utf-8-sig")
        buf = io.BytesIO(data)
        return send_file(buf, mimetype="text/csv", as_attachment=True, download_name="items_sample.csv")

    @app.route("/inventory")
    def inventory_list():
        items = Item.query.filter(Item.code != "DIRECT").order_by(Item.name).all()
        return render_template("inventory/list.html", items=items)

    # ----- API: item unit_price -----
    @app.route("/api/item/<int:id>")
    def api_item(id):
        item = Item.query.get_or_404(id)
        return {"id": item.id, "name": item.name, "spec": item.spec or "", "unit": item.unit, "unit_price": item.unit_price}

    # ----- Transactions -----
    @app.route("/transactions")
    @app.route("/transactions/list/<list_type>")
    def transaction_list(list_type=None):
        from datetime import date
        today = date.today()
        q = request.args.get("q", "").strip()
        customer_id = request.args.get("customer_id", type=int)
        gubun = request.args.get("gubun", "").strip()
        status = request.args.get("status", "").strip()
        date_from = request.args.get("date_from", "").strip()
        date_to = request.args.get("date_to", "").strip()
        view = request.args.get("view", "list")
        page = request.args.get("page", 1, type=int)
        per_page = 10

        # 기간 기본값: 당해 1월1일 ~ 12월31일 (파라미터 없을 때만)
        if not date_from and not date_to:
            date_from = f"{today.year}-01-01"
            date_to = f"{today.year}-12-31"

        # list_type에 따른 기본 status 및 제목
        list_titles = {"order": "주문내역", "estimate": "견적내역", "delivery": "납품내역", "claim": "청구내역", "statement": "거래명세서내역"}
        if list_type and list_type in list_titles:
            list_title = list_titles[list_type]
            if list_type != "statement" and list_type != "order" and not status:
                status = list_type
        else:
            list_title = "주문내역"

        # 매출 통계 (필터 적용 전 전체 데이터 기준)
        year_txs = Transaction.query.filter(extract("year", Transaction.transaction_date) == today.year).all()
        month_txs = Transaction.query.filter(
            extract("year", Transaction.transaction_date) == today.year,
            extract("month", Transaction.transaction_date) == today.month,
        ).all()
        sales_year = sum(t.total_amount for t in year_txs)
        sales_month = sum(t.total_amount for t in month_txs)

        # 주문 수량 통계 (필터 적용 전)
        all_txs = Transaction.query.all()
        cnt_total = len(all_txs)
        cnt_estimate = sum(1 for t in all_txs if t.estimate_date)
        cnt_delivery = sum(1 for t in all_txs if t.delivery_date)
        cnt_claim = sum(1 for t in all_txs if t.claim_date)
        cnt_confirmed = cnt_total  # 주문확정 = 전체

        query = Transaction.query.join(Customer)
        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(
                    Customer.name.ilike(like),
                    Transaction.memo.ilike(like),
                    Transaction.project_name.ilike(like),
                )
            )
        if customer_id:
            query = query.filter(Transaction.customer_id == customer_id)
        if gubun:
            query = query.filter(Customer.gubun == gubun)
        if date_from:
            try:
                df = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(Transaction.transaction_date >= df)
            except ValueError:
                pass
        if date_to:
            try:
                dt = datetime.strptime(date_to, "%Y-%m-%d").date()
                query = query.filter(Transaction.transaction_date <= dt)
            except ValueError:
                pass
        if status:
            if status == "estimate":
                query = query.filter(Transaction.estimate_date.isnot(None))
            elif status == "delivery":
                query = query.filter(Transaction.delivery_date.isnot(None))
            elif status == "claim":
                query = query.filter(Transaction.claim_date.isnot(None))

        pagination = query.order_by(Transaction.transaction_date.desc()).paginate(page=page, per_page=per_page)
        transactions = pagination.items
        items_summaries = {}
        for t in transactions:
            parts = []
            for ti in t.items:
                name = ti.item_name_custom or (ti.item.name if ti.item else "-")
                parts.append(f"{name}×{ti.quantity}")
            s = ", ".join(parts) if parts else "-"
            items_summaries[t.id] = s[:35] + "등" if len(s) > 35 else s

        customers = Customer.query.order_by(Customer.name).all()
        return render_template(
            "transactions/list.html",
            transactions=transactions,
            pagination=pagination,
            q=q,
            customer_id=customer_id,
            gubun=gubun,
            status=status,
            date_from=date_from,
            date_to=date_to,
            view=view,
            list_title=list_title,
            list_type=list_type,
            items_summaries=items_summaries,
            sales_year=sales_year,
            sales_month=sales_month,
            cnt_total=cnt_total,
            cnt_confirmed=cnt_confirmed,
            cnt_estimate=cnt_estimate,
            cnt_delivery=cnt_delivery,
            cnt_claim=cnt_claim,
            customers=customers,
        )

    @app.route("/transactions/add", methods=["GET", "POST"])
    def transaction_add():
        if request.method == "POST":
            customer_id = request.form.get("customer_id", type=int)
            date_str = request.form.get("transaction_date")
            project_name = request.form.get("project_name", "").strip() or None
            memo = request.form.get("memo", "").strip() or None
            if not customer_id or not date_str:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify(ok=False, error="거래처와 거래일자를 입력하세요.")
                flash("거래처와 거래일자를 입력하세요.", "danger")
                return redirect(url_for("transaction_add"))
            try:
                trans_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                trans_date = datetime.utcnow().date()
            t = Transaction(
                code=_next_transaction_code(),
                customer_id=customer_id,
                transaction_date=trans_date,
                project_name=project_name,
                memo=memo,
            )
            db.session.add(t)
            db.session.flush()
            item_ids = _parse_int_list(request, "item_id[]")
            quantities = _parse_int_list(request, "quantity[]")
            item_names_custom = request.form.getlist("item_name_custom[]")
            spec_custom_list = request.form.getlist("spec_custom[]")
            unit_custom_list = request.form.getlist("unit_custom[]")
            vat_excluded = request.form.get("vat_excluded") == "1"
            direct_item = _direct_input_item()
            for i, (item_id, qty) in enumerate(zip(item_ids, quantities)):
                if item_id <= 0 or qty <= 0:
                    continue
                item = Item.query.get(item_id)
                if not item:
                    continue
                unit_price = request.form.get(f"unit_price_{i}", type=int) or 0
                if item.id == direct_item.id:
                    item_name_custom = (item_names_custom[i] or "").strip() if i < len(item_names_custom) else None
                    if not item_name_custom:
                        continue
                    spec_custom = (spec_custom_list[i] or "").strip() if i < len(spec_custom_list) else None
                    unit_custom = (unit_custom_list[i] or "").strip() if i < len(unit_custom_list) else None
                else:
                    item_name_custom = None
                    spec_custom = None
                    unit_custom = None
                total = unit_price * qty
                if vat_excluded:
                    supply, vat = total, 0
                else:
                    supply = int(total / 1.1) if total else 0
                    vat = total - supply
                ti = TransactionItem(
                    transaction_id=t.id,
                    item_id=item_id,
                    item_name_custom=item_name_custom,
                    spec_custom=spec_custom,
                    unit_custom=unit_custom,
                    quantity=qty,
                    unit_price=unit_price,
                    supply_amount=supply,
                    vat=vat,
                    total=total,
                )
                db.session.add(ti)
            db.session.commit()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify(ok=True, redirect=url_for("transaction_list"))
            flash("주문이 등록되었습니다.", "success")
            return redirect(url_for("transaction_list"))
        customers = Customer.query.order_by(Customer.name).all()
        items = Item.query.order_by(Item.name).all()
        direct_item = _direct_input_item()
        default_date = datetime.utcnow().date().isoformat()
        return render_template(
            "transactions/form.html",
            transaction=None,
            customers=customers,
            items=items,
            direct_item=direct_item,
            default_date=default_date,
            vat_excluded_initial=False,
        )

    @app.route("/transactions/<int:id>/edit", methods=["GET", "POST"])
    def transaction_edit(id):
        t = Transaction.query.get_or_404(id)
        if request.method == "POST":
            t.customer_id = request.form.get("customer_id", type=int) or t.customer_id
            date_str = request.form.get("transaction_date")
            if date_str:
                try:
                    t.transaction_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass
            t.project_name = request.form.get("project_name", "").strip() or None
            t.memo = request.form.get("memo", "").strip() or None
            # 견적/납품/청구 일자 및 완료 상태
            if request.form.get("estimate_complete") == "1":
                est_str = request.form.get("estimate_date")
                if est_str:
                    try:
                        t.estimate_date = datetime.strptime(est_str, "%Y-%m-%d").date()
                    except ValueError:
                        t.estimate_date = t.transaction_date
                else:
                    t.estimate_date = t.transaction_date
            else:
                t.estimate_date = None
            if request.form.get("delivery_complete") == "1":
                del_str = request.form.get("delivery_date")
                if del_str:
                    try:
                        t.delivery_date = datetime.strptime(del_str, "%Y-%m-%d").date()
                    except ValueError:
                        t.delivery_date = t.transaction_date
                else:
                    t.delivery_date = t.transaction_date
            else:
                t.delivery_date = None
            if request.form.get("claim_complete") == "1":
                claim_str = request.form.get("claim_date")
                if claim_str:
                    try:
                        t.claim_date = datetime.strptime(claim_str, "%Y-%m-%d").date()
                    except ValueError:
                        t.claim_date = t.transaction_date
                else:
                    t.claim_date = t.transaction_date
            else:
                t.claim_date = None
            for ti in list(t.items):
                db.session.delete(ti)
            db.session.flush()
            item_ids = _parse_int_list(request, "item_id[]")
            quantities = _parse_int_list(request, "quantity[]")
            item_names_custom = request.form.getlist("item_name_custom[]")
            spec_custom_list = request.form.getlist("spec_custom[]")
            unit_custom_list = request.form.getlist("unit_custom[]")
            vat_excluded = request.form.get("vat_excluded") == "1"
            direct_item = _direct_input_item()
            for i, (item_id, qty) in enumerate(zip(item_ids, quantities)):
                if item_id <= 0 or qty <= 0:
                    continue
                item = Item.query.get(item_id)
                if not item:
                    continue
                unit_price = request.form.get(f"unit_price_{i}", type=int) or 0
                if item.id == direct_item.id:
                    item_name_custom = (item_names_custom[i] or "").strip() if i < len(item_names_custom) else None
                    if not item_name_custom:
                        continue
                    spec_custom = (spec_custom_list[i] or "").strip() if i < len(spec_custom_list) else None
                    unit_custom = (unit_custom_list[i] or "").strip() if i < len(unit_custom_list) else None
                else:
                    item_name_custom = None
                    spec_custom = None
                    unit_custom = None
                total = unit_price * qty
                if vat_excluded:
                    supply, vat = total, 0
                else:
                    supply = int(total / 1.1) if total else 0
                    vat = total - supply
                ti = TransactionItem(
                    transaction_id=t.id,
                    item_id=item_id,
                    item_name_custom=item_name_custom,
                    spec_custom=spec_custom,
                    unit_custom=unit_custom,
                    quantity=qty,
                    unit_price=unit_price,
                    supply_amount=supply,
                    vat=vat,
                    total=total,
                )
                db.session.add(ti)
            db.session.commit()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify(ok=True, redirect=url_for("transaction_edit", id=id))
            flash("주문이 수정되었습니다.", "success")
            return redirect(url_for("transaction_edit", id=id))
        customers = Customer.query.order_by(Customer.name).all()
        items = Item.query.order_by(Item.name).all()
        direct_item = _direct_input_item()
        default_date = datetime.utcnow().date().isoformat()
        vat_excluded_initial = t.items and not any(ti.vat > 0 for ti in t.items)
        is_editable = request.args.get("edit") == "1"
        return render_template(
            "transactions/form.html",
            transaction=t,
            customers=customers,
            items=items,
            direct_item=direct_item,
            default_date=default_date,
            vat_excluded_initial=vat_excluded_initial,
            is_editable=is_editable,
        )

    @app.route("/transactions/<int:id>/delete", methods=["POST"])
    def transaction_delete(id):
        t = Transaction.query.get_or_404(id)
        db.session.delete(t)
        db.session.commit()
        flash("주문이 삭제되었습니다.", "success")
        return redirect(url_for("transaction_list"))

    @app.route("/transactions/<int:id>/date", methods=["PATCH"])
    def transaction_update_date(id):
        t = Transaction.query.get_or_404(id)
        data = request.get_json(silent=True) or {}
        date_str = data.get("transaction_date")
        doc_type = data.get("doc_type")  # gyeonjeok(견적서), napum(납품서), cheonggu(청구서)
        if not date_str:
            return jsonify({"ok": False, "error": "날짜가 필요합니다."}), 400
        try:
            trans_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"ok": False, "error": "날짜 형식이 올바르지 않습니다."}), 400
        if doc_type == "gyeonjeok":
            t.estimate_date = trans_date
        elif doc_type == "napum":
            t.delivery_date = trans_date
        elif doc_type == "cheonggu":
            t.claim_date = trans_date
        else:
            t.transaction_date = trans_date
        db.session.commit()
        return jsonify({"ok": True})

    @app.route("/transactions/delete-bulk", methods=["POST"])
    def transaction_delete_bulk():
        ids = request.form.getlist("ids", type=int)
        if not ids:
            flash("삭제할 주문을 선택하세요.", "danger")
            return redirect(url_for("transaction_list"))
        total = Transaction.query.count()
        if len(ids) >= total:
            flash("전체 삭제는 할 수 없습니다.", "danger")
            return redirect(url_for("transaction_list"))
        for tid in ids:
            t = Transaction.query.get(tid)
            if t:
                db.session.delete(t)
        db.session.commit()
        flash(f"주문 {len(ids)}건이 삭제되었습니다.", "success")
        return redirect(url_for("transaction_list"))

    # ----- Print & PDF -----
    def _supplier():
        c = CompanyInfo.query.first()
        if c:
            return {
                "name": c.name or SUPPLIER_NAME,
                "biz_no": c.biz_no or SUPPLIER_BIZ_NO,
                "address": c.address or SUPPLIER_ADDRESS,
                "phone": c.phone or SUPPLIER_PHONE,
                "fax": c.fax or SUPPLIER_FAX,
                "contact": c.contact or SUPPLIER_CONTACT,
                "ceo": c.ceo or "",
                "account_no": c.account_no or "",
                "account_holder": c.account_holder or "",
                "bank": c.bank or "",
                "business_type": c.business_type or "",
                "stamp_path": c.stamp_path if c.stamp_path and os.path.isfile(c.stamp_path) else None,
            }
        return {
            "name": SUPPLIER_NAME,
            "biz_no": SUPPLIER_BIZ_NO,
            "address": SUPPLIER_ADDRESS,
            "phone": SUPPLIER_PHONE,
            "fax": SUPPLIER_FAX,
            "contact": SUPPLIER_CONTACT,
            "ceo": "",
            "account_no": "",
            "account_holder": "",
            "bank": "",
            "business_type": "",
            "stamp_path": None,
        }

    @app.route("/transactions/<int:id>/statement")
    def statement_print(id):
        t = Transaction.query.get_or_404(id)
        rows = _transaction_rows(t)
        total_supply, total_vat, total_amount = _totals(rows)
        popup = request.args.get("popup") == "1"
        show_stamp = request.args.get("stamp") == "1"
        return render_template(
            "print/statement.html",
            transaction=t,
            customer=t.customer,
            rows=rows,
            total_supply=total_supply,
            total_vat=total_vat,
            total_amount=total_amount,
            supplier=_supplier(),
            popup=popup,
            show_stamp=show_stamp,
        )

    @app.route("/transactions/<int:id>/napum")
    def napum_print(id):
        t = Transaction.query.get_or_404(id)
        rows = _transaction_rows(t)
        _, _, total_amount = _totals(rows)
        popup = request.args.get("popup") == "1"
        show_stamp = request.args.get("stamp") == "1"
        return render_template(
            "print/napum.html",
            transaction=t,
            customer=t.customer,
            rows=rows,
            total_amount=total_amount,
            total_amount_korean=amount_to_korean_won(total_amount),
            supplier=_supplier(),
            popup=popup,
            show_stamp=show_stamp,
        )

    @app.route("/transactions/<int:id>/napum/pdf")
    def napum_pdf(id):
        from pdf_utils import build_napum_pdf
        t = Transaction.query.get_or_404(id)
        rows = _transaction_rows(t)
        _, _, total_amount = _totals(rows)
        show_stamp = request.args.get("stamp") == "1"
        buf = build_napum_pdf(t, t.customer, rows, total_amount, _supplier(), show_stamp=show_stamp)
        return send_file(
            buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"납품서_{t.transaction_date}_{t.customer.name}.pdf",
        )

    @app.route("/transactions/<int:id>/cheonggu")
    def cheonggu_print(id):
        t = Transaction.query.get_or_404(id)
        rows = _transaction_rows(t)
        _, _, total_amount = _totals(rows)
        popup = request.args.get("popup") == "1"
        show_stamp = request.args.get("stamp") == "1"
        return render_template(
            "print/cheonggu.html",
            transaction=t,
            customer=t.customer,
            rows=rows,
            total_amount=total_amount,
            total_amount_korean=amount_to_korean_won(total_amount),
            supplier=_supplier(),
            popup=popup,
            show_stamp=show_stamp,
        )

    @app.route("/transactions/<int:id>/cheonggu/pdf")
    def cheonggu_pdf(id):
        from pdf_utils import build_cheonggu_pdf
        t = Transaction.query.get_or_404(id)
        rows = _transaction_rows(t)
        _, _, total_amount = _totals(rows)
        show_stamp = request.args.get("stamp") == "1"
        buf = build_cheonggu_pdf(t, t.customer, rows, total_amount, _supplier(), show_stamp=show_stamp)
        return send_file(
            buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"청구서_{t.transaction_date}_{t.customer.name}.pdf",
        )

    @app.route("/transactions/<int:id>/gyeonjeok")
    def gyeonjeok_print(id):
        t = Transaction.query.get_or_404(id)
        rows = _transaction_rows(t)
        total_supply, _, total_amount = _totals(rows)
        popup = request.args.get("popup") == "1"
        show_stamp = request.args.get("stamp") == "1"
        return render_template(
            "print/gyeonjeok.html",
            transaction=t,
            customer=t.customer,
            rows=rows,
            total_supply=total_supply,
            total_amount=total_amount,
            total_amount_korean=amount_to_korean_won(total_amount),
            supplier=_supplier(),
            popup=popup,
            show_stamp=show_stamp,
        )

    @app.route("/transactions/<int:id>/gyeonjeok/pdf")
    def gyeonjeok_pdf(id):
        from pdf_utils import build_gyeonjeok_pdf
        t = Transaction.query.get_or_404(id)
        rows = _transaction_rows(t)
        total_supply, _, total_amount = _totals(rows)
        show_stamp = request.args.get("stamp") == "1"
        buf = build_gyeonjeok_pdf(t, t.customer, rows, total_supply, total_amount, _supplier(), show_stamp=show_stamp)
        return send_file(
            buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"견적서_{t.transaction_date}_{t.customer.name}.pdf",
        )

    @app.route("/transactions/<int:id>/tax-invoice")
    def tax_invoice_print(id):
        """세금계산서 (표준 세금계산서 양식)"""
        t = Transaction.query.get_or_404(id)
        rows = _transaction_rows(t)
        total_supply, total_vat, total_amount = _totals(rows)
        popup = request.args.get("popup") == "1"
        show_stamp = request.args.get("stamp") == "1"
        return render_template(
            "print/tax.html",
            transaction=t,
            customer=t.customer,
            rows=rows,
            total_supply=total_supply,
            total_vat=total_vat,
            total_amount=total_amount,
            supplier=_supplier(),
            popup=popup,
            show_stamp=show_stamp,
        )
