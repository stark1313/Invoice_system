from flask import request

from extensions import db
from models import Item, TransactionItem


def parse_int_list(req, name, default=0):
    out = []
    for v in req.form.getlist(name):
        try:
            out.append(int(v) if v else default)
        except (ValueError, TypeError):
            out.append(default)
    return out


def direct_input_item():
    """직접입력용 placeholder Item (없으면 생성)"""
    item = Item.query.filter(Item.code == "DIRECT").first()
    if not item:
        item = Item(code="DIRECT", name="직접입력", unit="EA", unit_price=0)
        db.session.add(item)
        db.session.commit()
    return item


def build_transaction_items_from_form(transaction, req):
    """주문 품목 행을 세션에 추가한다. (기존 TransactionItem 삭제는 호출 측에서 처리)"""
    item_ids = parse_int_list(req, "item_id[]")
    quantities = parse_int_list(req, "quantity[]")
    item_names_custom = req.form.getlist("item_name_custom[]")
    spec_custom_list = req.form.getlist("spec_custom[]")
    unit_custom_list = req.form.getlist("unit_custom[]")
    vat_excluded = req.form.get("vat_excluded") == "1"
    direct_item = direct_input_item()
    for i, (item_id, qty) in enumerate(zip(item_ids, quantities)):
        if item_id <= 0 or qty <= 0:
            continue
        item = Item.query.get(item_id)
        if not item:
            continue
        unit_price = req.form.get(f"unit_price_{i}", type=int) or 0
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
            transaction_id=transaction.id,
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


def transaction_rows(t):
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


def totals(rows):
    total_supply = sum(r["supply_amount"] for r in rows)
    total_vat = sum(r["vat"] for r in rows)
    total_amount = sum(r["total"] for r in rows)
    return total_supply, total_vat, total_amount
