import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, user, password, timeout=10)

def run_cmd(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    return exit_status, out, err

cmd_fix = """
echo "=== RE-ALINEANDO DESPLIEGUE CON NGINX ==="
# Matamos los procesos de nohup que estaban en /api
pkill -9 -f "python3 run.py" || true

cd /opt/cco
echo "Sincronizando /opt/cco (Directorio maestro de Nginx y Systemd)..."
git fetch origin main
git reset --hard origin/main
git clean -fd

echo "Reiniciando CCO Service nativo..."
systemctl daemon-reload
systemctl restart cco
systemctl status cco --no-pager | head -n 10
"""

_, out, err = run_cmd(ssh, cmd_fix)
print("OUT:\n", out)
if err: print("ERR:\n", err)

ssh.close()
print("RHEL 10 Nginx Alignment Successful.")
