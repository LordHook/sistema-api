import sys
import os

from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if admin:
        admin.set_password('admin123')
        db.session.commit()
        print("La contraseña del usuario 'admin' ha sido restablecida a: admin123")
    else:
        print("El usuario 'admin' no existe en la base de datos.")
        print("Los usuarios actuales en el sistema son:")
        users = User.query.all()
        for u in users:
            print(f"- Usuario: {u.username} | Rol: {u.role}")
