import paramiko

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, user, password, timeout=10)

sftp = ssh.open_sftp()
sftp.get('/opt/cco/app/routes/schedule.py', 'remote_schedule.py')
sftp.get('/opt/cco/app/models/worker.py', 'remote_worker.py')
sftp.close()
ssh.close()
