import paramiko

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, user, password, timeout=10)

cmd = """
curl -s -c cookie.txt -d "username=admin&password=admin123" http://localhost/login > /dev/null
curl -s -b cookie.txt http://localhost/schedule > schedule_out.html
cat schedule_out.html | grep -i "Modo Pincel" -A 10
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print("OUT:", stdout.read().decode('utf-8', 'replace'))
ssh.close()
