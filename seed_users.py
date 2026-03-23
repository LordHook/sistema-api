import os
from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()

def create_user(username, password, role, group=None):
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username, role=role, assigned_group=group)
        user.set_password(password)
        db.session.add(user)
        print(f"Creado usuario: {username} (Rol: {role}, Grupo: {group})")
    else:
        user.role = role
        user.assigned_group = group
        user.set_password(password)
        print(f"Actualizado usuario: {username}")
    db.session.commit()

with app.app_context():
    print("Iniciando seeder de usuarios...")
    # Admin is handled separately but we add the requested ones
    create_user('wormeno', 'Cco_G1_2026$', 'supervisor', 1)
    create_user('ainape', 'Cco_G2_2026$', 'supervisor', 2)
    create_user('jbellido', 'Cco_G3_2026$', 'supervisor', 3)
    create_user('auditoria', 'Cco_Audit_2026$', 'visualizador', None)
    print("Seeder finalizado.")
