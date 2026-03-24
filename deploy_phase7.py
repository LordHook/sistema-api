import paramiko
import sys
import time

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

print("=== 2. AUDITORIA DE RUTAS ===")
_, out, _ = run_cmd(ssh, "ls -ld /api/.git /opt/cco/.git 2>/dev/null")
print(out)

cmd_pull = """
cd /api || cd /opt/cco
pwd
echo "Forzando sincronización limpia con GitHub..."
git fetch origin main
git reset --hard origin/main
git clean -fd
"""
_, out, err = run_cmd(ssh, cmd_pull)
print("PULL OUT:\n", out)
if err: print("PULL ERR:\n", err)

print("=== 3. REINICIANDO APLICACION ===")
cmd_start = """
cd /api || cd /opt/cco
nohup python3 run.py --host=0.0.0.0 --port=5000 > app.log 2>&1 &
sleep 2
"""
run_cmd(ssh, cmd_start)

# Verify if it's running
_, out, _ = run_cmd(ssh, "netstat -tulpn | grep :5000")
print("NETSTAT:", out)

ssh.close()
print("Audit Successful.")
