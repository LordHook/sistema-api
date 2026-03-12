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
    workers = Worker.query.order_by(Worker.section, Worker.group_number,
                                     Worker.order_number).all()
    return jsonify([{
        'id': w.id,
        'order_number': w.order_number,
        'first_name': w.first_name,
        'last_name': w.last_name,
        'full_name': w.full_name,
        'regime': w.regime,
        'section': w.section,
        'area': w.area,
        'group_number': w.group_number,
        'status': w.status,
        'resignation_date': w.resignation_date.isoformat() if w.resignation_date else None,
    } for w in workers])


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
    for field in ['first_name', 'last_name', 'regime', 'section', 'area', 'group_number']:
        if field in data and getattr(worker, field) != data[field]:
            changes.append(f'{field}: {getattr(worker, field)} → {data[field]}')
            setattr(worker, field, data[field])

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
        details=f'Trabajador eliminado: {worker.full_name}',
    )

    db.session.delete(worker)
    db.session.commit()
    return jsonify({'message': 'Trabajador eliminado exitosamente'})
