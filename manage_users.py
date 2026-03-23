import paramiko
import sys

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

def ssh_interactive_handler(title, instructions, prompt_list):
    return [password for _ in prompt_list]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(host, port, user, password, timeout=10)
except paramiko.ssh_exception.AuthenticationException:
    t = paramiko.Transport((host, port))
    t.connect()
    t.auth_interactive(user, ssh_interactive_handler)
    ssh._transport = t

# 1. Check current users
# 2. Add supervisors and visualizador
# 3. Enable schedule generation by ensuring role is 'admin'
setup_users_script = """
cd /opt/cco
source .venv/bin/activate
export FLASK_APP=run.py
export FLASK_ENV=production
export DATABASE_URL=postgresql://cemovi_user:password@localhost:5432/cemovi_db

echo "--- Current Users ---"
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

echo "--- Creating Missing Users ---"
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

echo "--- Restarting Service ---"
pkill -f run.py || true
nohup python3 run.py --host=0.0.0.0 --port=5000 > app.log 2>&1 &
"""

stdin, stdout, stderr = ssh.exec_command(setup_users_script)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print(f"Error: {err}")

ssh.close()
