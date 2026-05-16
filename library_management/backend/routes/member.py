from __future__ import annotations
from functools import wraps
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from backend.models.models import get_all_books, get_all_transactions, get_categories

member_bp = Blueprint("member", __name__, url_prefix="/member")


def member_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


@member_bp.route("/dashboard")
@member_required
def dashboard():
    my_txns = get_all_transactions(user_id=session["user_id"])
    active = [t for t in my_txns if t["status"] in ("issued", "overdue")]
    past = [t for t in my_txns if t["status"] == "returned"]
    total_fine = sum(t.get("fine_amount", 0) or 0 for t in my_txns if not t.get("fine_paid"))
    return render_template("member/dashboard.html",
                           active_books=active, past_books=past,
                           total_fine=total_fine)


@member_bp.route("/search")
@member_required
def search():
    query = request.args.get("q", "")
    cat_id = request.args.get("category_id")
    books = get_all_books(search=query, category_id=int(cat_id) if cat_id else None)
    categories = get_categories()
    return render_template("member/search.html", books=books,
                           categories=categories, query=query)


@member_bp.route("/my-books")
@member_required
def my_books():
    txns = get_all_transactions(user_id=session["user_id"])
    return render_template("member/my_books.html", transactions=txns)
