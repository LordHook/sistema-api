import paramiko
import sys
import os

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

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

print("Ensuring remote directory exists...")
ssh.exec_command(f"mkdir -p {extract_dir}")

print("Opening SFTP...")
sftp = ssh.open_sftp()
print("Uploading...")
sftp.put(local_file, remote_file)
sftp.close()

bash_script = f"""#!/bin/bash
cd {extract_dir}
unzip -o {remote_file}

# Setup Postgres
dnf install -y postgresql-server postgresql-contrib || true
postgresql-setup --initdb || true
systemctl enable --now postgresql

su - postgres -c "psql -c \\"CREATE USER cemovi_user WITH PASSWORD 'password';\\"" || true
su - postgres -c "psql -c \\"CREATE DATABASE cemovi_db OWNER cemovi_user;\\"" || true
su - postgres -c "psql -c \\"ALTER USER cemovi_user CREATEDB;\\"" || true

# Setup environment
echo 'FLASK_ENV=production' > .env
echo 'DATABASE_URL=postgresql://cemovi_user:password@localhost:5432/cemovi_db' >> .env
echo 'SECRET_KEY=CCO-PROD-KEY-2026' >> .env

# Setup python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt psycopg2-binary

# Run Migrations
export $(grep -v '^#' .env | xargs)
python3 -c "import sys; sys.path.append('/opt/cco'); from app import create_app; from app.extensions import db; from sqlalchemy import text; app = create_app(); ctx = app.app_context(); ctx.push(); db.create_all(); db.session.execute(text('ALTER TABLE workers ADD COLUMN IF NOT EXISTS start_date DATE;')); db.session.execute(text('ALTER TABLE workers ADD COLUMN IF NOT EXISTS allowed_shifts VARCHAR(20) DEFAULT \\'M,T,N\\';')); db.session.execute(text('ALTER TABLE workers ADD COLUMN IF NOT EXISTS resignation_date DATE;')); db.session.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS assigned_group INTEGER;')); db.session.commit()" || true

python3 seed_phase6.py

# Run App
pkill -f run.py || true
nohup python3 run.py --host=0.0.0.0 --port=5000 > app.log 2>&1 &
"""

print("Executing bash script on remote...")
stdin, stdout, stderr = ssh.exec_command(f"cat << 'EOF' > {extract_dir}/deploy.sh\n{bash_script}\nEOF\nbash {extract_dir}/deploy.sh")

print(stdout.read().decode(errors='replace'))
err = stderr.read().decode(errors='replace')
if err:
    print(f"Error: {err}")

ssh.close()
print("Deployment Configuration Complete!")
