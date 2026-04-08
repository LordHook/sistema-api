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
from datetime import date, timedelta
from app.extensions import db
from app.models.schedule import ScheduleEntry
from app.models.worker import Worker

def _apply_monthly_snapshots(workers, year, month):
    from app.models.worker import MonthlyWorkerStatus
    snapshots = MonthlyWorkerStatus.query.filter_by(year=year, month=month).all()
    snap_map = {s.worker_id: s for s in snapshots}
    
    for w in workers:
        if w.id in snap_map:
            w.section = snap_map[w.id].section
            w.group_number = snap_map[w.id].group_number
            if hasattr(snap_map[w.id], 'area') and snap_map[w.id].area is not None:
                w.area = snap_map[w.id].area
    return workers

def _ensure_snapshots_exist(workers, year, month):
    from app.models.worker import MonthlyWorkerStatus
    snapshots = MonthlyWorkerStatus.query.filter_by(year=year, month=month).all()
    snap_map = {s.worker_id: s for s in snapshots}
    
    new_snaps = []
    for w in workers:
        if w.id not in snap_map:
            snap = MonthlyWorkerStatus(worker_id=w.id, year=year, month=month, section=w.section, group_number=w.group_number, area=w.area)
            new_snaps.append(snap)
            
    if new_snaps:
        db.session.add_all(new_snaps)
        db.session.flush()


def generate_monthly_schedule(year, month):
    """Genera el rol de servicio completo para un mes dado (todo el personal)."""
    num_days = calendar.monthrange(year, month)[1]

    # Limpiar entradas auto-generadas previas del mes
    ScheduleEntry.query.filter_by(
        year=year, month=month, is_auto_generated=True
    ).delete()
    db.session.flush()

    all_workers = _get_relevant_workers(year, month)
    _ensure_snapshots_exist(all_workers, year, month)
    all_workers = _apply_monthly_snapshots(all_workers, year, month)

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
    _ensure_snapshots_exist(all_workers, year, month)
    all_workers = _apply_monthly_snapshots(all_workers, year, month)
    
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
    """Get active workers, those who resigned during this month, and filtering by start_date."""
    # Buscar todos y filtrar en memoria para garantizar lógica temporal perfecta (N ~ 150)
    all_workers = Worker.query.order_by(Worker.order_number).all()
    
    filtered_workers = []
    for w in all_workers:
        # Filtrar ingresos futuros
        if w.start_date:
            if w.start_date.year > year or (w.start_date.year == year and w.start_date.month > month):
                continue
                
        # Lógica de Cese
        if w.resignation_date:
            res_year = w.resignation_date.year
            res_month = w.resignation_date.month
            # Mostrar SÓLO si la renuncia ocurrió EN EL MISMO MES o EN EL FUTURO
            if res_year > year or (res_year == year and res_month >= month):
                filtered_workers.append(w)
            continue
            
        # Si no tiene fecha de renuncia, mostrar solo activos
        if w.status == 'activo':
            filtered_workers.append(w)
            
    return filtered_workers


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
    """Secciones A/B/C: turno fijo. Sección A rige sus descansos fijos."""
    entries = []
    
    # Separar Sección A de B y C
    sec_a = [w for w in workers if w.section == 'A']
    sec_others = [w for w in workers if w.section != 'A']
    
    if sec_a:
        entries.extend(_generate_sequential_schedule(sec_a, year, month, num_days, [default_shift], 0, is_fixed=True, section_a_rules=True))
    
    if sec_others:
        entries.extend(_generate_sequential_schedule(sec_others, year, month, num_days, [default_shift], 0, is_fixed=True, section_a_rules=False))
        
    return entries


def _generate_rotating_section(workers, year, month, num_days, shift_rotation, base_shift_index):
    """Sección D: turnos rotativos M→T→N con descansos escalonados."""
    return _generate_sequential_schedule(workers, year, month, num_days, shift_rotation, base_shift_index, is_fixed=False)


