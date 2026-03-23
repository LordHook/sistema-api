from flask import Blueprint, request, send_file
from flask_login import login_required, current_user
from datetime import date
from app.services.export_service import (
    export_schedule_excel,
    export_schedule_pdf,
    export_audit_excel,
    export_attendance_excel,
)
from app.models.audit import AuditLog
from app.extensions import db

export_bp = Blueprint('export', __name__)


@export_bp.route('/export/schedule')
@login_required
def export_schedule():
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    fmt = request.args.get('format', 'xlsx')

    month_names = [
        '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]

    AuditLog.log(
        user_id=current_user.id,
        action='export',
        details=f'Exportación de horario {month_names[month]} {year} en formato {fmt.upper()}',
    )
    db.session.commit()

    if fmt == 'pdf':
        output = export_schedule_pdf(year, month)
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Rol_Servicio_{month_names[month]}_{year}.pdf',
        )
    else:
        output = export_schedule_excel(year, month)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'Rol_Servicio_{month_names[month]}_{year}.xlsx',
        )


@export_bp.route('/export/audit')
@login_required
def export_audit():
    filters = {}
    if request.args.get('group'):
        filters['group'] = request.args.get('group')
    if request.args.get('start_date'):
        filters['start_date'] = request.args.get('start_date')
    if request.args.get('end_date'):
        filters['end_date'] = request.args.get('end_date')
    if request.args.get('action'):
        filters['action'] = request.args.get('action')

    AuditLog.log(
        user_id=current_user.id,
        action='export',
        details=f'Exportación de registro de auditoría',
    )
    db.session.commit()

    output = export_audit_excel(filters)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='Registro_Auditoria_CCO.xlsx',
    )


@export_bp.route('/export/attendance')
@login_required
def export_attendance():
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    
    if current_user.role == 'supervisor':
        group = str(current_user.assigned_group) if current_user.assigned_group else request.args.get('group', '1')
    elif current_user.role in ['admin', 'visualizador']:
        group = request.args.get('group', None)
    else:
        group = 'all'

    month_names = [
        '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]

    AuditLog.log(
        user_id=current_user.id,
        action='export',
        details=f'Exportación de asistencia {month_names[month]} {year} (Grupo {group or "Todos"})',
    )
    db.session.commit()

    output = export_attendance_excel(year, month, group, current_user.role)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'Asistencia_CCO_{month_names[month]}_{year}.xlsx',
    )

