import paramiko
import sys

host = '172.16.10.70'
port = 22
user = 'root'
password = 'Admin123$'

local_file = 'deployment.zip'
remote_file = '/opt/cco/deployment.zip'
extract_dir = '/opt/cco'

def ssh_interactive_handler(title, instructions, prompt_list):
    return [password for _ in prompt_list]

print("Connecting to SSH with keyboard-interactive fallback...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    # Try standard password auth
    ssh.connect(host, port, user, password, timeout=10)
    print("Connected via standard password.")
except paramiko.ssh_exception.AuthenticationException:
    print("Standard auth failed, trying keyboard-interactive...")
    try:
        t = paramiko.Transport((host, port))
        t.connect()
        t.auth_interactive(user, ssh_interactive_handler)
        ssh._transport = t
        print("Connected via keyboard-interactive.")
    except Exception as e:
        print(f"Keyboard-interactive also failed: {e}")
        sys.exit(1)
except Exception as e:
    print(f"Connection error: {e}")
    sys.exit(1)

print("Opening SFTP...")
sftp = ssh.open_sftp()
print("Uploading...")
sftp.put(local_file, remote_file)
sftp.close()

print("Unzipping on remote...")
commands = [
    f"cd {extract_dir}",
    f"unzip -o {remote_file}",
    "source .venv/bin/activate || echo 'No venv'",
    "python3 alter_db.py",
    "python3 seed_phase5.py",
    "pkill -f run.py",
    "nohup python3 run.py --host=0.0.0.0 --port=5000 > app.log 2>&1 &"
]

for cmd in commands:
    print(f"Running: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print(f"Error: {err}")

ssh.close()
print("Deployment Complete!")
