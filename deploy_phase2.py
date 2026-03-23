import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

print("Connecting to RHEL 10...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, user, password, timeout=10)

print("Uploading Codebase...")
sftp = ssh.open_sftp()
sftp.put('deployment.zip', '/opt/deployment.zip')
sftp.close()

# Provide the python code to delete schedules remotely using their codebase
cmd = """
echo "Extracting codebase..."
systemctl stop cco
cd /opt/cco
unzip -o -q /opt/deployment.zip

# Make sure python environment works
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
python3 -c "print('Actualizacion de codigo finalizada en produccion.')"

echo "Restarting Service..."
chown -R cco:cco /opt/cco
systemctl start cco
"""

print("Executing Remote Commands...")
stdin, stdout, stderr = ssh.exec_command(cmd)
print("OUT:", stdout.read().decode('utf-8', 'replace'))
err = stderr.read().decode('utf-8', 'replace')
if err: print("ERR:", err)

ssh.close()
print("Phase 2 Deployment Successful!")
