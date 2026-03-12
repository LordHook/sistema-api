from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.models.audit import AuditLog
from app.models.worker import Worker

audit_bp = Blueprint('audit', __name__)


@audit_bp.route('/api/audit')
@login_required
def get_audit_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    query = AuditLog.query.order_by(AuditLog.timestamp.desc())

    # Filters
    group = request.args.get('group')
    if group:
        group_num = int(group)
        worker_ids = [w.id for w in Worker.query.filter_by(group_number=group_num).all()]
        query = query.filter(AuditLog.target_worker_id.in_(worker_ids))

    action = request.args.get('action')
    if action:
        query = query.filter_by(action=action)

    start_date = request.args.get('start_date')
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)

    end_date = request.args.get('end_date')
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date + ' 23:59:59')

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items

    return jsonify({
        'logs': [{
            'id': log.id,
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'user': log.user.username if log.user else 'Sistema',
            'action': log.action,
            'action_label': AuditLog.ACTION_LABELS.get(log.action, log.action),
            'worker': log.target_worker.full_name if log.target_worker else '-',
            'target_date': log.target_date.isoformat() if log.target_date else '-',
            'old_value': log.old_value or '-',
            'new_value': log.new_value or '-',
            'details': log.details or '',
        } for log in logs],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page,
    })
