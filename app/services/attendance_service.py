"""Servicio de lógica de asistencia."""
from datetime import date
from app.extensions import db
from app.models.attendance import AttendanceRecord
from app.models.schedule import ScheduleEntry
from app.models.worker import Worker
from app.models.audit import AuditLog


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

    old_status = record.status if record else None

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


def get_dashboard_stats(target_date=None):
    """Get statistics for the dashboard."""
    if target_date is None:
        target_date = date.today()

    year = target_date.year
    month = target_date.month

    total_active = Worker.query.filter_by(status='activo').count()

    # Today's attendance
    today_records = AttendanceRecord.query.filter_by(attendance_date=target_date).all()
    attended = sum(1 for r in today_records if r.status == 'asistio')
    absent = sum(1 for r in today_records if r.status == 'falto')
    late = sum(1 for r in today_records if r.status == 'tardanza')

    # Count rest/vacation today
    today_schedules = ScheduleEntry.query.filter_by(
        year=year, month=month, day=target_date.day
    ).all()
    resting = sum(1 for s in today_schedules if s.shift_code == 'D')
    on_vacation = sum(1 for s in today_schedules if s.shift_code == 'V')

    # Monthly attendance per group
    monthly_records = AttendanceRecord.query.filter(
        db.extract('year', AttendanceRecord.attendance_date) == year,
        db.extract('month', AttendanceRecord.attendance_date) == month,
    ).all()

    group_stats = {}
    for r in monthly_records:
        worker = Worker.query.get(r.worker_id)
        if worker:
            group_key = f'Grupo {worker.group_number}' if worker.group_number else worker.section
            if group_key not in group_stats:
                group_stats[group_key] = {'asistio': 0, 'falto': 0, 'tardanza': 0}
            if r.status in group_stats[group_key]:
                group_stats[group_key][r.status] += 1

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
