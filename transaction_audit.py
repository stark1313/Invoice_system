from datetime import datetime

from extensions import db
from models import TransactionAuditLog

ACTION_CREATE = "create"
ACTION_UPDATE = "update"
ACTION_DELETE = "delete"
ACTION_PATCH_DATE = "patch_date"


def log_order_event(action, *, transaction_id=None, code="", summary=""):
    """주문 감사 로그 1건 (호출 후 같은 트랜잭션에서 commit 하면 됨)"""
    row = TransactionAuditLog(
        transaction_id=transaction_id,
        transaction_code=(code or "")[:20],
        action=action[:32],
        summary=(summary or "")[:500],
        created_at=datetime.utcnow(),
    )
    db.session.add(row)
