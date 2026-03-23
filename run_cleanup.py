import paramiko
import sys
import os

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'
extract_dir = '/opt/cco'

def ssh_interactive_handler(title, instructions, prompt_list):
    return [password for _ in prompt_list]

print("Connecting to SSH...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(host, port, user, password, timeout=10)
except paramiko.ssh_exception.AuthenticationException:
    t = paramiko.Transport((host, port))
    t.connect()
    t.auth_interactive(user, ssh_interactive_handler)
    ssh._transport = t

cleanup_script = """#!/bin/bash
cd /opt/cco
source .venv/bin/activate
export FLASK_APP=run.py
export FLASK_ENV=production
export DATABASE_URL=postgresql://cemovi_user:password@localhost:5432/cemovi_db

python3 -c "
from app import create_app;
from app.extensions import db;
from app.models.worker import Worker;
from app.models.schedule import ScheduleEntry;
from app.models.attendance import AttendanceRecord;
app = create_app();
with app.app_context():
    print('Cleaning up validation data...')
    AttendanceRecord.query.delete()
    ScheduleEntry.query.delete()
    Worker.query.delete()
    db.session.commit()
    print('Tables Workers, Schedules, and Attendance cleared.')
"

# Restart application
pkill -f run.py || true
nohup python3 run.py --host=0.0.0.0 --port=5000 > app.log 2>&1 &
echo 'Application restarted.'
"""

print("Executing cleanup script on remote...")
stdin, stdout, stderr = ssh.exec_command(f"cat << 'EOF' > {extract_dir}/cleanup.sh\n{cleanup_script}\nEOF\nbash {extract_dir}/cleanup.sh")

print(stdout.read().decode(errors='replace'))
err = stderr.read().decode(errors='replace')
if err:
    print(f"Error: {err}")

ssh.close()
print("Cleanup Complete!")
