from datetime import datetime, timezone
from app.extensions import db


class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    __table_args__ = (
        db.UniqueConstraint('worker_id', 'attendance_date', name='uq_attendance_worker_date'),
    )

    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False, index=True)
    attendance_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)  # 'asistio' | 'falto' | 'tardanza'
    shift_code = db.Column(db.String(5), nullable=True)  # M | T | N (turno asignado ese día)
    validated_by_admin = db.Column(db.Boolean, default=False)
    validated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    validator = db.relationship('User', foreign_keys=[validated_by])

    STATUS_LABELS = {
        'asistio': 'Asistió',
        'falto': 'Faltó',
        'tardanza': 'Tardanza',
    }

    STATUS_COLORS = {
        'asistio': '#22c55e',
        'falto': '#ef4444',
        'tardanza': '#f59e0b',
    }

    def __repr__(self):
        return f'<Attendance {self.worker_id} {self.attendance_date}: {self.status}>'
