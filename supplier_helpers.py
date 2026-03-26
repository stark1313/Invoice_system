import os

from models import CompanyInfo
from config import (
    SUPPLIER_NAME,
    SUPPLIER_BIZ_NO,
    SUPPLIER_ADDRESS,
    SUPPLIER_PHONE,
    SUPPLIER_FAX,
    SUPPLIER_CONTACT,
)


def get_supplier():
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
