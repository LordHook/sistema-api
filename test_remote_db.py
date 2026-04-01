import paramiko

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, user, password, timeout=10)

def exec_cmd(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode('utf-8', 'ignore').strip()

print("Querying production Postgres for workers 1 to 5...")
script = """
from app import create_app
from app.models.worker import Worker
app = create_app()
with app.app_context():
    workers = Worker.query.order_by(Worker.order_number).limit(6).all()
    for w in workers:
        print(f"ID:{w.id}, ONum:{w.order_number}, Name:{w.full_name}, Status: '{w.status}', Resign: '{w.resignation_date}'")
"""
with open("test_db.py", "w") as f:
    f.write(script)

import os
os.system("scp test_db.py root@172.16.10.70:/opt/cco/test_db.py")
# We can't use scp with password easily, so we write the file via echo

echo_cmd = f'''cat << 'EOF' > /opt/cco/test_db.py
{script}
EOF'''

ssh.exec_command(echo_cmd)
import time
time.sleep(1)

print(exec_cmd("cd /opt/cco && source .venv/bin/activate && python3 test_db.py"))

ssh.close()