def _generate_sequential_schedule(workers, year, month, num_days, shift_rotation, base_shift_index, is_fixed=False, section_a_rules=False):
    """
    Generates deterministic staggered schedule across months using DB history.
    If section_a_rules is True, ignores staggered history and STRICTLY assigns 'M' on Mon-Fri and 'D' on Sat-Sun.
    """
    entries = []

    for idx, worker in enumerate(workers):
        # 1. Determine anchor state from previous days (skip for Sec A)
        last_date_checked = date(year, month, 1) - timedelta(days=1)
        prev_entries = []
        if not section_a_rules:
            prev_month = month - 1 if month > 1 else 12
            prev_year = year if month > 1 else year - 1
            raw_entries = ScheduleEntry.query.filter(
                ScheduleEntry.worker_id == worker.id,
                db.or_(
                    db.and_(ScheduleEntry.year == prev_year, ScheduleEntry.month == prev_month),
                    db.and_(ScheduleEntry.year == year, ScheduleEntry.month == month - 2 if month > 2 else 12)
                )
            ).order_by(
                ScheduleEntry.year.desc(), 
                ScheduleEntry.month.desc(), 
                ScheduleEntry.day.desc()
            ).all()
            prev_entries = [
                e for e in raw_entries
                if date(e.year, e.month, e.day) <= last_date_checked
            ][:14]

        # Descubrimiento de Anclajes de Tiempo
        last_rest_date = None
        pending_extra_rest = False
        
        # Anclaje de Lunes (Strict Weekly Sequence)
        # Asumimos el índice base de la sección como punto de inicio por defecto
        anchor_monday = date(2024, 1, 1) # Un lunes arbitrario en el pasado lejano
        anchor_shift_index = base_shift_index

        if prev_entries:
            # Encontrar el último descanso para el patrón de 8 días
            if prev_entries[0].shift_code == 'D' and date(prev_entries[0].year, prev_entries[0].month, prev_entries[0].day).weekday() == 6:
                pending_extra_rest = True
                last_rest_date = date(prev_entries[0].year, prev_entries[0].month, prev_entries[0].day) - timedelta(days=8)
            else:
                for e in prev_entries:
                    if e.shift_code == 'D':
                        last_rest_date = date(e.year, e.month, e.day)
                        break
                        
            # Encontrar el último turno real trabajado ('M', 'N', 'T') para anclar el ciclo semanal en la semana correcta
            work_shifts = [(e.shift_code, date(e.year, e.month, e.day)) for e in prev_entries if e.shift_code in shift_rotation]
            if work_shifts:
                most_recent_shift, prev_working_date = work_shifts[0]
                if most_recent_shift in shift_rotation:
                    anchor_shift_index = shift_rotation.index(most_recent_shift)
                    # El Lunes matemático que rige la semana de ese último turno trabajado
                    anchor_monday = prev_working_date - timedelta(days=prev_working_date.weekday())

        # Si no hay historial de descansos, forjamos el ciclo inicial
        if not last_rest_date:
            rest_day_start = (idx % 7) + 1
            last_rest_date = date(year, month, 1) - timedelta(days = 8 - rest_day_start)
            
        # Generar Secuencia Diaria
        for day in range(1, num_days + 1):
            current_date = date(year, month, day)

            # Check existing manual manual entries
            existing = ScheduleEntry.query.filter_by(
                worker_id=worker.id, year=year, month=month, day=day, is_auto_generated=False
            ).first()
            if existing:
                if existing.shift_code in ('D', 'DM', 'V'):
                    last_rest_date = current_date
                    pending_extra_rest = False
                continue

            # Check start_date mid-month entry
            if worker.start_date and current_date < worker.start_date:
                entries.append(ScheduleEntry(
                    worker_id=worker.id, year=year, month=month, day=day,
                    shift_code='NI', is_auto_generated=True
                ))
                continue

            # Check resignation
            if worker.resignation_date and current_date >= worker.resignation_date:
                entries.append(ScheduleEntry(
                    worker_id=worker.id, year=year, month=month, day=day,
                    shift_code='R', is_auto_generated=True
                ))
                continue

            # CÁLCULO DE CICLO SEMANAL ESTRICTO 
            # Hallamos qué Lunes rige la fecha actual
            current_monday = current_date - timedelta(days=current_date.weekday())
            # Diferencia en semanas vs nuestra semana ancla (la última vez que trabajó con certeza un turno base)
            weeks_diff = (current_monday - anchor_monday).days // 7
            
            # El índice de turno corresponde rotar estrictamente 1 por semana. 
            weekly_shift_index = (anchor_shift_index + weeks_diff) % len(shift_rotation)
            weekly_base_shift = shift_rotation[weekly_shift_index] if not is_fixed else shift_rotation[0]

            # DETERMINACIÓN FINAL DEL DÍA (Considerando Descansos)
            if section_a_rules:
                if current_date.weekday() >= 5: # 5=Sat, 6=Sun
                    shift = 'D'
                else:
                    shift = shift_rotation[0]
            elif pending_extra_rest:
                # Descanso de Lunes después del Domingo compensador
                shift = 'D'
                pending_extra_rest = False
                last_rest_date = current_date
            else:
                days_since_rest = (current_date - last_rest_date).days
                if days_since_rest >= 8:
                    shift = 'D'
                    if current_date.weekday() == 6: # Sunday
                        pending_extra_rest = True
                    else:
                        last_rest_date = current_date
                else:
                    shift = weekly_base_shift

            entries.append(ScheduleEntry(
                worker_id=worker.id, year=year, month=month, day=day,
                shift_code=shift, is_auto_generated=True
            ))

    return entries


