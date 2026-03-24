from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import date
from app.extensions import db
from app.models.attendance import AttendanceRecord
from app.models.audit import AuditLog
from app.services.attendance_service import get_attendance_for_date, save_attendance
from app.services.schedule_generator import get_schedule_grid
from sqlalchemy import extract

attendance_bp = Blueprint('attendance', __name__)


@attendance_bp.route('/attendance')
@login_required
def attendance_page():
    return render_template('attendance.html')


@attendance_bp.route('/api/attendance')
@login_required
def get_attendance():
    date_str = request.args.get('date')
    target_date = date.fromisoformat(date_str) if date_str else date.today()
    data = get_attendance_for_date(target_date)
    return jsonify({'date': target_date.isoformat(), 'records': data})


@attendance_bp.route('/api/attendance/grid')
@login_required
def get_attendance_grid():
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    
    # Apply supervisor group restriction
    if current_user.role == 'supervisor':
        group = str(current_user.assigned_group) if current_user.assigned_group else request.args.get('group', '1')
    elif current_user.role in ['admin', 'visualizador']:
        group = request.args.get('group', None)
    else:
        group = 'all'

    grid = get_schedule_grid(year, month, group_filter=group, user_role=current_user.role, username=current_user.username)

    # Fetch all attendance records for this month
    from app.extensions import db
    import calendar
    _, last_day = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)
    
    records = AttendanceRecord.query.filter(
        AttendanceRecord.attendance_date >= start_date,
        AttendanceRecord.attendance_date <= end_date
    ).all()
    
    # Map by (worker_id, day)
    att_map = {(r.worker_id, r.attendance_date.day): r for r in records}

    # Inject into grid
    for section in grid.get('sections', []):
        for grp in section.get('groups', []):
            for row in grp.get('rows', []):
                w_id = row['worker']['id']
                for day_data in row.get('days', []):
                    d = day_data['day']
                    record = att_map.get((w_id, d))
                    if record:
                        day_data['attendance_status'] = record.status
                        day_data['attendance_id'] = record.id
                    else:
                        day_data['attendance_status'] = None
                        day_data['attendance_id'] = None

    today_date = date.today()
    grid['current_day'] = today_date.day if (today_date.year == year and today_date.month == month) else None
    grid['real_year'] = today_date.year
    grid['real_month'] = today_date.month
    grid['real_day'] = today_date.day
    grid['is_admin'] = current_user.is_admin

    return jsonify(grid)


@attendance_bp.route('/api/attendance', methods=['POST'])
@login_required
def post_attendance():
    data = request.get_json()
    worker_id = data['worker_id']
    target_date = date.fromisoformat(data['date'])
    status = data['status']
    notes = data.get('notes', '')

    try:
        record = save_attendance(worker_id, target_date, status, current_user.id, notes)
    except ValueError as e:
        return jsonify({'error': str(e)}), 403

    return jsonify({
        'message': 'Asistencia registrada',
        'id': record.id if record else None,
    })


@attendance_bp.route('/api/attendance/batch', methods=['POST'])
@login_required
def batch_attendance():
    data = request.get_json()
    target_date = date.fromisoformat(data['date'])
    records = data.get('records', [])

    try:
        for r in records:
            save_attendance(r['worker_id'], target_date, r['status'],
                            current_user.id, r.get('notes', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 403

    return jsonify({'message': f'{len(records)} registros guardados'})


@attendance_bp.route('/api/attendance/<int:record_id>/validate', methods=['PUT'])
@login_required
def validate_attendance(record_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Solo administradores pueden validar'}), 403

    record = AttendanceRecord.query.get_or_404(record_id)
    record.validated_by_admin = True
    record.validated_by = current_user.id

    AuditLog.log(
        user_id=current_user.id,
        action='attendance_change',
        target_worker_id=record.worker_id,
        target_date=record.attendance_date,
        old_value='no validado',
        new_value='validado',
        details='Asistencia validada por administrador',
    )

    db.session.commit()
    return jsonify({'message': 'Asistencia validada'})
