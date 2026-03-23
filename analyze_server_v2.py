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

analysis_script = """
echo "--- POSTGRES TABLES ---"
# List tables
su - postgres -c "psql -d cemovi_db -t -c \\"SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'\\";"

echo "--- RECORD COUNTS ---"
# Count records in main tables
su - postgres -c "psql -d cemovi_db -c \\"SELECT 
    (SELECT count(*) FROM workers) AS workers,
    (SELECT count(*) FROM users) AS users,
    (SELECT count(*) FROM attendance_records) AS attendance,
    (SELECT count(*) FROM schedule_entries) AS schedules,
    (SELECT count(*) FROM audit_logs) AS logs;\\""

echo "--- PROCESS STATUS ---"
# Check if run.py is running
pgrep -fl run.py || echo "Application process (run.py) NOT FOUND"

echo "--- SYSTEM HEALTH ---"
# Check memory and disk
free -h | grep Mem
df -h /opt/cco
"""

stdin, stdout, stderr = ssh.exec_command(analysis_script)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print(f"Error: {err}")

ssh.close()
