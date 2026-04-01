import paramiko
import os
import subprocess

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

print("Starting SFTP upload for modified files...")

# Get list of files from git status
out = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD~1']).decode('utf-8')
targets = [line.strip() for line in out.split('\n') if line.strip() and not line.startswith('.')]

print(f"Files to upload: {targets}")

transport = paramiko.Transport((host, port))
transport.connect(username=user, password=password)
sftp = paramiko.SFTPClient.from_transport(transport)

remote_base = '/api'
local_base = os.getcwd()

for target in targets:
    local_path = os.path.join(local_base, target)
    remote_path = f"{remote_base}/{target}"
    
    # Try to upload if file exists locally
    if not os.path.exists(local_path):
        continue
        
    # Check if we need to create remote dirs
    remote_dir = os.path.dirname(remote_path)
    try:
        sftp.stat(remote_dir)
    except IOError:
        try:
            # We assume the parent structure mostly exists or we don't care about deep nests right now
            sftp.mkdir(remote_dir)
        except:
            pass
            
    try:
        sftp.put(local_path, remote_path)
        print(f"Uploaded successfully: {target}")
    except Exception as e:
        print(f"Error uploading {target}: {e}")

sftp.close()
transport.close()
print("SFTP Transfer complete.")
