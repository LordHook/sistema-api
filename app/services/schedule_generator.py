"""
Algoritmo de Generación de Horarios (Rol de Servicio)

Reglas:
- Máximo 7 días consecutivos de trabajo
- 1 día de descanso por semana
- Descanso rotativo: avanza +1 día cada semana (+8 días desde el último descanso)
- Al pasar Domingo→Lunes: 2 días consecutivos de descanso
- Distribución equitativa: ~N/7 personas descansando por día
- Bloqueo por renuncia: si fecha >= resignation_date → 'R'
"""
import calendar
from datetime import date
from app.extensions import db
from app.models.schedule import ScheduleEntry
from app.models.worker import Worker


def generate_monthly_schedule(year, month):
    """Genera el rol de servicio completo para un mes dado."""
    num_days = calendar.monthrange(year, month)[1]

    # Limpiar entradas auto-generadas previas del mes
    ScheduleEntry.query.filter_by(
        year=year, month=month, is_auto_generated=True
    ).delete()
    db.session.flush()

    workers = Worker.query.filter_by(status='activo').order_by(Worker.order_number).all()
    # Also include workers who resigned DURING this month
    resigned_this_month = Worker.query.filter(
        Worker.status == 'inactivo',
        Worker.resignation_date != None,  # noqa: E711
        db.extract('year', Worker.resignation_date) == year,
        db.extract('month', Worker.resignation_date) == month,
    ).order_by(Worker.order_number).all()

    all_workers = workers + [w for w in resigned_this_month if w not in workers]

    # Group workers by section
    sections = {
        'A': [],  # Jefatura
        'B': [],  # Gestión de Video
        'C': [],  # Supervisores
        'D': [],  # Operativo (Groups 1-3)
    }

    for w in all_workers:
        if w.section in sections:
            sections[w.section].append(w)

    entries = []

    # Generate for sections A, B, C (fixed shift, only manage rest days)
    for section_key in ['A', 'B', 'C']:
        section_workers = sections[section_key]
        entries.extend(
            _generate_fixed_shift_section(section_workers, year, month, num_days, 'M')
        )

    # Generate for section D (rotating shifts M→T→N by group)
    groups = {}
    for w in sections['D']:
        g = w.group_number or 1
        if g not in groups:
            groups[g] = []
        groups[g].append(w)

    shift_rotation = ['M', 'T', 'N']
    for group_num in sorted(groups.keys()):
        group_workers = groups[group_num]
        base_shift_index = (group_num - 1) % 3
        entries.extend(
            _generate_rotating_section(
                group_workers, year, month, num_days,
                shift_rotation, base_shift_index
            )
        )

    db.session.add_all(entries)
    db.session.commit()
    return len(entries)


def _generate_fixed_shift_section(workers, year, month, num_days, default_shift):
    """Secciones A/B/C: turno fijo, solo rotan descansos."""
    entries = []
    total_workers = len(workers)

    for idx, worker in enumerate(workers):
        # Compute rest day offset for this worker to distribute evenly
        rest_day_start = (idx % 7) + 1  # Day 1-7

        for day in range(1, num_days + 1):
            current_date = date(year, month, day)
            shift = _determine_shift(
                worker, current_date, day, rest_day_start,
                default_shift, total_workers, idx
            )
            entries.append(ScheduleEntry(
                worker_id=worker.id,
                year=year,
                month=month,
                day=day,
                shift_code=shift,
                is_auto_generated=True,
            ))

    return entries


def _generate_rotating_section(workers, year, month, num_days,
                                shift_rotation, base_shift_index):
    """Sección D: turnos rotativos M→T→N con descansos escalonados."""
    entries = []
    total_workers = len(workers)

    for idx, worker in enumerate(workers):
        rest_day_start = (idx % 7) + 1

        for day in range(1, num_days + 1):
            current_date = date(year, month, day)

            # Determine which week we're in (0-based)
            week_num = (day - 1) // 7
            # Rotate shift each week for the group
            current_shift_index = (base_shift_index + week_num) % len(shift_rotation)
            work_shift = shift_rotation[current_shift_index]

            shift = _determine_shift(
                worker, current_date, day, rest_day_start,
                work_shift, total_workers, idx
            )
            entries.append(ScheduleEntry(
                worker_id=worker.id,
                year=year,
                month=month,
                day=day,
                shift_code=shift,
                is_auto_generated=True,
            ))

    return entries


def _determine_shift(worker, current_date, day, rest_day_start,
                     work_shift, total_workers, worker_index):
    """Determina el turno para un trabajador en un día dado."""
    # Check resignation
    if worker.resignation_date and current_date >= worker.resignation_date:
        return 'R'

    # Check if this is a manually set entry (vacation, compensated)
    existing = ScheduleEntry.query.filter_by(
        worker_id=worker.id,
        year=current_date.year,
        month=current_date.month,
        day=day,
        is_auto_generated=False,
    ).first()
    if existing:
        return existing.shift_code

    # Calculate rest days using the staggered rotation algorithm
    if _is_rest_day(day, rest_day_start, current_date):
        return 'D'

    return work_shift