def get_schedule_grid(year, month, group_filter=None, user_role='admin', username=None):
    """Returns the schedule data structured for the grid view.
    group_filter: 'all', 'staff', '1', '2', '3', or None
    user_role: 'admin', 'supervisor', etc to apply visibility rules.
    """
    num_days = calendar.monthrange(year, month)[1]

    workers = Worker.query.order_by(Worker.section, Worker.group_number,
                                     Worker.order_number).all()

    # MIGRAR A TURNO DIFERENCIADO (TD)
    for w in workers:
        name_upper = (w.full_name or '').upper()
        if 'GUERRERO VALLEJO' in name_upper or 'VASQUEZ ESTRELLA' in name_upper:
            w.section = 'TD'

    workers = _apply_monthly_snapshots(workers, year, month)

    # Filter to relevant workers
    relevant_workers = []
    for w in workers:
        # Hide if started in the future
        if w.start_date:
            if w.start_date.year > year or (w.start_date.year == year and w.start_date.month > month):
                continue

        # Hide if resigned in the past relative to the currently viewed month
        if w.resignation_date:
            if w.resignation_date.year > year or (w.resignation_date.year == year and w.resignation_date.month >= month):
                relevant_workers.append(w)
        # Otherwise show if active
        elif w.status == 'activo':
            relevant_workers.append(w)
        else:
            # Fallback for perfectly tracking historical data of 'inactivo' workers
            # Include them ONLY if they have schedule entries in this specific month
            has_entries = ScheduleEntry.query.filter_by(worker_id=w.id, year=year, month=month).count() > 0
            if has_entries:
                relevant_workers.append(w)

    # Apply strict RBAC username filter
    user_to_group = {'wormeno': 1, 'ainape': 2, 'jbellido': 3}
    if username in user_to_group:
        gnum = user_to_group[username]
        relevant_workers = [w for w in relevant_workers
                            if (w.section == 'D' and (w.group_number or 1) == gnum) 
                            or (w.section == 'C' and w.group_number == gnum)
                            or w.section == 'B'
                            or w.section == 'TD']
        group_filter = str(gnum) # Override to ensure correct section tabs render
    elif group_filter and group_filter != 'all':
        if group_filter == 'staff':
            relevant_workers = [w for w in relevant_workers if w.section in ('A', 'B', 'C', 'TD')]
        elif group_filter.isdigit():
            gnum = int(group_filter)
            relevant_workers = [w for w in relevant_workers
                                if (w.section == 'D' and (w.group_number or 1) == gnum) 
                                or w.section == 'B'
                                or (w.section == 'C' and w.group_number == gnum)
                                or w.section == 'TD']

    # Security Rules: Hide Section A from Supervisors and Auditor.
    # We already filtered them, but enforce strictly here for 'auditoria' or anyone bypassing.
    if user_role == 'supervisor' or username == 'auditoria':
        relevant_workers = [w for w in relevant_workers if w.section != 'A']

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

    # If filtering by a specific group, only show section D and section B
    if group_filter and group_filter.isdigit():
        gnum = int(group_filter)
        
        # Sec TD (Turno Diferenciado)
        td_workers = [w for w in workers if w.section == 'TD']
        if td_workers:
            sections.append({
                'key': 'TD',
                'name': 'Personal Turno Diferenciado',
                'groups': [{'label': '----- TURNO DIFERENCIADO -----', 'rows': _build_worker_rows(td_workers, entry_map, num_days)['rows']}],
            })

        # Sec B
        sec_b = [w for w in workers if w.section == 'B']
        if sec_b:
            sections.append({
                'key': 'B',
                'name': 'Área de Gestión de Video',
                'groups': [{'label': '----- GESTIÓN DE VIDEO -----', 'rows': _build_worker_rows(sec_b, entry_map, num_days)['rows']}],
            })

        # Sec C (Supervisor del grupo)
        sec_c = [w for w in workers if w.section == 'C']
        if sec_c:
            sections.append({
                'key': 'C',
                'name': 'Supervisor',
                'groups': [{'label': '----- SUPERVISORES -----', 'rows': _build_worker_rows(sec_c, entry_map, num_days)['rows']}],
            })

        # Sec D
        d_workers = [w for w in workers if w.section == 'D']
        if d_workers:
            groups_data = {'CCO': [], 'SCV': [], 'ALFA': []}
            for w in d_workers:
                area_key = w.area if w.area in ('CCO', 'SCV', 'ALFA') else 'CCO'
                groups_data[area_key].append(w)

            d_groups = []
            for area in ['CCO', 'SCV', 'ALFA']:
                area_workers = groups_data.get(area, [])
                if area_workers:
                    d_groups.append({
                        'label': f'----- OPERADORES {area} -----',
                        'rows': _build_worker_rows(area_workers, entry_map, num_days, sort_by_pattern=(area in ['CCO', 'SCV']))['rows'],
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
        ('A', 'Jefatura CCO, Planta Externa, Encargados y Coordinadores', False),
        ('B', 'Área de Gestión de Video', False),
        ('C', 'Supervisores', False),
        ('TD', 'Personal Turno Diferenciado', False),
    ]

    for sec_key, sec_name, do_sort in section_config:
        sec_workers = [w for w in workers if w.section == sec_key]
        if sec_workers:
            sections.append({
                'key': sec_key,
                'name': sec_name,
                'groups': [_build_worker_rows(sec_workers, entry_map, num_days, sort_by_pattern=do_sort)],
            })

    # Section D - show if 'all' or no filter
    if not group_filter or group_filter == 'all':
        d_workers = [w for w in workers if w.section == 'D']
        if d_workers:
            groups_data = {}
            for w in d_workers:
                g = w.group_number or 1
                if g not in groups_data:
                    groups_data[g] = {'CCO': [], 'SCV': [], 'ALFA': []}
                area_key = w.area if w.area in ('CCO', 'SCV', 'ALFA') else 'CCO'
                groups_data[g][area_key].append(w)

            d_groups = []
            for group_num in sorted(groups_data.keys()):
                for area in ['CCO', 'SCV', 'ALFA']:
                    area_workers = groups_data[group_num].get(area, [])
                    if area_workers:
                        d_groups.append({
                            'label': f'Grupo {group_num} - {area}',
                            'rows': _build_worker_rows(area_workers, entry_map, num_days, sort_by_pattern=(area in ['CCO', 'SCV']))['rows'],
                        })

            if d_groups:
                sections.append({
                    'key': 'D',
                    'name': 'Rol de Servicio Operativo',
                    'groups': d_groups,
                })

    return sections


def _build_worker_rows(workers, entry_map, num_days, sort_by_pattern=False):
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
                'allowed_shifts': w.allowed_shifts or 'M,T,N',
            },
            'days': days,
        })
        
    if sort_by_pattern:
        def get_first_rest_day(row_days):
            for i, d in enumerate(row_days):
                if d['shift'] == 'D':
                    return i
            return 999
            
        rows.sort(key=lambda r: (
            get_first_rest_day(r['days']), 
            "".join(d['shift'] or '_' for d in r['days']), 
            r['worker']['order_number'] or 0
        ))
        
    return {'rows': rows}

