from datetime import datetime, timezone
from flask_login import UserMixin
from app.extensions import db, bcrypt


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False, default='')
    role = db.Column(db.String(20), nullable=False, default='standard')  # 'admin' | 'standard' | 'supervisor'
    assigned_group = db.Column(db.Integer, nullable=True) # 1, 2, or 3 for supervisors
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic',
                                 foreign_keys='AuditLog.user_id')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
