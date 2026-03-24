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
    out = stdout.read().decode().strip()
    return out

print("=== NGINX CONFIG ===")
print(run_cmd(ssh, "cat /etc/nginx/nginx.conf | grep -A 20 server {"))
print("--- Conf.d ---")
print(run_cmd(ssh, "cat /etc/nginx/conf.d/*.conf 2>/dev/null"))

print("\n=== SYSTEMD CCO SERVICE ===")
print(run_cmd(ssh, "cat /etc/systemd/system/cco.service 2>/dev/null"))
print(run_cmd(ssh, "cat /lib/systemd/system/cco.service 2>/dev/null"))

ssh.close()
