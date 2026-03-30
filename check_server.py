import paramiko
import os
import sys

# Credenciales del servidor
HOST = "172.16.10.70"
PORT = 22
USER = "root"
PASSWORD = "soporte12#$"

def run_ssh_command(ssh, command):
    print(f"Executing: {command}")
    stdin, stdout, stderr = ssh.exec_command(command)
    out = stdout.read().decode('utf-8').strip()
    err = stderr.read().decode('utf-8').strip()
    if out:
        print(f"OUT:\n{out}")
    if err:
        print(f"ERR:\n{err}")
    return out

def verify_deploy():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, port=PORT, username=USER, password=PASSWORD)
        
        # Check running process
        print("Checking running processes on port 5000:")
        run_ssh_command(ssh, "netstat -tulpn | grep :5000")
        
        # Restart process cleanly
        print("Killing old processes")
        run_ssh_command(ssh, "pkill -f 'python3 run.py' || true")
        run_ssh_command(ssh, "pkill -f 'gunicorn' || true")
        run_ssh_command(ssh, "kill -9 $(lsof -t -i:5000) || true")
        
        # Git pull again just to be sure
        run_ssh_command(ssh, "cd /api && git reset --hard HEAD && git pull origin main")
        
        # Sync to /opt/cco (delete existing app folder first)
        run_ssh_command(ssh, "rm -rf /opt/cco/app")
        run_ssh_command(ssh, "\\cp -r /api/app /opt/cco/")
        run_ssh_command(ssh, "\\cp -r /api/run.py /opt/cco/run.py")
        run_ssh_command(ssh, "\\cp -r /api/requirements.txt /opt/cco/requirements.txt")
        run_ssh_command(ssh, "\\cp -r /api/db_cleanup.py /opt/cco/")
        
        # Check if schedule.py was synced
        run_ssh_command(ssh, "grep 'Domingo Doble' /opt/cco/app/routes/schedule.py || grep 'target_date.weekday() == 6' /opt/cco/app/routes/schedule.py")
        
        # Restart service
        run_ssh_command(ssh, "cd /opt/cco && nohup python3 run.py --host=0.0.0.0 --port=5000 > /dev/null 2>&1 &")
        
        import time
        time.sleep(3)
        print("Service status after restart:")
        run_ssh_command(ssh, "netstat -tulpn | grep :5000")

    except Exception as e:
        print(f"SSH Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    verify_deploy()
