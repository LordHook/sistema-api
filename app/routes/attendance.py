from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import date
from app.extensions import db
from app.models.attendance import AttendanceRecord
from app.models.audit import AuditLog
from app.services.attendance_service import get_attendance_for_date, save_attendance

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


@attendance_bp.route('/api/attendance', methods=['POST'])
@login_required
def post_attendance():
    data = request.get_json()
    worker_id = data['worker_id']
    target_date = date.fromisoformat(data['date'])
    status = data['status']
    notes = data.get('notes', '')

    record = save_attendance(worker_id, target_date, status, current_user.id, notes)

    return jsonify({
        'message': 'Asistencia registrada',
        'id': record.id,
    })


@attendance_bp.route('/api/attendance/batch', methods=['POST'])
@login_required
def batch_attendance():
    data = request.get_json()
    target_date = date.fromisoformat(data['date'])
    records = data.get('records', [])

    for r in records:
        save_attendance(r['worker_id'], target_date, r['status'],
                        current_user.id, r.get('notes', ''))

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
