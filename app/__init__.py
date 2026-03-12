import os
from flask import Flask
from app.config import config_map
from app.extensions import db, migrate, login_manager, bcrypt


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name, config_map['development']))

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Import models so they are registered with SQLAlchemy
    from app.models import User, Worker, ScheduleEntry, AttendanceRecord, AuditLog  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.personnel import personnel_bp
    from app.routes.schedule import schedule_bp
    from app.routes.attendance import attendance_bp
    from app.routes.audit import audit_bp
    from app.routes.export import export_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(personnel_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(export_bp)

    # Create tables and default admin user
    with app.app_context():
        db.create_all()
        _create_default_admin()

    return app


def _create_default_admin():
    from app.models.user import User
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            full_name='Administrador del Sistema',
            role='admin',
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
