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

def exec_cmd(cmd):
    print(f"Executing: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', 'replace')
    err = stderr.read().decode('utf-8', 'replace')
    if out: print("OUT:", out)
    if err: print("ERR:", err)
    return out

print("--- 1. Diagnostico de Ruta y Git ---")
exec_cmd("cd /opt/cco && git pull origin main && git log -1")

print("--- 2. Destruccion de Procesos Fantasma ---")
out = exec_cmd("netstat -tulpn | grep :5000")
# Parse PID out of netstat
lines = out.strip().split('\n')
pids_killed = []
for line in lines:
    if ':5000' in line and 'LISTEN' in line:
        parts = line.split()
        # the PID/Program name is usually the last part
        pid_prog = parts[-1]
        pid = pid_prog.split('/')[0]
        if pid.isdigit() and pid not in pids_killed:
            print(f"Killing PID {pid}")
            exec_cmd(f"kill -9 {pid}")
            pids_killed.append(pid)

if not pids_killed:
    # try python process just in case
    print("No PID found in netstat, checking pgrep")
    exec_cmd("pkill -9 -f 'python3 run.py'")

print("--- 3. Despliegue en Limpio ---")
# Give it a second
time.sleep(2)
exec_cmd("cd /opt/cco && nohup python3 run.py --host=0.0.0.0 --port=5000 > /dev/null 2>&1 &")

time.sleep(3)
exec_cmd("netstat -tulpn | grep :5000")

ssh.close()
print("Done Phase 2")
