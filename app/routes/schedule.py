from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import date
from app.extensions import db
from app.models.schedule import ScheduleEntry
from app.models.audit import AuditLog
from app.services.schedule_generator import generate_monthly_schedule, get_schedule_grid

schedule_bp = Blueprint('schedule', __name__)


@schedule_bp.route('/schedule')
@login_required
def schedule_page():
    return render_template('schedule.html')


@schedule_bp.route('/api/schedule')
@login_required
def get_schedule():
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    grid = get_schedule_grid(year, month)
    return jsonify(grid)


@schedule_bp.route('/api/schedule/generate', methods=['POST'])
@login_required
def generate_schedule():
    if not current_user.is_admin:
        return jsonify({'error': 'Solo administradores pueden generar horarios'}), 403

    data = request.get_json()
    year = data.get('year', date.today().year)
    month = data.get('month', date.today().month)

    count = generate_monthly_schedule(year, month)

    AuditLog.log(
        user_id=current_user.id,
        action='schedule_change',
        details=f'Horario generado para {month}/{year} ({count} entradas)',
    )
    db.session.commit()

    return jsonify({
        'message': f'Horario generado exitosamente: {count} entradas creadas',
        'count': count,
    })


@schedule_bp.route('/api/schedule/entry/<int:entry_id>', methods=['PUT'])
@login_required
def update_entry(entry_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Solo administradores pueden modificar el horario'}), 403

    entry = ScheduleEntry.query.get_or_404(entry_id)
    data = request.get_json()

    old_shift = entry.shift_code
    new_shift = data.get('shift_code')

    if new_shift and new_shift != old_shift:
        entry.shift_code = new_shift
        entry.is_auto_generated = False

        AuditLog.log(
            user_id=current_user.id,
            action='schedule_change',
            target_worker_id=entry.worker_id,
            target_date=date(entry.year, entry.month, entry.day),
            old_value=old_shift,
            new_value=new_shift,
            details=f'Turno modificado manualmente',
        )

        db.session.commit()

    return jsonify({'message': 'Entrada actualizada'})
