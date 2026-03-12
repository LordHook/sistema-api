from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from datetime import date
from app.services.attendance_service import get_dashboard_stats

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@dashboard_bp.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    date_str = request.args.get('date')
    target_date = date.fromisoformat(date_str) if date_str else date.today()
    stats = get_dashboard_stats(target_date)
    return jsonify(stats)
