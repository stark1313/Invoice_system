from datetime import datetime
from extensions import db


class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True)
    gubun = db.Column(db.String(20), default="일반")
    name = db.Column(db.String(200), nullable=False)
    biz_no = db.Column(db.String(20))
    business_type = db.Column(db.String(100))
    business_item = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    address = db.Column(db.String(500))
    ceo = db.Column(db.String(100))
    remarks = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    transactions = db.relationship("Transaction", backref="customer", lazy=True)


class Item(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True)
    name = db.Column(db.String(200), nullable=False)
    spec = db.Column(db.String(100))
    unit = db.Column(db.String(20), default="EA")
    unit_price = db.Column(db.Integer, default=0)
    image_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Transaction(db.Model):
    __tablename__ = "transactions"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    transaction_date = db.Column(db.Date, nullable=False)
    estimate_date = db.Column(db.Date)
    delivery_date = db.Column(db.Date)
    claim_date = db.Column(db.Date)
    project_name = db.Column(db.String(500))
    memo = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = db.relationship("TransactionItem", backref="transaction", lazy=True, cascade="all, delete-orphan")

    @property
    def total_amount(self):
        return sum(ti.total for ti in self.items)


class CompanyInfo(db.Model):
    __tablename__ = "company_info"
    id = db.Column(db.Integer, primary_key=True)
    biz_no = db.Column(db.String(20))
    name = db.Column(db.String(200))
    ceo = db.Column(db.String(100))
    address = db.Column(db.String(500))
    phone = db.Column(db.String(50))
    fax = db.Column(db.String(50))
    account_no = db.Column(db.String(50))
    account_holder = db.Column(db.String(100))
    bank = db.Column(db.String(100))
    business_type = db.Column(db.String(200))
    stamp_path = db.Column(db.String(500))
    contact = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TransactionItem(db.Model):
    __tablename__ = "transaction_items"
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    item_name_custom = db.Column(db.String(200))
    spec_custom = db.Column(db.String(100))
    unit_custom = db.Column(db.String(20))
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Integer, default=0)
    supply_amount = db.Column(db.Integer, default=0)
    vat = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    item = db.relationship("Item", backref="transaction_items")
