from datetime import datetime, timezone
from app.extensions import db


class ScheduleEntry(db.Model):
    __tablename__ = 'schedule_entries'
    __table_args__ = (
        db.UniqueConstraint('worker_id', 'year', 'month', 'day', name='uq_schedule_worker_date'),
        db.Index('ix_schedule_period', 'year', 'month'),
    )

    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    day = db.Column(db.Integer, nullable=False)
    shift_code = db.Column(db.String(5), nullable=False)  # M | T | N | D | V | C | R
    is_auto_generated = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    SHIFT_LABELS = {
        'M': 'Mañana (06:00-14:00)',
        'T': 'Tarde (14:00-22:00)',
        'N': 'Noche (22:00-06:00)',
        'D': 'Descanso',
        'V': 'Vacaciones',
        'C': 'Compensado',
        'R': 'Renuncia',
    }

    SHIFT_COLORS = {
        'M': '#22c55e',  # green
        'T': '#f59e0b',  # amber
        'N': '#6366f1',  # indigo
        'D': '#64748b',  # slate
        'V': '#06b6d4',  # cyan
        'C': '#a855f7',  # purple
        'R': '#ef4444',  # red
    }

    def __repr__(self):
        return f'<Schedule {self.worker_id} {self.year}-{self.month:02d}-{self.day:02d}: {self.shift_code}>'
