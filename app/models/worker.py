from datetime import datetime, timezone
from app.extensions import db


class Worker(db.Model):
    __tablename__ = 'workers'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.Integer, unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    regime = db.Column(db.String(10), nullable=False)  # 'CAS' | 'LS'
    section = db.Column(db.String(5), nullable=False)   # 'A' | 'B' | 'C' | 'D'
    area = db.Column(db.String(50), nullable=False)
    # 'Jefatura' | 'Gestion_Video' | 'Supervisores' | 'CCO' | 'SCV'
    group_number = db.Column(db.Integer, nullable=True)  # 1, 2, 3 (solo sección D)
    status = db.Column(db.String(20), nullable=False, default='activo')  # 'activo' | 'inactivo'
    resignation_date = db.Column(db.Date, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    allowed_shifts = db.Column(db.String(20), default='M,T,N')  # Ej: 'M,T,N', 'T,N'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    schedule_entries = db.relationship('ScheduleEntry', backref='worker', lazy='dynamic',
                                       cascade='all, delete-orphan')
    attendance_records = db.relationship('AttendanceRecord', backref='worker', lazy='dynamic',
                                         cascade='all, delete-orphan')

    @property
    def full_name(self):
        return f'{self.last_name}, {self.first_name}'

    @property
    def display_name(self):
        return f'{self.first_name} {self.last_name}'

    @staticmethod
    def next_order_number():
        max_order = db.session.query(db.func.max(Worker.order_number)).scalar()
        return (max_order or 0) + 1

    def __repr__(self):
        return f'<Worker {self.order_number}: {self.full_name}>'

class MonthlyWorkerStatus(db.Model):
    __tablename__ = 'monthly_worker_status'
    __table_args__ = (
        db.UniqueConstraint('worker_id', 'year', 'month', name='uq_monthly_status_worker_period'),
        db.Index('ix_monthly_status_period', 'year', 'month'),
    )

    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id', ondelete='CASCADE'), nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    section = db.Column(db.String(5), nullable=False)
    area = db.Column(db.String(50), nullable=True)
    group_number = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    worker = db.relationship('Worker', backref=db.backref('monthly_statuses', lazy='dynamic', cascade='all, delete-orphan'), overlaps="attendance_records,schedule_entries,worker")

    def __repr__(self):
        return f'<MonthlyStatus {self.worker_id} {self.year}-{self.month:02d}: Sec {self.section} Grp {self.group_number}>'
