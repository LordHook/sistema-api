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

daemon_command = """
cd /opt/cco
source .venv/bin/activate
pkill -f gunicorn || true
pkill -f run.py || true
# Use --daemon and proper logs
# timeout 90 for database initialization if needed
.venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 --chdir /opt/cco "app:create_app()" --timeout 90 --access-logfile /opt/cco/access.log --error-logfile /opt/cco/error.log --daemon
sleep 3
pgrep -fl gunicorn
netstat -tuln | grep 5000
"""

stdin, stdout, stderr = ssh.exec_command(daemon_command)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print(f"Error: {err}")

ssh.close()
