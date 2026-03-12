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
    """Genera el rol de servicio completo para un mes dado (todo el personal)."""
    num_days = calendar.monthrange(year, month)[1]

    # Limpiar entradas auto-generadas previas del mes
    ScheduleEntry.query.filter_by(
        year=year, month=month, is_auto_generated=True
    ).delete()
    db.session.flush()

    all_workers = _get_relevant_workers(year, month)

    # Group workers by section
    sections = {'A': [], 'B': [], 'C': [], 'D': []}
    for w in all_workers:
        if w.section in sections:
            sections[w.section].append(w)

    entries = []

    # Sections A, B, C (fixed shift)
    for section_key in ['A', 'B', 'C']:
        entries.extend(
            _generate_fixed_shift_section(sections[section_key], year, month, num_days, 'M')
        )

    # Section D (rotating shifts by group)
    entries.extend(_generate_section_d(sections['D'], year, month, num_days))

    db.session.add_all(entries)
    db.session.commit()
    return len(entries)


def generate_group_schedule(year, month, group_number):
    """Genera el horario exclusivamente para un grupo operativo específico (1, 2 o 3).
    La distribución equitativa de descansos se calcula solo con los integrantes de ese grupo.
    """
    num_days = calendar.monthrange(year, month)[1]

    all_workers = _get_relevant_workers(year, month)
    group_workers = [w for w in all_workers if w.section == 'D' and (w.group_number or 1) == group_number]

    if not group_workers:
        return 0

    # Delete only this group's auto-generated entries
    worker_ids = [w.id for w in group_workers]
    ScheduleEntry.query.filter(
        ScheduleEntry.worker_id.in_(worker_ids),
        ScheduleEntry.year == year,
        ScheduleEntry.month == month,
        ScheduleEntry.is_auto_generated == True,  # noqa: E712
    ).delete(synchronize_session='fetch')
    db.session.flush()

    # Generate only for this group
    shift_rotation = ['M', 'T', 'N']
    base_shift_index = (group_number - 1) % 3

    entries = _generate_rotating_section(
        group_workers, year, month, num_days,
        shift_rotation, base_shift_index
    )

    db.session.add_all(entries)
    db.session.commit()
    return len(entries)


def _get_relevant_workers(year, month):
    """Get active workers and those who resigned during this month."""
    workers = Worker.query.filter_by(status='activo').order_by(Worker.order_number).all()
    resigned_this_month = Worker.query.filter(
        Worker.status == 'inactivo',
        Worker.resignation_date != None,  # noqa: E711
        db.extract('year', Worker.resignation_date) == year,
        db.extract('month', Worker.resignation_date) == month,
    ).order_by(Worker.order_number).all()

    return workers + [w for w in resigned_this_month if w not in workers]


def _generate_section_d(d_workers, year, month, num_days):
    """Generate rotating shifts for Section D organized by groups."""
    entries = []
    groups = {}
    for w in d_workers:
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
    return entries


def _generate_fixed_shift_section(workers, year, month, num_days, default_shift):
    """Secciones A/B/C: turno fijo, solo rotan descansos."""
    entries = []
    total_workers = len(workers)

    for idx, worker in enumerate(workers):
        rest_day_start = (idx % 7) + 1

        for day in range(1, num_days + 1):
            current_date = date(year, month, day)
            shift = _determine_shift(
                worker, current_date, day, rest_day_start,
                default_shift, total_workers, idx
            )
            entries.append(ScheduleEntry(
                worker_id=worker.id,
                year=year, month=month, day=day,
                shift_code=shift,
                is_auto_generated=True,
            ))

    return entries


def _generate_rotating_section(workers, year, month, num_days,
                                shift_rotation, base_shift_index):
    """Sección D: turnos rotativos M→T→N con descansos escalonados.
    Distribución equitativa: ~len(workers)/7 descansan por día.
    """
    entries = []
    total_workers = len(workers)

    for idx, worker in enumerate(workers):
        rest_day_start = (idx % 7) + 1

        for day in range(1, num_days + 1):
            current_date = date(year, month, day)

            # Determine which week we're in (0-based)
            week_num = (day - 1) // 7
            current_shift_index = (base_shift_index + week_num) % len(shift_rotation)
            work_shift = shift_rotation[current_shift_index]

            shift = _determine_shift(
                worker, current_date, day, rest_day_start,
                work_shift, total_workers, idx
            )
            entries.append(ScheduleEntry(
                worker_id=worker.id,
                year=year, month=month, day=day,
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
    days_since_start = day - rest_day_start

    if days_since_start < 0:
        return False

    # Every 8 days is a rest day
    if days_since_start % 8 == 0:
        return True

    # Check for the "double rest" when crossing Sun→Mon
    if days_since_start > 0 and (days_since_start - 1) % 8 == 0:
        prev_day = day - 1
        if prev_day >= 1:
            prev_date = date(current_date.year, current_date.month, prev_day)
            if prev_date.weekday() == 6:  # Sunday
                return True

    return False


def get_schedule_grid(year, month, group_filter=None):
    """Returns the schedule data structured for the grid view.
    group_filter: 'all', 'staff', '1', '2', '3', or None
    """
    num_days = calendar.monthrange(year, month)[1]

    workers = Worker.query.order_by(Worker.section, Worker.group_number,
                                     Worker.order_number).all()

    # Filter to relevant workers
    relevant_workers = []
    for w in workers:
        if w.status == 'activo':
            relevant_workers.append(w)
        elif w.resignation_date:
            if w.resignation_date.year == year and w.resignation_date.month >= month:
                relevant_workers.append(w)
            elif w.resignation_date.year > year:
                relevant_workers.append(w)

    # Apply group filter
    if group_filter and group_filter != 'all':
        if group_filter == 'staff':
            relevant_workers = [w for w in relevant_workers if w.section in ('A', 'B', 'C')]
        elif group_filter.isdigit():
            gnum = int(group_filter)
            relevant_workers = [w for w in relevant_workers
                                if w.section == 'D' and (w.group_number or 1) == gnum]

    entries = ScheduleEntry.query.filter_by(year=year, month=month).all()
    entry_map = {}
    for e in entries:
        entry_map[(e.worker_id, e.day)] = e

    sections = _build_sections(relevant_workers, entry_map, num_days, group_filter)

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
        'group_filter': group_filter,
    }


def _build_sections(workers, entry_map, num_days, group_filter=None):
    """Organizes workers into display sections."""
    sections = []

    # If filtering by a specific group, only show section D
    if group_filter and group_filter.isdigit() if group_filter else False:
        gnum = int(group_filter)
        d_workers = [w for w in workers if w.section == 'D']
        if d_workers:
            groups_data = {'CCO': [], 'SCV': []}
            for w in d_workers:
                area_key = w.area if w.area in ('CCO', 'SCV') else 'CCO'
                groups_data[area_key].append(w)

            d_groups = []
            for area in ['CCO', 'SCV']:
                area_workers = groups_data.get(area, [])
                if area_workers:
                    d_groups.append({
                        'label': f'Grupo {gnum} - {area}',
                        'rows': _build_worker_rows(area_workers, entry_map, num_days)['rows'],
                    })

            if d_groups:
                total_in_group = sum(len(g['rows']) for g in d_groups)
                sections.append({
                    'key': 'D',
                    'name': f'Grupo {gnum} — Rol de Servicio Operativo ({total_in_group} integrantes, ~{total_in_group // 7 or 1} descansos/día)',
                    'groups': d_groups,
                })
        return sections

    # Normal view (all or staff)
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

    # Section D - show if 'all' or no filter
    if not group_filter or group_filter == 'all':
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
