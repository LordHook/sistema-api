from datetime import datetime, timezone
from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False)
    # 'schedule_change' | 'attendance_change' | 'worker_change' | 'login' | 'export'
    target_worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=True)
    target_date = db.Column(db.Date, nullable=True)
    old_value = db.Column(db.String(255), nullable=True)
    new_value = db.Column(db.String(255), nullable=True)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    target_worker = db.relationship('Worker', foreign_keys=[target_worker_id])

    ACTION_LABELS = {
        'schedule_change': 'Cambio de Horario',
        'attendance_change': 'Cambio de Asistencia',
        'worker_change': 'Cambio de Personal',
        'login': 'Inicio de Sesión',
        'export': 'Exportación',
    }

    @staticmethod
    def log(user_id, action, target_worker_id=None, target_date=None,
            old_value=None, new_value=None, details=None):
        entry = AuditLog(
            user_id=user_id,
            action=action,
            target_worker_id=target_worker_id,
            target_date=target_date,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            details=details,
        )
        db.session.add(entry)
        return entry

    def __repr__(self):
        return f'<AuditLog {self.action} by user {self.user_id} at {self.timestamp}>'
