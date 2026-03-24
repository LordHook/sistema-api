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

print("--- Check deployment path ---")
exec_cmd("ls -la /api/.git || echo 'no git in /api'")
exec_cmd("ls -la /opt/cco/.git || echo 'no git in /opt/cco'")

print("--- Trying to pull in /api ---")
exec_cmd("cd /api && git pull origin main && git log -1")

ssh.close()
print("Done")
