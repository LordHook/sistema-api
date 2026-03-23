"""Servicio de lógica de asistencia."""
from datetime import date
from app.extensions import db
from app.models.attendance import AttendanceRecord
from app.models.schedule import ScheduleEntry
from app.models.worker import Worker
from app.models.audit import AuditLog
from app.models.user import User
from datetime import datetime


def get_attendance_for_date(target_date):
    """Gets attendance data for a specific date, including scheduled shift info."""
    workers = Worker.query.filter_by(status='activo').order_by(
        Worker.section, Worker.group_number, Worker.order_number
    ).all()

    records = AttendanceRecord.query.filter_by(attendance_date=target_date).all()
    record_map = {r.worker_id: r for r in records}

    # Get scheduled shifts for this date
    schedule_entries = ScheduleEntry.query.filter_by(
        year=target_date.year, month=target_date.month, day=target_date.day
    ).all()
    shift_map = {s.worker_id: s.shift_code for s in schedule_entries}

    result = []
    for w in workers:
        shift = shift_map.get(w.id, '')
        record = record_map.get(w.id)

        # Skip workers on rest, vacation, compensation, or resigned
        if shift in ('D', 'V', 'C', 'R'):
            continue

        result.append({
            'worker': {
                'id': w.id,
                'order_number': w.order_number,
                'name': w.full_name,
                'section': w.section,
                'area': w.area,
                'group_number': w.group_number,
            },
            'shift': shift,
            'attendance': {
                'id': record.id if record else None,
                'status': record.status if record else None,
                'validated': record.validated_by_admin if record else False,
                'notes': record.notes if record else '',
            } if record else None,
        })

    return result


def save_attendance(worker_id, target_date, status, user_id, notes=None):
    """Save or update an attendance record."""
    record = AttendanceRecord.query.filter_by(
        worker_id=worker_id, attendance_date=target_date
    ).first()

    # Get the scheduled shift
    schedule = ScheduleEntry.query.filter_by(
        worker_id=worker_id,
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
    ).first()

    now = datetime.now()
    today = date.today()

    # Días Futuros: Bloqueo total (incluso admin)
    if target_date > today:
        raise ValueError("No se puede marcar asistencia en días futuros.")

    # Time validations
    user = User.query.get(user_id)
    if user and not user.is_admin:
        if user.is_visualizador:
            raise ValueError("Los visualizadores no tienen permiso para editar asistencia.")
        
        # 23:59 Lock for past days (Supervisors only edit Today)
        if target_date < today:
            raise ValueError("Solo el Administrador puede editar la asistencia de días pasados.")
        
        # Live Time Validation
        shift = schedule.shift_code if schedule else None
        current_hour = now.hour
        if shift == 'M' and not (6 <= current_hour < 14):
            raise ValueError("El turno Mañana solo se puede marcar entre las 06:00 y las 13:59.")
        elif shift == 'T' and not (14 <= current_hour < 22):
            raise ValueError("El turno Tarde solo se puede marcar entre las 14:00 y las 21:59.")
        elif shift == 'N' and not (current_hour >= 22 or current_hour < 6):
            raise ValueError("El turno Noche solo se puede marcar entre las 22:00 y las 05:59.")

    old_status = record.status if record else None

    # Handle Eraser logic
    if not status or status == 'CLEAR':
        if record:
            db.session.delete(record)
            AuditLog.log(
                user_id=user_id,
                action='attendance_change',
                target_worker_id=worker_id,
                target_date=target_date,
                old_value=old_status,
                new_value='borrado',
                details='Registro de asistencia eliminado (Borrador)',
            )
            db.session.commit()
        return None

    if record:
        record.status = status
        record.notes = notes
        if old_status != status:
            record.updated_at = db.func.now()
    else:
        record = AttendanceRecord(
            worker_id=worker_id,
            attendance_date=target_date,
            status=status,
            shift_code=schedule.shift_code if schedule else None,
            notes=notes,
        )
        db.session.add(record)

    # Log audit
    if old_status != status:
        AuditLog.log(
            user_id=user_id,
            action='attendance_change',
            target_worker_id=worker_id,
            target_date=target_date,
            old_value=old_status,
            new_value=status,
            details=f'Asistencia {"creada" if old_status is None else "modificada"}',
        )

    db.session.commit()
    return record


def get_dashboard_stats(target_date=None, user_role='admin', assigned_group=None):
    """Get statistics for the dashboard."""
    if target_date is None:
        target_date = date.today()

    year = target_date.year
    month = target_date.month

    workers_query = Worker.query.filter_by(status='activo')
    if user_role == 'supervisor':
        if assigned_group:
            # Filter for their specific group or Section B
            workers_query = workers_query.filter(
                db.or_(
                    db.and_(Worker.section == 'D', Worker.group_number == assigned_group),
                    Worker.section == 'B'
                )
            )
        else:
            # Fallback if no group assigned
            workers_query = workers_query.filter(Worker.section == 'B')
            
    relevant_worker_ids = [w.id for w in workers_query.all()]
    total_active = len(relevant_worker_ids)

    # Today's attendance
    today_records = AttendanceRecord.query.filter(
        AttendanceRecord.attendance_date == target_date,
        AttendanceRecord.worker_id.in_(relevant_worker_ids)
    ).all()
    attended = sum(1 for r in today_records if r.status in ('A', 'asistio'))
    absent = sum(1 for r in today_records if r.status in ('F', 'falto'))
    late = sum(1 for r in today_records if r.status == 'tardanza')

    # Count rest/vacation today
    today_schedules = ScheduleEntry.query.filter(
        ScheduleEntry.year == year, 
        ScheduleEntry.month == month, 
        ScheduleEntry.day == target_date.day,
        ScheduleEntry.worker_id.in_(relevant_worker_ids)
    ).all()
    resting = sum(1 for s in today_schedules if s.shift_code == 'D')
    on_vacation = sum(1 for s in today_schedules if s.shift_code == 'V')

    # Monthly attendance per group
    monthly_records = AttendanceRecord.query.filter(
        db.extract('year', AttendanceRecord.attendance_date) == year,
        db.extract('month', AttendanceRecord.attendance_date) == month,
        AttendanceRecord.worker_id.in_(relevant_worker_ids)
    ).all()

    group_stats = {}
    
    # Pre-fill expected groups based on role
    if user_role == 'supervisor' and assigned_group:
        group_stats = {
            f'Grupo {assigned_group}': {'A': 0, 'F': 0, 'tardanza': 0},
            'B': {'A': 0, 'F': 0, 'tardanza': 0}
        }
    
    for r in monthly_records:
        worker = Worker.query.get(r.worker_id)
        if worker:
            group_key = f'Grupo {worker.group_number}' if worker.group_number else worker.section
            if group_key not in group_stats:
                group_stats[group_key] = {'A': 0, 'F': 0, 'tardanza': 0}
            if r.status in group_stats[group_key]:
                group_stats[group_key][r.status] += 1
            # Fallback for old data
            elif r.status == 'asistio':
                group_stats[group_key]['A'] += 1
            elif r.status == 'falto':
                group_stats[group_key]['F'] += 1

    return {
        'date': target_date.isoformat(),
        'total_active': total_active,
        'today': {
            'attended': attended,
            'absent': absent,
            'late': late,
            'resting': resting,
            'on_vacation': on_vacation,
        },
        'group_stats': group_stats,
    }
