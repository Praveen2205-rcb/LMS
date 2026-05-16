from __future__ import annotations
import json
import datetime
from decimal import Decimal
from flask import Blueprint, jsonify, request, session
from backend.models.models import (get_dashboard_stats, get_all_transactions,
                                    get_all_books, get_all_members, update_overdue_status,
                                    get_recent_activity)

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _resp(data) -> str:
    return json.dumps(data, default=_default)


@api_bp.route("/stats")
def stats():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    update_overdue_status()
    return _resp(get_dashboard_stats()), 200, {"Content-Type": "application/json"}


@api_bp.route("/transactions")
def transactions():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    status = request.args.get("status", "")
    limit = int(request.args.get("limit", 20))
    txns = get_all_transactions(status=status)[:limit]
    return _resp(txns), 200, {"Content-Type": "application/json"}


@api_bp.route("/books")
def books():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    search = request.args.get("search", "")
    books_list = get_all_books(search=search)
    return _resp(books_list), 200, {"Content-Type": "application/json"}


@api_bp.route("/members")
def members():
    if "user_id" not in session or session.get("role") not in ("admin", "librarian"):
        return jsonify({"error": "Unauthorized"}), 401
    search = request.args.get("search", "")
    members_list = get_all_members(search=search)
    return _resp(members_list), 200, {"Content-Type": "application/json"}


@api_bp.route("/activity")
def activity():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    limit = int(request.args.get("limit", 15))
    logs = get_recent_activity(limit)
    return _resp(logs), 200, {"Content-Type": "application/json"}
