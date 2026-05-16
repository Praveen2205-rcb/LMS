from __future__ import annotations
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from backend.models.models import (get_all_books, get_all_members, get_all_transactions,
                                    get_transaction, issue_book, return_book,
                                    get_dashboard_stats, update_overdue_status)
from backend.utils.logger import log_action

librarian_bp = Blueprint("librarian", __name__, url_prefix="/librarian")


def librarian_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") not in ("admin", "librarian"):
            flash("Librarian access required.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


@librarian_bp.route("/dashboard")
@librarian_required
def dashboard():
    update_overdue_status()
    stats = get_dashboard_stats()
    recent_txns = get_all_transactions()[:10]
    return render_template("librarian/dashboard.html", stats=stats, recent_txns=recent_txns)


@librarian_bp.route("/issue", methods=["GET", "POST"])
@librarian_required
def issue():
    books = get_all_books()
    members = get_all_members()
    if request.method == "POST":
        book_id = int(request.form["book_id"])
        user_id = int(request.form["user_id"])
        days = int(request.form.get("loan_days", 14))
        txn_id = issue_book(book_id, user_id, session["user_id"], days)
        if txn_id:
            log_action(session["user_id"], "ISSUE_BOOK", "transaction", txn_id,
                       f"Issued book {book_id} to user {user_id}", request.remote_addr)
            flash(f"Book issued successfully! Transaction ID: {txn_id}", "success")
            return redirect(url_for("librarian.dashboard"))
        else:
            flash("Book not available or invalid selection.", "error")
    return render_template("librarian/issue.html", books=books, members=members)


@librarian_bp.route("/return", methods=["GET", "POST"])
@librarian_required
def return_book_view():
    active_txns = get_all_transactions(status="issued")
    overdue_txns = get_all_transactions(status="overdue")
    all_active = active_txns + overdue_txns
    result = None
    if request.method == "POST":
        txn_id = int(request.form["transaction_id"])
        result = return_book(txn_id, session["user_id"])
        if "error" not in result:
            log_action(session["user_id"], "RETURN_BOOK", "transaction", txn_id,
                       f"Book returned, fine: ₹{result['fine']}", request.remote_addr)
            flash(f"Book returned! Fine: ₹{result['fine']:.2f}", "success" if result["fine"] == 0 else "warning")
            return redirect(url_for("librarian.return_book_view"))
        else:
            flash(result["error"], "error")
    return render_template("librarian/return.html", transactions=all_active, result=result)


@librarian_bp.route("/members")
@librarian_required
def members():
    search = request.args.get("search", "")
    from backend.models.models import get_all_members
    members_list = get_all_members(search=search)
    return render_template("librarian/members.html", members=members_list, search=search)


@librarian_bp.route("/members/<int:user_id>")
@librarian_required
def member_detail(user_id: int):
    from backend.models.models import get_user, get_all_transactions
    member = get_user(user_id)
    if not member:
        flash("Member not found.", "error")
        return redirect(url_for("librarian.members"))
    txns = get_all_transactions(user_id=user_id)
    return render_template("librarian/member_detail.html", member=member, transactions=txns)