def _is_rest_day(day, rest_day_start, current_date):
    """
    Determines if a given day is a rest day.
    Rest advances +1 day each week (every 8 days from last rest).
    When crossing Sunday→Monday, grant 2 consecutive rest days.
    """
    # Calculate which "cycle day" this is relative to worker's rest pattern
    # rest_day_start is the first rest day (1-7)
    # Pattern: rest on day X, then X+8, then X+16, etc.
    # But adjusted: rest advances +1 each week

    days_since_start = day - rest_day_start

    if days_since_start < 0:
        return False

    # Every 8 days is a rest day
    if days_since_start % 8 == 0:
        return True

    # Check for the "double rest" when crossing Sun→Mon
    # If rest day falls on Sunday (weekday 6), the next day (Monday) is also rest
    if days_since_start > 0 and (days_since_start - 1) % 8 == 0:
        # Previous day was a rest day, check if it was a Sunday
        prev_day = day - 1
        if prev_day >= 1:
            prev_date = date(current_date.year, current_date.month, prev_day)
            if prev_date.weekday() == 6:  # Sunday
                return True

    return False


def get_schedule_grid(year, month):
    """Returns the schedule data structured for the grid view."""
    num_days = calendar.monthrange(year, month)[1]

    workers = Worker.query.order_by(Worker.section, Worker.group_number,
                                     Worker.order_number).all()

    # Filter to only include active workers or those who resigned during this month
    relevant_workers = []
    for w in workers:
        if w.status == 'activo':
            relevant_workers.append(w)
        elif w.resignation_date:
            if w.resignation_date.year == year and w.resignation_date.month >= month:
                relevant_workers.append(w)
            elif w.resignation_date.year > year:
                relevant_workers.append(w)

    entries = ScheduleEntry.query.filter_by(year=year, month=month).all()

    # Build lookup dict
    entry_map = {}
    for e in entries:
        entry_map[(e.worker_id, e.day)] = e

    # Build sections
    sections = _build_sections(relevant_workers, entry_map, num_days)

    # Day headers with weekday names
    day_headers = []
    for d in range(1, num_days + 1):
        dt = date(year, month, d)
        day_headers.append({
            'day': d,
            'weekday': ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa', 'Do'][dt.weekday()],
            'is_weekend': dt.weekday() >= 5,
        })

    return {
        'year': year,
        'month': month,
        'month_name': [
            '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ][month],
        'num_days': num_days,
        'day_headers': day_headers,
        'sections': sections,
    }


def _build_sections(workers, entry_map, num_days):
    """Organizes workers into display sections."""
    sections = []

    section_config = [
        ('A', 'Jefatura CEMOVI, Planta Externa, Encargados y Coordinadores', None),
        ('B', 'Área de Gestión de Video', None),
        ('C', 'Supervisores', None),
    ]

    for sec_key, sec_name, _ in section_config:
        sec_workers = [w for w in workers if w.section == sec_key]
        if sec_workers:
            sections.append({
                'key': sec_key,
                'name': sec_name,
                'groups': [_build_worker_rows(sec_workers, entry_map, num_days)],
            })

    # Section D - split by groups
    d_workers = [w for w in workers if w.section == 'D']
    if d_workers:
        groups_data = {}
        for w in d_workers:
            g = w.group_number or 1
            if g not in groups_data:
                groups_data[g] = {'CCO': [], 'SCV': []}
            area_key = w.area if w.area in ('CCO', 'SCV') else 'CCO'
            groups_data[g][area_key].append(w)

        d_groups = []
        for group_num in sorted(groups_data.keys()):
            for area in ['CCO', 'SCV']:
                area_workers = groups_data[group_num].get(area, [])
                if area_workers:
                    d_groups.append({
                        'label': f'Grupo {group_num} - {area}',
                        'rows': _build_worker_rows(area_workers, entry_map, num_days)['rows'],
                    })

        if d_groups:
            sections.append({
                'key': 'D',
                'name': 'Rol de Servicio Operativo',
                'groups': d_groups,
            })

    return sections


def _build_worker_rows(workers, entry_map, num_days):
    """Builds row data for a list of workers."""
    rows = []
    for w in workers:
        days = []
        for d in range(1, num_days + 1):
            entry = entry_map.get((w.id, d))
            shift = entry.shift_code if entry else ''
            entry_id = entry.id if entry else None
            days.append({
                'day': d,
                'shift': shift,
                'entry_id': entry_id,
                'color': ScheduleEntry.SHIFT_COLORS.get(shift, '#374151'),
            })
        rows.append({
            'worker': {
                'id': w.id,
                'order_number': w.order_number,
                'name': w.full_name,
                'regime': w.regime,
                'area': w.area,
                'status': w.status,
            },
            'days': days,
        })
    return {'rows': rows}
