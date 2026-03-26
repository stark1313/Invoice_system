import csv
import io

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, url_for
from sqlalchemy import or_

from codegen import next_customer_code
from extensions import db
from models import Customer

bp = Blueprint("customers", __name__)


@bp.route("/customers")
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


@bp.route("/customers/add", methods=["GET", "POST"])
def customer_add():
    if request.method == "POST":
        gubun = request.form.get("gubun", "").strip() or "일반"
        if gubun not in ("일반", "관급"):
            gubun = "일반"
        c = Customer(
            code=next_customer_code(),
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
        return redirect(url_for("customers.customer_list"))
    return render_template("customers/form.html", customer=None)


@bp.route("/customers/<int:id>/edit", methods=["GET", "POST"])
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
        return redirect(url_for("customers.customer_list"))
    return render_template("customers/form.html", customer=customer)


@bp.route("/customers/<int:id>/delete", methods=["POST"])
def customer_delete(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    flash("거래처가 삭제되었습니다.", "success")
    return redirect(url_for("customers.customer_list"))


@bp.route("/customers/upload", methods=["GET", "POST"])
def customer_upload():
    if request.method == "POST":
        f = request.files.get("file")
        if not f or not f.filename or not f.filename.lower().endswith((".csv", ".txt")):
            flash("CSV 파일을 선택해 주세요.", "danger")
            return redirect(url_for("customers.customer_upload"))
        try:
            stream = io.StringIO(f.stream.read().decode("utf-8-sig"))
            reader = csv.reader(stream)
            header = next(reader, None)
            if not header:
                flash("파일 내용이 비어 있습니다.", "danger")
                return redirect(url_for("customers.customer_upload"))
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
        return redirect(url_for("customers.customer_list"))
    return render_template("customers/upload.html")


@bp.route("/customers/sample-csv")
def customer_sample_csv():
    si = io.StringIO()
    w = csv.writer(si)
    w.writerow(["거래처명", "사업자등록번호", "업태", "종목", "전화번호", "대표자", "주소"])
    w.writerow(["(주)예시회사", "123-45-67890", "제조업", "전자제품", "02-1234-5678", "홍길동", "서울시 강남구"])
    data = si.getvalue().encode("utf-8-sig")
    buf = io.BytesIO(data)
    return send_file(buf, mimetype="text/csv", as_attachment=True, download_name="customers_sample.csv")
