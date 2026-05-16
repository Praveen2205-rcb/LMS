from __future__ import annotations
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash
from backend.models.models import (get_all_books, get_book, add_book, update_book, delete_book,
                                    get_all_members, get_user, add_member, update_member,
                                    get_all_transactions, get_categories, get_dashboard_stats,
                                    get_recent_activity)
from backend.utils.logger import log_action
from backend.utils.report_generator import generate_full_report

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    stats = get_dashboard_stats()
    activity = get_recent_activity(10)
    return render_template("admin/dashboard.html", stats=stats, activity=activity)


# ── BOOKS ─────────────────────────────────────────────────────────────────────

@admin_bp.route("/books")
@admin_required
def books():
    search = request.args.get("search", "")
    cat_id = request.args.get("category_id")
    books_list = get_all_books(search=search, category_id=int(cat_id) if cat_id else None)
    categories = get_categories()
    return render_template("admin/books.html", books=books_list,
                           categories=categories, search=search)


@admin_bp.route("/books/add", methods=["GET", "POST"])
@admin_required
def add_book_view():
    categories = get_categories()
    if request.method == "POST":
        data = {k: v.strip() or None for k, v in request.form.items()}
        try:
            new_id = add_book(data)
            log_action(session["user_id"], "ADD_BOOK", "book", new_id,
                       f"Added book: {data['title']}", request.remote_addr)
            flash(f"Book '{data['title']}' added successfully!", "success")
            return redirect(url_for("admin.books"))
        except Exception as e:
            flash(f"Error adding book: {e}", "error")
    return render_template("admin/book_form.html", book=None, categories=categories, action="Add")


@admin_bp.route("/books/edit/<int:book_id>", methods=["GET", "POST"])
@admin_required
def edit_book_view(book_id: int):
    book = get_book(book_id)
    categories = get_categories()
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for("admin.books"))
    if request.method == "POST":
        data = {k: v.strip() or None for k, v in request.form.items()}
        update_book(book_id, data)
        log_action(session["user_id"], "UPDATE_BOOK", "book", book_id,
                   f"Updated book ID {book_id}", request.remote_addr)
        flash("Book updated successfully!", "success")
        return redirect(url_for("admin.books"))
    return render_template("admin/book_form.html", book=book, categories=categories, action="Edit")


@admin_bp.route("/books/delete/<int:book_id>", methods=["POST"])
@admin_required
def delete_book_view(book_id: int):
    book = get_book(book_id)
    if book:
        delete_book(book_id)
        log_action(session["user_id"], "DELETE_BOOK", "book", book_id,
                   f"Deleted book: {book['title']}", request.remote_addr)
        flash("Book deleted.", "success")
    return redirect(url_for("admin.books"))


# ── MEMBERS ───────────────────────────────────────────────────────────────────

@admin_bp.route("/members")
@admin_required
def members():
    search = request.args.get("search", "")
    members_list = get_all_members(search=search)
    return render_template("admin/members.html", members=members_list, search=search)


@admin_bp.route("/members/add", methods=["GET", "POST"])
@admin_required
def add_member_view():
    if request.method == "POST":
        data = {k: v.strip() for k, v in request.form.items()}
        data["password_hash"] = generate_password_hash(data.get("password", "member123"))
        try:
            new_id = add_member(data)
            log_action(session["user_id"], "ADD_MEMBER", "user", new_id,
                       f"Added member: {data['full_name']}", request.remote_addr)
            flash(f"Member '{data['full_name']}' registered!", "success")
            return redirect(url_for("admin.members"))
        except Exception as e:
            flash(f"Error: {e}", "error")
    return render_template("admin/member_form.html", member=None, action="Add")


@admin_bp.route("/members/edit/<int:user_id>", methods=["GET", "POST"])
@admin_required
def edit_member_view(user_id: int):
    member = get_user(user_id)
    if not member:
        flash("Member not found.", "error")
        return redirect(url_for("admin.members"))
    if request.method == "POST":
        data = {k: v.strip() for k, v in request.form.items()}
        data["is_active"] = 1 if data.get("is_active") else 0
        update_member(user_id, data)
        log_action(session["user_id"], "UPDATE_MEMBER", "user", user_id,
                   f"Updated member ID {user_id}", request.remote_addr)
        flash("Member updated.", "success")
        return redirect(url_for("admin.members"))
    return render_template("admin/member_form.html", member=member, action="Edit")


# ── TRANSACTIONS & REPORTS ────────────────────────────────────────────────────

@admin_bp.route("/transactions")
@admin_required
def transactions():
    status = request.args.get("status", "")
    txns = get_all_transactions(status=status)
    return render_template("admin/transactions.html", transactions=txns, status_filter=status)


@admin_bp.route("/reports")
@admin_required
def reports():
    stats = get_dashboard_stats()
    return render_template("admin/reports.html", stats=stats)


@admin_bp.route("/reports/generate")
@admin_required
def generate_report():
    try:
        filepath = generate_full_report(generated_by=session["user_id"])
        log_action(session["user_id"], "GENERATE_REPORT", "report", None,
                   "Generated full library report", request.remote_addr)
        flash("Report generated successfully!", "success")
        return send_file(filepath, as_attachment=True, download_name="library_report.pdf")
    except Exception as e:
        flash(f"Error generating report: {e}", "error")
        return redirect(url_for("admin.reports"))
