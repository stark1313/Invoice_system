from flask import Blueprint, redirect, url_for

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return redirect(url_for("transactions.transaction_list"))


@bp.route("/health")
def health():
    return "ok", 200
