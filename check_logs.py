import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('172.16.10.70', 22, 'root', 'soporte12#$', timeout=5)
    stdin, stdout, stderr = ssh.exec_command("tail -n 120 /opt/cco/app.log")
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print("ERRORS:", err)
    ssh.close()
except Exception as e:
    print(f"Connection failed: {e}")
