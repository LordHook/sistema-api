import paramiko

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, user, password, timeout=10)

cmd = "md5sum /opt/cco/app/templates/schedule.html /opt/cco/app/static/js/schedule.js"
stdin, stdout, stderr = ssh.exec_command(cmd)
print("REMOTE:")
print(stdout.read().decode('utf-8', 'replace'))
ssh.close()
