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

cmd = "systemctl is-active cco && systemctl is-active nginx && curl -s http://localhost/login | head -n 10"
stdin, stdout, stderr = ssh.exec_command(cmd)

print("OUT:", stdout.read().decode(errors="replace"))
err = stderr.read().decode(errors="replace")
if err: print("ERR:", err)

ssh.close()
