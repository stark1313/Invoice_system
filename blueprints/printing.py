from flask import Blueprint, render_template, request, send_file

from utils import amount_to_korean_won
from supplier_helpers import get_supplier
from transaction_helpers import totals, transaction_rows
from models import Transaction

bp = Blueprint("printing", __name__)


@bp.route("/transactions/<int:id>/statement")
def statement_print(id):
    t = Transaction.query.get_or_404(id)
    rows = transaction_rows(t)
    total_supply, total_vat, total_amount = totals(rows)
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
        supplier=get_supplier(),
        popup=popup,
        show_stamp=show_stamp,
    )


@bp.route("/transactions/<int:id>/napum")
def napum_print(id):
    t = Transaction.query.get_or_404(id)
    rows = transaction_rows(t)
    _, _, total_amount = totals(rows)
    popup = request.args.get("popup") == "1"
    show_stamp = request.args.get("stamp") == "1"
    return render_template(
        "print/napum.html",
        transaction=t,
        customer=t.customer,
        rows=rows,
        total_amount=total_amount,
        total_amount_korean=amount_to_korean_won(total_amount),
        supplier=get_supplier(),
        popup=popup,
        show_stamp=show_stamp,
    )


@bp.route("/transactions/<int:id>/napum/pdf")
def napum_pdf(id):
    from pdf_utils import build_napum_pdf

    t = Transaction.query.get_or_404(id)
    rows = transaction_rows(t)
    _, _, total_amount = totals(rows)
    show_stamp = request.args.get("stamp") == "1"
    buf = build_napum_pdf(t, t.customer, rows, total_amount, get_supplier(), show_stamp=show_stamp)
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"납품서_{t.transaction_date}_{t.customer.name}.pdf",
    )


@bp.route("/transactions/<int:id>/cheonggu")
def cheonggu_print(id):
    t = Transaction.query.get_or_404(id)
    rows = transaction_rows(t)
    _, _, total_amount = totals(rows)
    popup = request.args.get("popup") == "1"
    show_stamp = request.args.get("stamp") == "1"
    return render_template(
        "print/cheonggu.html",
        transaction=t,
        customer=t.customer,
        rows=rows,
        total_amount=total_amount,
        total_amount_korean=amount_to_korean_won(total_amount),
        supplier=get_supplier(),
        popup=popup,
        show_stamp=show_stamp,
    )


@bp.route("/transactions/<int:id>/cheonggu/pdf")
def cheonggu_pdf(id):
    from pdf_utils import build_cheonggu_pdf

    t = Transaction.query.get_or_404(id)
    rows = transaction_rows(t)
    _, _, total_amount = totals(rows)
    show_stamp = request.args.get("stamp") == "1"
    buf = build_cheonggu_pdf(t, t.customer, rows, total_amount, get_supplier(), show_stamp=show_stamp)
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"청구서_{t.transaction_date}_{t.customer.name}.pdf",
    )


@bp.route("/transactions/<int:id>/gyeonjeok")
def gyeonjeok_print(id):
    t = Transaction.query.get_or_404(id)
    rows = transaction_rows(t)
    total_supply, _, total_amount = totals(rows)
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
        supplier=get_supplier(),
        popup=popup,
        show_stamp=show_stamp,
    )


@bp.route("/transactions/<int:id>/gyeonjeok/pdf")
def gyeonjeok_pdf(id):
    from pdf_utils import build_gyeonjeok_pdf

    t = Transaction.query.get_or_404(id)
    rows = transaction_rows(t)
    total_supply, _, total_amount = totals(rows)
    show_stamp = request.args.get("stamp") == "1"
    buf = build_gyeonjeok_pdf(t, t.customer, rows, total_supply, total_amount, get_supplier(), show_stamp=show_stamp)
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"견적서_{t.transaction_date}_{t.customer.name}.pdf",
    )


@bp.route("/transactions/<int:id>/tax-invoice")
def tax_invoice_print(id):
    t = Transaction.query.get_or_404(id)
    rows = transaction_rows(t)
    total_supply, total_vat, total_amount = totals(rows)
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
        supplier=get_supplier(),
        popup=popup,
        show_stamp=show_stamp,
    )
