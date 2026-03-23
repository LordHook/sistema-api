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

# 1. Check .env
# 2. Check current active pg_hba.conf path from postgres itself
# 3. Test psql connection
debug_script = """
echo "--- ENV ---"
cat /opt/cco/.env 2>/dev/null || echo ".env not found"

echo "--- PG SETTINGS ---"
su - postgres -c "psql -t -P format=unaligned -c 'show hba_file;'" 2>/dev/null || echo "Could not get hba_file"

echo "--- PSQL CONNECTION TEST ---"
su - postgres -c "psql -U cemovi_user -d cemovi_db -h localhost -c 'SELECT 1'" 2>&1
"""

stdin, stdout, stderr = ssh.exec_command(debug_script)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print(f"Error: {err}")

ssh.close()
