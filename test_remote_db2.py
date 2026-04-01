import paramiko

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, user, password, timeout=10)

script = """
import sys
sys.path.append('/opt/cco')
from app import create_app
from app.models.worker import Worker
app = create_app()
with app.app_context():
    workers = Worker.query.order_by(Worker.order_number).limit(6).all()
    for w in workers:
        print(f"ONum:{w.order_number}, Name:{w.full_name}, Status: '{w.status}', Resign: '{w.resignation_date}'")
"""

stdin, stdout, stderr = ssh.exec_command("cat << 'EOF' > /opt/cco/test_db2.py\n" + script + "\nEOF")
stdout.channel.recv_exit_status()

stdin, stdout, stderr = ssh.exec_command("cd /opt/cco && source .venv/bin/activate && python3 test_db2.py")
print(stdout.read().decode('utf-8', 'ignore').strip())
print(stderr.read().decode('utf-8', 'ignore').strip())

ssh.close()
