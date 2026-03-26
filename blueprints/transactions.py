from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy import extract, func, or_

from codegen import next_transaction_code
from extensions import db
from models import Customer, Item, Transaction, TransactionItem
from transaction_helpers import build_transaction_items_from_form, direct_input_item

bp = Blueprint("transactions", __name__)


@bp.route("/transactions")
@bp.route("/transactions/list/<list_type>")
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

    if not date_from and not date_to:
        date_from = f"{today.year}-01-01"
        date_to = f"{today.year}-12-31"

    list_titles = {"order": "주문내역", "estimate": "견적내역", "delivery": "납품내역", "claim": "청구내역", "statement": "거래명세서내역"}
    if list_type and list_type in list_titles:
        list_title = list_titles[list_type]
        if list_type != "statement" and list_type != "order" and not status:
            status = list_type
    else:
        list_title = "주문내역"

    sales_year = int(
        db.session.query(func.coalesce(func.sum(TransactionItem.total), 0))
        .join(Transaction, TransactionItem.transaction_id == Transaction.id)
        .filter(extract("year", Transaction.transaction_date) == today.year)
        .scalar()
        or 0
    )
    sales_month = int(
        db.session.query(func.coalesce(func.sum(TransactionItem.total), 0))
        .join(Transaction, TransactionItem.transaction_id == Transaction.id)
        .filter(
            extract("year", Transaction.transaction_date) == today.year,
            extract("month", Transaction.transaction_date) == today.month,
        )
        .scalar()
        or 0
    )

    cnt_total = db.session.query(func.count(Transaction.id)).scalar() or 0
    cnt_estimate = (
        db.session.query(func.count(Transaction.id)).filter(Transaction.estimate_date.isnot(None)).scalar() or 0
    )
    cnt_delivery = (
        db.session.query(func.count(Transaction.id)).filter(Transaction.delivery_date.isnot(None)).scalar() or 0
    )
    cnt_claim = db.session.query(func.count(Transaction.id)).filter(Transaction.claim_date.isnot(None)).scalar() or 0
    cnt_confirmed = cnt_total

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


@bp.route("/transactions/add", methods=["GET", "POST"])
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
            return redirect(url_for("transactions.transaction_add"))
        try:
            trans_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            trans_date = datetime.utcnow().date()
        t = Transaction(
            code=next_transaction_code(),
            customer_id=customer_id,
            transaction_date=trans_date,
            project_name=project_name,
            memo=memo,
        )
        db.session.add(t)
        db.session.flush()
        build_transaction_items_from_form(t, request)
        db.session.commit()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(ok=True, redirect=url_for("transactions.transaction_list"))
        flash("주문이 등록되었습니다.", "success")
        return redirect(url_for("transactions.transaction_list"))
    customers = Customer.query.order_by(Customer.name).all()
    items = Item.query.order_by(Item.name).all()
    direct_item = direct_input_item()
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


@bp.route("/transactions/<int:id>/edit", methods=["GET", "POST"])
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
        build_transaction_items_from_form(t, request)
        db.session.commit()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(ok=True, redirect=url_for("transactions.transaction_edit", id=id))
        flash("주문이 수정되었습니다.", "success")
        return redirect(url_for("transactions.transaction_edit", id=id))
    customers = Customer.query.order_by(Customer.name).all()
    items = Item.query.order_by(Item.name).all()
    direct_item = direct_input_item()
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


@bp.route("/transactions/<int:id>/delete", methods=["POST"])
def transaction_delete(id):
    t = Transaction.query.get_or_404(id)
    db.session.delete(t)
    db.session.commit()
    flash("주문이 삭제되었습니다.", "success")
    return redirect(url_for("transactions.transaction_list"))


@bp.route("/transactions/<int:id>/date", methods=["PATCH"])
def transaction_update_date(id):
    t = Transaction.query.get_or_404(id)
    data = request.get_json(silent=True) or {}
    date_str = data.get("transaction_date")
    doc_type = data.get("doc_type")
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


@bp.route("/transactions/delete-bulk", methods=["POST"])
def transaction_delete_bulk():
    ids = request.form.getlist("ids", type=int)
    if not ids:
        flash("삭제할 주문을 선택하세요.", "danger")
        return redirect(url_for("transactions.transaction_list"))
    total = Transaction.query.count()
    if len(ids) >= total:
        flash("전체 삭제는 할 수 없습니다.", "danger")
        return redirect(url_for("transactions.transaction_list"))
    for tid in ids:
        t = Transaction.query.get(tid)
        if t:
            db.session.delete(t)
    db.session.commit()
    flash(f"주문 {len(ids)}건이 삭제되었습니다.", "success")
    return redirect(url_for("transactions.transaction_list"))
