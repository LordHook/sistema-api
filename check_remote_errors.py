import paramiko

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, user, password, timeout=10)

cmd = """
echo "=== NGINX 500 ERRORS ==="
grep " 500 " /var/log/nginx/access.log | tail -n 10

echo "=== GUNICORN ERRORS ==="
journalctl -u cco --no-pager | grep -i "error" | tail -n 10

echo "=== APP.LOG ERRORS ==="
cat /opt/cco/app.log | grep -i "error" | tail -n 10
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("OUT:", stdout.read().decode('utf-8', 'replace'))
ssh.close()
