from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app.models.audit import AuditLog
from app.extensions import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active:
            login_user(user)
            AuditLog.log(user_id=user.id, action='login', details='Inicio de sesión exitoso')
            db.session.commit()
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.dashboard'))

        flash('Usuario o contraseña incorrectos.', 'error')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'success')
    return redirect(url_for('auth.login'))
