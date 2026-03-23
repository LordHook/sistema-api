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

bash_script = """
su - postgres -c "psql -d cco_db -c \\"ALTER TABLE users ADD COLUMN IF NOT EXISTS assigned_group INTEGER;\\""
cd /opt/cco
source .venv/bin/activate
python3 manage_users.py
"""

stdin, stdout, stderr = ssh.exec_command(bash_script)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print(f"Error: {err}")

ssh.close()
