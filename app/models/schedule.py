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
        'M': '#4ade80',  # Soft Green (Emerald 400)
        'T': '#fcd34d',  # Soft Amber (Amber 300)
        'N': '#818cf8',  # Soft Indigo (Indigo 400)
        'D': '#94a3b8',  # Soft Slate (Slate 400)
        'V': '#22d3ee',  # Soft Cyan (Cyan 400)
        'C': '#c084fc',  # Soft Purple (Purple 400)
        'R': '#f87171',  # Soft Red (Red 400)
    }

    def __repr__(self):
        return f'<Schedule {self.worker_id} {self.year}-{self.month:02d}-{self.day:02d}: {self.shift_code}>'
