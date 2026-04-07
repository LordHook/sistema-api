from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import date
from functools import wraps
from app.extensions import db
from app.models.worker import Worker
from app.models.audit import AuditLog

personnel_bp = Blueprint('personnel', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'error': 'Acceso no autorizado'}), 403
        return f(*args, **kwargs)
    return decorated


@personnel_bp.route('/personnel')
@login_required
@admin_required
def personnel_page():
    return render_template('personnel.html')


@personnel_bp.route('/api/personnel', methods=['GET'])
@login_required
def get_personnel():
    status_filter = request.args.get('status', 'activo')
    year_str = request.args.get('year')
    month_str = request.args.get('month')
    
    year = int(year_str) if year_str and year_str.isdigit() else None
    month = int(month_str) if month_str and month_str.isdigit() else None
    
    workers = Worker.query.order_by(Worker.section, Worker.group_number, Worker.order_number).all()
    filtered_workers = []
    
    for w in workers:
        if status_filter == 'inactivo':
            # VISTA HISTORIAL
            if not year or not month:
                # Ver Totalizado (Histórico Global)
                if w.status in ['inactivo', 'deshabilitado'] or w.resignation_date is not None:
                    filtered_workers.append(w)
            else:
                # Filtro Estricto: Solo mostrar de ESTE MES
                if w.resignation_date:
                    if w.resignation_date.year == year and w.resignation_date.month == month:
                        filtered_workers.append(w)
                else:
                    # Inactivos "Legacy" sin fecha de cese: No pertenecen a ningún mes específico.
                    # Quedan ocultos del filtro mensual para limpiar la vista. Solo se ven en "Ver Totalizado".
                    pass
        else:
            # VISTA PERSONAL ACTIVO (MATRIZ / ROL)
            if w.resignation_date and year and month:
                res_y = w.resignation_date.year
                res_m = w.resignation_date.month
                if year > res_y or (year == res_y and month > res_m):
                    # El mes que se visualiza es POSTERIOR a su renuncia. Ya no figura.
                    continue
                # Si llegamos aquí, la renuncia es de ESTE mes o FUTURA. ¡Debe mostrarse!
            else:
                # Si NO TIENE fecha de cese (o no hay filtro), aplicamos el bloqueo estricto de legacy inactivos.
                if w.status in ['inactivo', 'deshabilitado']:
                    continue
            
            filtered_workers.append(w)

    response_data = []
    from app.models.worker import MonthlyWorkerStatus
    
    for w in filtered_workers:
        snap_section = w.section
        snap_area = w.area
        snap_group = w.group_number
        
        if year and month:
            snap = MonthlyWorkerStatus.query.filter_by(worker_id=w.id, year=year, month=month).first()
            if snap:
                snap_section = snap.section
                snap_group = snap.group_number
                if hasattr(snap, 'area') and snap.area is not None:
                    snap_area = snap.area
                    
        response_data.append({
            'id': w.id,
            'order_number': w.order_number,
            'first_name': w.first_name,
            'last_name': w.last_name,
            'full_name': w.full_name,
            'regime': w.regime,
            'section': snap_section,
            'area': snap_area,
            'group_number': snap_group,
            'status': w.status,
            'resignation_date': w.resignation_date.isoformat() if w.resignation_date else None,
        })

    return jsonify(response_data)


@personnel_bp.route('/api/personnel', methods=['POST'])
@login_required
@admin_required
def create_worker():
    data = request.get_json()

    worker = Worker(
        order_number=Worker.next_order_number(),
        first_name=data['first_name'],
        last_name=data['last_name'],
        regime=data['regime'],
        section=data['section'],
        area=data['area'],
        group_number=data.get('group_number'),
        status='activo',
    )
    db.session.add(worker)

    from app.models.worker import MonthlyWorkerStatus
    effective_year = data.get('effective_year')
    effective_month = data.get('effective_month')
    
    current_date = date.today()
    if not effective_year or not effective_month:
        effective_year = current_date.year
        effective_month = current_date.month
        
    snap = MonthlyWorkerStatus(
        worker=worker,
        year=effective_year,
        month=effective_month,
        section=worker.section,
        area=worker.area,
        group_number=worker.group_number
    )
    db.session.add(snap)

    AuditLog.log(
        user_id=current_user.id,
        action='worker_change',
        target_worker_id=None,
        details=f'Trabajador creado: {worker.full_name}',
    )

    db.session.commit()

    # Update audit log with worker id
    log_entry = AuditLog.query.order_by(AuditLog.id.desc()).first()
    if log_entry:
        log_entry.target_worker_id = worker.id
        db.session.commit()

    return jsonify({
        'id': worker.id,
        'order_number': worker.order_number,
        'message': 'Trabajador creado exitosamente',
    }), 201


@personnel_bp.route('/api/personnel/<int:worker_id>', methods=['PUT'])
@login_required
@admin_required
def update_worker(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    data = request.get_json()

    changes = []
    section_changed = False
    
    for field in ['first_name', 'last_name', 'regime', 'section', 'area', 'group_number']:
        if field in data and getattr(worker, field) != data[field]:
            changes.append(f'{field}: {getattr(worker, field)} → {data[field]}')
            setattr(worker, field, data[field])
            if field in ['section', 'group_number', 'area']:
                section_changed = True

    # Handle resignation
    if 'resignation_date' in data:
        old_date = worker.resignation_date
        new_date = date.fromisoformat(data['resignation_date']) if data['resignation_date'] else None
        if old_date != new_date:
            worker.resignation_date = new_date
            worker.status = 'inactivo' if new_date else 'activo'
            changes.append(
                f'resignation_date: {old_date} → {new_date}, status: {"inactivo" if new_date else "activo"}'
            )

    if changes:
        if section_changed:
            from app.models.worker import MonthlyWorkerStatus
            
            # Use provided effective date or default to current
            effective_year = data.get('effective_year')
            effective_month = data.get('effective_month')
            
            current_date = date.today()
            if not effective_year or not effective_month:
                effective_year = current_date.year
                effective_month = current_date.month
                
            # Update existing snapshots from the effective month onwards
            snapshots = MonthlyWorkerStatus.query.filter(
                MonthlyWorkerStatus.worker_id == worker.id,
                db.or_(
                    MonthlyWorkerStatus.year > effective_year,
                    db.and_(MonthlyWorkerStatus.year == effective_year, MonthlyWorkerStatus.month >= effective_month)
                )
            ).all()
            
            for snap in snapshots:
                snap.section = worker.section
                snap.area = worker.area
                snap.group_number = worker.group_number

        AuditLog.log(
            user_id=current_user.id,
            action='worker_change',
            target_worker_id=worker.id,
            details='; '.join(changes),
        )

    db.session.commit()
    return jsonify({'message': 'Trabajador actualizado exitosamente'})


@personnel_bp.route('/api/personnel/<int:worker_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_worker(worker_id):
    worker = Worker.query.get_or_404(worker_id)

    AuditLog.log(
        user_id=current_user.id,
        action='worker_change',
        target_worker_id=worker.id,
        details=f'Trabajador deshabilitado: {worker.full_name}',
    )

    worker.status = 'inactivo'
    
    # Asignar fecha de cese automáticamente al mes actual si no la tenía
    if not worker.resignation_date:
        from datetime import datetime
        worker.resignation_date = datetime.utcnow().date()
        
    db.session.commit()
    return jsonify({'message': 'Trabajador deshabilitado exitosamente'})
