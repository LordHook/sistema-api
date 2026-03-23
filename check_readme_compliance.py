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

check_script = """
echo "--- Checking OS Users ---"
id cco || echo "User cco does not exist"

echo "--- Checking Directory /opt/cco ---"
ls -la /opt/cco

echo "--- Checking systemd service ---"
systemctl status cco || echo "Service cco not found"

echo "--- Checking Postgres Databases ---"
su - postgres -c "psql -l | grep cco_" || echo "No cco_ databases found"

echo "--- Checking Nginx ---"
systemctl status nginx || echo "Nginx not running"
ls -l /etc/nginx/conf.d/ || echo "No nginx conf.d"
"""

stdin, stdout, stderr = ssh.exec_command(check_script)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print(f"Error: {err}")

ssh.close()
