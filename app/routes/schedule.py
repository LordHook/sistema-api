from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import date
from app.extensions import db
from app.models.schedule import ScheduleEntry
from app.models.audit import AuditLog
from app.models.worker import Worker
from app.services.schedule_generator import (
    generate_monthly_schedule,
    generate_group_schedule,
    get_schedule_grid,
)

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
    
    if current_user.role == 'supervisor':
        group = str(current_user.assigned_group) if current_user.assigned_group else request.args.get('group', '1')
    else:
        group = request.args.get('group', None)  # 'all', 'staff', '1', '2', '3'
        
    grid = get_schedule_grid(year, month, group_filter=group, user_role=current_user.role)
    return jsonify(grid)


@schedule_bp.route('/api/schedule/generate', methods=['POST'])
@login_required
def generate_schedule():
    if not current_user.is_admin:
        return jsonify({'error': 'Solo administradores pueden generar horarios'}), 403

    data = request.get_json()
    start_year = data.get('year', date.today().year)
    start_month = data.get('month', date.today().month)
    group = data.get('group', None)  # None = all, '1'/'2'/'3' = specific group
    project_year = data.get('project_year', False)

    months_to_generate = []
    if project_year:
        months_to_generate = [m for m in range(start_month, 13)]
    else:
        months_to_generate = [start_month]

    total_count = 0
    group_label = ''

    for m in months_to_generate:
        if group and group.isdigit():
            count = generate_group_schedule(start_year, m, int(group))
            group_label = f'Grupo {group}'
        else:
            count = generate_monthly_schedule(start_year, m)
            group_label = 'todo el personal'
        total_count += count

    mod_label = f"hasta diciembre {start_year}" if project_year else f"en {start_month}/{start_year}"
    
    AuditLog.log(
        user_id=current_user.id,
        action='schedule_change',
        details=f'Horario generado para {group_label} {mod_label} ({total_count} entradas)',
    )
    db.session.commit()

    return jsonify({
        'message': f'Horario generado exitosamente para {group_label}: {total_count} entradas creadas',
        'count': total_count,
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

        # Handle Resignation special case
        if new_shift == 'R':
            worker = Worker.query.get(entry.worker_id)
            if worker:
                worker.resignation_date = date(entry.year, entry.month, entry.day)
            
            # Auto-fill R to the end of the month
            subsequent_entries = ScheduleEntry.query.filter(
                ScheduleEntry.worker_id == entry.worker_id,
                ScheduleEntry.year == entry.year,
                ScheduleEntry.month == entry.month,
                ScheduleEntry.day > entry.day
            ).all()

            for sub_entry in subsequent_entries:
                sub_entry.shift_code = 'R'
                sub_entry.is_auto_generated = True

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
