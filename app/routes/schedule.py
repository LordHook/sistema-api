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
    elif current_user.role in ['admin', 'visualizador']:
        group = request.args.get('group', None)  # 'all', 'staff', '1', '2', '3'
    else:
        group = 'all'
        
    grid = get_schedule_grid(year, month, group_filter=group, user_role=current_user.role, username=current_user.username)
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


@schedule_bp.route('/api/schedule/entry', methods=['POST'])
@login_required
def create_or_update_entry():
    if not current_user.is_admin:
        return jsonify({'error': 'Solo administradores pueden modificar el horario'}), 403

    try:
        data = request.get_json()
        worker_id = data.get('worker_id')
        day = data.get('day')
        year = data.get('year')
        month = data.get('month')
        new_shift = data.get('shift_code')
        auto_complete = data.get('auto_complete', True)

        if not all([worker_id, year, month, day]):
            return jsonify({'error': 'Faltan parámetros de fecha o trabajador'}), 400
            
        # Ensure safely casted integers to avoid TypeErrors
        worker_id = int(worker_id)
        day = int(day)
        year = int(year)
        month = int(month)

        # Normalize empty strings to 'CLEAR'
        if new_shift == '':
            new_shift = 'CLEAR'

        entry = ScheduleEntry.query.filter_by(worker_id=worker_id, year=year, month=month, day=day).first()
        old_shift = entry.shift_code if entry else None

        if new_shift is not None and new_shift != old_shift:
            # Validate allowed shifts if it is M, T, or N
            worker = Worker.query.get(worker_id)
            if worker and new_shift in ['M', 'T', 'N']:
                # PROTECT SPECIAL CODES FROM OVERWRITES
                protected_codes = ['PO', 'PC', 'PV', 'DM', 'V', 'LM', 'LE', 'PS', 'C', 'R', 'D']
                if old_shift in protected_codes and not current_user.is_admin:
                    return jsonify({'error': f'Celda protegida: Borra {old_shift} antes de asignar turno regular.'}), 400

                allowed = (worker.allowed_shifts or 'M,T,N').split(',')
                if new_shift not in allowed:
                    return jsonify({'error': f'El trabajador no tiene habilitado el turno {new_shift}'}), 400

            if new_shift == 'CLEAR':
                if entry:
                    db.session.delete(entry)
                    AuditLog.log(
                        user_id=current_user.id,
                        action='schedule_change',
                        target_worker_id=worker_id,
                        target_date=date(year, month, day),
                        old_value=old_shift,
                        new_value='vacio',
                        details='Turno borrado manualmente'
                    )
                    db.session.commit()
                return jsonify({'message': 'Entrada borrada'})
                    
            if not entry:
                entry = ScheduleEntry(worker_id=worker_id, year=year, month=month, day=day, is_auto_generated=False)
                db.session.add(entry)
                
            entry.shift_code = new_shift
            entry.is_auto_generated = False

            # Handle Resignation special case
            if new_shift == 'R' and auto_complete:
                if worker:
                    worker.resignation_date = date(year, month, day)
                
                # Auto-fill R to the end of the month
                import calendar
                _, num_days = calendar.monthrange(year, month)
                for d in range(day + 1, num_days + 1):
                    existing_entry = ScheduleEntry.query.filter_by(worker_id=worker_id, year=year, month=month, day=d).first()
                    if existing_entry:
                        # Only overwrite empty cells
                        if existing_entry.shift_code in ['CLEAR', 'NI', None, '']:
                            existing_entry.shift_code = 'R'
                            existing_entry.is_auto_generated = True
                    else:
                        new_entry = ScheduleEntry(worker_id=worker_id, year=year, month=month, day=d, shift_code='R', is_auto_generated=True)
                        db.session.add(new_entry)

            # NEW AUTO-COMPLETE LOGIC FOR SECTION D and TD
            if auto_complete and worker and worker.section in ['D', 'TD']:
                import calendar
                _, num_days = calendar.monthrange(year, month)
                
                if new_shift == 'D':
                    curr_rest_day = day
                    target_date = date(year, month, day)
                    pending_extra_rest = False
                    if target_date.weekday() == 6: # Sunday
                        pending_extra_rest = True
                        
                    for curr_d in range(day + 1, num_days + 1):
                        loop_date = date(year, month, curr_d)
                        assign_d = False
                        
                        if pending_extra_rest:
                            # Exactly Lunes after Domingo Doble
                            assign_d = True
                            pending_extra_rest = False
                            curr_rest_day = curr_d # Lunes is the new anchor for the strict +7 day cycle
                        else:
                            days_since_rest = curr_d - curr_rest_day
                            if days_since_rest >= 8: # Escalonado 8-day calendar leap
                                assign_d = True
                                if loop_date.weekday() == 6: # Next rest falls on Sunday
                                    pending_extra_rest = True
                                    # Wait until tomorrow to shift the anchor
                                else:
                                    curr_rest_day = curr_d
                                    
                        if assign_d:
                            existing_entry = ScheduleEntry.query.filter_by(worker_id=worker_id, year=year, month=month, day=curr_d).first()
                            if existing_entry:
                                if existing_entry.shift_code in ['CLEAR', 'NI', None, '']:
                                    existing_entry.shift_code = 'D'
                                    existing_entry.is_auto_generated = True
                            else:
                                new_entry = ScheduleEntry(worker_id=worker_id, year=year, month=month, day=curr_d, shift_code='D', is_auto_generated=True)
                                db.session.add(new_entry)

                elif new_shift in ['M', 'T', 'N']:
                    rotation = {'M': 'N', 'N': 'T', 'T': 'M'}
                    active_shift = new_shift
                    
                    # Autocomplete future work days until end of month
                    for d in range(day + 1, num_days + 1):
                        loop_date = date(year, month, d)
                        existing_entry = ScheduleEntry.query.filter_by(worker_id=worker_id, year=year, month=month, day=d).first()
                        
                        # Exact mathematical Monday trigger: Strict rotation ignoring rests
                        if loop_date.weekday() == 0:
                            active_shift = rotation[active_shift]
                        
                        if existing_entry and existing_entry.shift_code not in ['CLEAR', 'NI', None, '']:
                            # Skip placing the shift here to respect existing data
                            # But the 'active_shift' context remains intact for the rest of the week!
                            pass
                        else:
                            if existing_entry:
                                existing_entry.shift_code = active_shift
                                existing_entry.is_auto_generated = True
                            else:
                                new_entry = ScheduleEntry(worker_id=worker_id, year=year, month=month, day=d, shift_code=active_shift, is_auto_generated=True)
                                db.session.add(new_entry)

            AuditLog.log(
                user_id=current_user.id,
                action='schedule_change',
                target_worker_id=worker_id,
                target_date=date(year, month, day),
                old_value=old_shift or 'vacio',
                new_value=new_shift,
                details=f'Turno modificado manualmente',
            )

            db.session.commit()

        return jsonify({'message': 'Entrada actualizada'})
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error interno en el servidor: {str(e)}'}), 500