def cascade_forward_shift(worker_id, year, month, start_day, new_shift):
    from app.models.worker import Worker
    from app.models.schedule import ScheduleEntry
    from app.extensions import db
    from calendar import monthrange
    from datetime import date, timedelta
    
    worker = Worker.query.get(worker_id)
    if not worker or not worker.section or not (worker.section in ['D', 'TD'] or worker.section.startswith('Sección D') or worker.section.startswith('D')):
        return
        
    num_days = monthrange(year, month)[1]
    start_date = date(year, month, start_day)
    shift_rotation = ['M', 'N', 'T']
    
    if new_shift == 'D':
        # MODO 1: Auto-completar SOLAMENTE descansos.
        # Borramos descansos auto-generados posteriores. Respetamos los M/N/T.
        entries_to_delete = ScheduleEntry.query.filter(
            ScheduleEntry.worker_id == worker.id,
            ScheduleEntry.year == year,
            ScheduleEntry.month == month,
            ScheduleEntry.day > start_day,
            ScheduleEntry.is_auto_generated == True,
            ScheduleEntry.shift_code == 'D'
        ).all()
        for e in entries_to_delete:
            db.session.delete(e)
        db.session.flush()

        new_entries = []
        last_rest_date = start_date
        pending_extra_rest = True if start_date.weekday() == 6 else False
        
        for day in range(start_day + 1, num_days + 1):
            current_date = date(year, month, day)
            
            # Saltamos celdas que ya tengan entradas manuales
            existing = ScheduleEntry.query.filter_by(
                worker_id=worker.id, year=year, month=month, day=day, is_auto_generated=False
            ).first()
            if existing:
                if existing.shift_code in ('D', 'V', 'DM'):
                    last_rest_date = current_date
                    pending_extra_rest = False
                continue

            if worker.resignation_date and current_date >= worker.resignation_date:
                continue

            shift = None
            if pending_extra_rest:
                shift = 'D'
                pending_extra_rest = False
                last_rest_date = current_date
            else:
                days_since_rest = (current_date - last_rest_date).days
                if days_since_rest >= 8:
                    shift = 'D'
                    if current_date.weekday() == 6:
                        pending_extra_rest = True
                    else:
                        last_rest_date = current_date

            if shift == 'D':
                collision = ScheduleEntry.query.filter_by(worker_id=worker.id, year=year, month=month, day=day, is_auto_generated=True).first()
                if collision:
                    collision.shift_code = 'D'
                else:
                    new_entries.append(ScheduleEntry(
                        worker_id=worker.id, year=year, month=month, day=day,
                        shift_code='D', is_auto_generated=True
                    ))
                    
        for e in new_entries:
            db.session.add(e)
        db.session.commit()
    
    elif new_shift in shift_rotation:
        # MODO 2: Auto-completar SOLAMENTE M, N, T (Nunca inyecta D)
        # 1. Determinar el Anclaje
        anchor_monday = start_date - timedelta(days=start_date.weekday())
        anchor_shift_index = shift_rotation.index(new_shift)
        
        # Borramos turnos M/N/T auto-generados posteriores. Respetamos los D.
        entries_to_delete = ScheduleEntry.query.filter(
            ScheduleEntry.worker_id == worker.id,
            ScheduleEntry.year == year,
            ScheduleEntry.month == month,
            ScheduleEntry.day > start_day,
            ScheduleEntry.is_auto_generated == True,
            ScheduleEntry.shift_code.in_(shift_rotation)
        ).all()
        for e in entries_to_delete:
            db.session.delete(e)
        db.session.flush()

        new_entries = []
        for day in range(start_day + 1, num_days + 1):
            current_date = date(year, month, day)
            
            # Saltamos si ya hay CUALQUIER registro existente (manual o auto-generado tipo D)
            existing = ScheduleEntry.query.filter_by(
                worker_id=worker.id, year=year, month=month, day=day
            ).first()
            if existing: # Si ya hay D (incluso autogenerado) u otra cosa manual, lo esquivamos.
                continue
                
            if worker.resignation_date and current_date >= worker.resignation_date:
                continue
                
            current_monday = current_date - timedelta(days=current_date.weekday())
            weeks_diff = (current_monday - anchor_monday).days // 7
            weekly_shift_index = (anchor_shift_index + weeks_diff) % len(shift_rotation)
            shift = shift_rotation[weekly_shift_index]
                    
            new_entries.append(ScheduleEntry(
                worker_id=worker.id, year=year, month=month, day=day,
                shift_code=shift, is_auto_generated=True
            ))
            
        for e in new_entries:
            db.session.add(e)
        db.session.commit()
