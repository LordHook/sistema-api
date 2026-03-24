import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

print("Connecting to RHEL 10 via SSH...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, user, password, timeout=10)

cmd = """
echo "Syncing from Github..."
cd /api || cd /opt/cco  # Fallback to /opt/cco if /api does not exist, as per previous conventions
git reset --hard HEAD
git clean -fd
git pull origin main

echo "Stopping existing Python instances..."
pkill -f "python3 run.py" || true

echo "Starting Application in background..."
nohup python3 run.py --host=0.0.0.0 --port=5000 > app.log 2>&1 &
sleep 2
echo "Service restarted."
"""

print("Executing Remote Commands...")
stdin, stdout, stderr = ssh.exec_command(cmd)

# Wait for commands to finish executing
exit_status = stdout.channel.recv_exit_status()

print("OUT:")
for line in stdout:
    print(line.strip())

err = stderr.read().decode('utf-8', 'replace').strip()
if err: 
    print("ERR:")
    print(err)

ssh.close()
print("Phase 5 Deployment Successful!")
