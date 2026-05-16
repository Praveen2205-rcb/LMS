from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from backend.models.models import get_user_by_username
from backend.utils.logger import log_action

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET"])
def index():
    if "user_id" in session:
        return redirect(url_for(f"{session['role']}.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for(f"{session['role']}.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_user_by_username(username)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["full_name"] = user["full_name"]
            log_action(user["id"], "LOGIN", "auth", user["id"],
                       f"{user['full_name']} logged in", request.remote_addr)
            return redirect(url_for(f"{user['role']}.dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    user_id = session.get("user_id")
    full_name = session.get("full_name", "Unknown")
    log_action(user_id, "LOGOUT", "auth", user_id, f"{full_name} logged out")
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
