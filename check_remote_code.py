import paramiko
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, user, password, timeout=10)

cmd = """
echo "=== GUNICORN PROCESSES ==="
ps aux | grep gunicorn | grep -v grep

echo "=== MODO PINCEL IN SCHEDULE.HTML ==="
cat /opt/cco/app/templates/schedule.html | grep "Modo Pincel" -A 10

echo "=== DATABASE URL IN .ENV ==="
cat /opt/cco/.env | grep DATABASE_URL

echo "=== COUNT OF WORKERS IN CCO_DB ==="
su - postgres -c "psql -d cco_db -t -c \\"SELECT count(*) FROM workers;\\""

echo "=== COUNT OF WORKERS IN CEMOVI_DB ==="
su - postgres -c "psql -d cemovi_db -t -c \\"SELECT count(*) FROM workers;\\"" || echo "cemovi_db error"

echo "=== LATEST COMMITS IN GITHUB ==="
# Check if /opt/cco is a git repository
if [ -d /opt/cco/.git ]; then
    cd /opt/cco && git log -n 3 --oneline
else
    echo "Not a git repo."
fi
"""

stdin, stdout, stderr = ssh.exec_command(cmd)

print(stdout.read().decode('utf-8', 'replace'))
err = stderr.read().decode('utf-8', 'replace')
if err: print("ERR:", err)

ssh.close()
