import paramiko
import sys
import time
import re

sys.stdout.reconfigure(encoding='utf-8')

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, user, password, timeout=10)

def exec_cmd(cmd):
    print(f"Executing: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', 'replace').strip()
    err = stderr.read().decode('utf-8', 'replace').strip()
    if out: print("OUT:", out)
    if err: print("ERR:", err)
    return out

print("--- 1. Commit and Pull en Repositorio Git ---")
# exec_cmd("cd /api && git pull origin main && git log -1")
print("Bypassed Git pull. Using SFTP modified files in /api directly.")

print("--- 2. Autodescubrimiento del Directorio de Produccion ---")
out = exec_cmd("netstat -tulpn | grep :5000")

pids = []
for line in out.split('\\n'):
    if ':5000' in line and 'LISTEN' in line:
        parts = line.split()
        pid_prog = parts[-1]
        pid = pid_prog.split('/')[0]
        if pid.isdigit() and pid not in pids:
            pids.append(pid)

app_dir = "/opt/cco" # fallback
if pids:
    first_pid = pids[0]
    print(f"Puerto 5000 ocupado por PID {first_pid}. Identificando entorno...")
    pwdx_out = exec_cmd(f"pwdx {first_pid}")
    if pwdx_out and ":" in pwdx_out:
        app_dir = pwdx_out.split(':')[1].strip()
        print(f"Autodescubrimiento exitoso: Aplicacion viva corriendo en {app_dir}")
else:
    print("No hay procesos en puerto 5000. Usando ruta por defecto: /opt/cco")

print(f"--- 3. Sincronizacion Codigo hacia {app_dir} ---")
exec_cmd(f"rm -rf {app_dir}/app")
exec_cmd(f"\\cp -r /api/* {app_dir}/")

print("--- 4. Destruccion de Procesos Zombies en puerto 5000 ---")
for pid in pids:
    print(f"Destruyendo con kill -9 PID {pid}")
    exec_cmd(f"kill -9 {pid}")

# Wait a second to free port
time.sleep(2)

print(f"--- 5. Reinicio Seguro de la App en {app_dir} ---")
# Install reqs just in case
exec_cmd(f"cd {app_dir} && source .venv/bin/activate && pip install -r requirements.txt || true")
# Exec database cleanup on Production Postgres
exec_cmd(f"cd {app_dir} && source .venv/bin/activate && python3 clean_duplicates.py")
# Exec database missing tables and historical seeding
exec_cmd(f"cd {app_dir} && source .venv/bin/activate && python3 migrate_and_seed.py")
# Star background process
exec_cmd(f"cd {app_dir} && nohup python3 run.py --host=0.0.0.0 --port=5000 > /dev/null 2>&1 &")

time.sleep(3)
exec_cmd("netstat -tulpn | grep :5000")

ssh.close()
print("Despliegue Dinamico Exitoso!")
