import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, user, password, timeout=10)

setup_users_script = """
cd /opt/cco
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)

echo "--- Current Users in cco_db ---"
python3 -c "
from app import create_app;
from app.extensions import db;
from app.models.user import User;
app = create_app();
with app.app_context():
    users = User.query.all();
    for u in users:
        print(f'User: {u.username}, Role: {u.role}, Name: {u.full_name}, Group: {u.assigned_group}')
"

echo "--- Creating Missing Users in cco_db ---"
python3 -c "
from app import create_app;
from app.extensions import db;
from app.models.user import User;
app = create_app();
with app.app_context():
    # 1. Fix admin role if not 'admin'
    admin = User.query.filter_by(username='admin').first()
    if admin and admin.role != 'admin':
        admin.role = 'admin'
        print('Fixed admin role.')
    
    # 2. Add Supervisors
    supervisors = [
        ('supervisor1', 'soporte12#$', 'Supervisor Grupo 1', 1),
        ('supervisor2', 'soporte12#$', 'Supervisor Grupo 2', 2),
        ('supervisor3', 'soporte12#$', 'Supervisor Grupo 3', 3),
    ]
    for uname, pwd, name, group in supervisors:
        if not User.query.filter_by(username=uname).first():
            u = User(username=uname, full_name=name, role='supervisor', assigned_group=group)
            u.set_password(pwd)
            db.session.add(u)
            print(f'Created supervisor: {uname}')
            
    # 3. Add Visualizador (Auditor)
    auditor_uname = 'auditoria'
    if not User.query.filter_by(username=auditor_uname).first():
        u = User(username=auditor_uname, full_name='Auditoría de Asistencias', role='visualizador')
        u.set_password('soporte12#$')
        db.session.add(u)
        print(f'Created visualizador: {auditor_uname}')
        
    db.session.commit()
"
"""

stdin, stdout, stderr = ssh.exec_command(setup_users_script)
print("OUT:", stdout.read().decode('utf-8', 'replace'))
err = stderr.read().decode('utf-8', 'replace')
if err: print("ERR:", err)

ssh.close()
