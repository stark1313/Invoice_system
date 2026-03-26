from extensions import db
from models import Customer, Document, Item, Transaction


def next_customer_code():
    r = db.session.query(db.func.max(Customer.code)).filter(Customer.code.like("C%")).scalar()
    n = int(r[1:]) + 1 if r and len(r) > 1 and r[1:].isdigit() else 1
    return f"C{n:06d}"


def next_transaction_code():
    r = db.session.query(db.func.max(Transaction.code)).filter(Transaction.code.like("B%")).scalar()
    n = int(r[1:]) + 1 if r and len(r) > 1 and r[1:].isdigit() else 1
    return f"B{n:06d}"


def next_item_code():
    r = db.session.query(db.func.max(Item.code)).filter(Item.code.like("P%")).scalar()
    n = int(r[1:]) + 1 if r and len(r) > 1 and r[1:].isdigit() else 1
    return f"P{n:06d}"


def next_document_code():
    r = db.session.query(db.func.max(Document.code)).filter(Document.code.like("D%")).scalar()
    n = int(r[1:]) + 1 if r and len(r) > 1 and r[1:].isdigit() else 1
    return f"D{n:06d}"
