import paramiko

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, user, password, timeout=10)

cmd = """
cd /opt/cco
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)

python3 -c "
from app import create_app
from app.services.schedule_generator import generate_monthly_schedule
import datetime

app = create_app()
with app.app_context():
    count = generate_monthly_schedule(2026, 3)
    print(f'Generated {count} entries for March 2026.')
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("OUT:", stdout.read().decode('utf-8', 'replace'))
err = stderr.read().decode('utf-8', 'replace')
if err: print("ERR:", err)

ssh.close()
