import paramiko

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, user, password, timeout=10)

def exec_cmd(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode('ascii', 'ignore').strip()

print("Checking API dir:")
print(exec_cmd("grep 'id=\"view-resignations\"' /api/app/templates/personnel.html"))

print("Checking OPT dir:")
print(exec_cmd("grep 'id=\"view-resignations\"' /opt/cco/app/templates/personnel.html"))

ssh.close()
