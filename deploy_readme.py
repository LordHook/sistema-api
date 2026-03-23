import paramiko
import sys
import os

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

local_file = 'deployment.zip'
remote_file = '/opt/deployment.zip' # Put zip outside /opt/cco to avoid chown issues
extract_dir = '/opt/cco'

def ssh_interactive_handler(title, instructions, prompt_list):
    return [password for _ in prompt_list]

print("Connecting to SSH with keyboard-interactive fallback...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(host, port, user, password, timeout=10)
    print("Connected.")
except paramiko.ssh_exception.AuthenticationException:
    t = paramiko.Transport((host, port))
    t.connect()
    t.auth_interactive(user, ssh_interactive_handler)
    ssh._transport = t
    print("Connected via interactive.")

print("Uploading deployment archive...")
sftp = ssh.open_sftp()
sftp.put(local_file, remote_file)
sftp.close()

# The mega bash script implementing the README
bash_script = f"""#!/bin/bash
set -e

echo "=== 1. Stopping Old Services ==="
systemctl stop cco || true
systemctl stop nginx || true
pkill -f gunicorn || true
pkill -f run.py || true

echo "=== 2. System Dependencies ==="
dnf install -y python3.12 python3.12-pip python3.12-devel postgresql-server postgresql-devel gcc nginx unzip policycoreutils-python-utils

echo "=== 3. PostgreSQL Configuration ==="
postgresql-setup --initdb || true
systemctl enable --now postgresql

# The database specified in README
su - postgres -c "psql -c \\"CREATE USER cco_user WITH PASSWORD 'password';\\"" || true
su - postgres -c "psql -c \\"CREATE DATABASE cco_db OWNER cco_user;\\"" || true
su - postgres -c "psql -c \\"ALTER USER cco_user CREATEDB;\\"" || true

# Apply our pg_hba fix just in case it was reverted
PG_HBA="/var/lib/pgsql/data/pg_hba.conf"
if [ -f "$PG_HBA" ]; then
    echo "local   all             all                                     trust" > $PG_HBA
    echo "host    all             all             127.0.0.1/32            md5" >> $PG_HBA
    echo "host    all             all             ::1/128                 md5" >> $PG_HBA
    echo "host    all             all             0.0.0.0/0               md5" >> $PG_HBA
    systemctl restart postgresql
fi

echo "=== 4. OS User Configuration ==="
id -u cco &>/dev/null || useradd -m cco -s /bin/bash

echo "=== 5. App Extraction and Setup ==="
rm -rf {extract_dir}
mkdir -p {extract_dir}
cd {extract_dir}
unzip -q {remote_file}

echo "FLASK_ENV=production" > .env
echo "DATABASE_URL=postgresql://cco_user:password@localhost:5432/cco_db" >> .env
echo "SECRET_KEY=CCO-PROD-KEY-2026-FINAL" >> .env

echo "=== 6. Python Environment ==="
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt psycopg2-binary gunicorn

# Migrations and seeding MUST be run now while root but with venv
export $(grep -v '^#' .env | xargs)
echo "Running Migrations..."
python3 -c "import sys; sys.path.append('/opt/cco'); from app import create_app; from app.extensions import db; from sqlalchemy import text; app = create_app(); ctx = app.app_context(); ctx.push(); db.create_all(); db.session.execute(text('ALTER TABLE workers ADD COLUMN IF NOT EXISTS start_date DATE;')); db.session.execute(text('ALTER TABLE workers ADD COLUMN IF NOT EXISTS allowed_shifts VARCHAR(20) DEFAULT \\'M,T,N\\';')); db.session.execute(text('ALTER TABLE workers ADD COLUMN IF NOT EXISTS resignation_date DATE;')); db.session.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS assigned_group INTEGER;')); db.session.commit()" || true

echo "Seeding Database..."
python3 seed_phase6.py
python3 manage_users.py

# Fix permissions
chown -R cco:cco {extract_dir}

echo "=== 7. Systemd Service (cco.service) ==="
cat << 'EOF2' > /etc/systemd/system/cco.service
[Unit]
Description=CCO Flask App
After=network.target postgresql.service

[Service]
User=cco
WorkingDirectory=/opt/cco
Environment="PATH=/opt/cco/.venv/bin"
ExecStart=/opt/cco/.venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 run:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF2

systemctl daemon-reload
systemctl enable --now cco

echo "=== 8. Nginx Configuration ==="
# Remove default nginx binding if necessary to prevent port 80 conflicts
rm -f /etc/nginx/conf.d/default.conf

cat << 'EOF3' > /etc/nginx/conf.d/cco.conf
server {{
    listen 80;
    server_name _; 

    location / {{
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}

    location /static/ {{
        alias /opt/cco/app/static/;
    }}
}}
EOF3

# Fix SELinux allows Nginx to proxy
setsebool -P httpd_can_network_connect 1 || true

systemctl enable --now nginx
systemctl restart nginx

echo "=== ALIGNMENT COMPLETE ==="
"""

print("Executing master deployment script on remote...")
stdin, stdout, stderr = ssh.exec_command(f"cat << 'MASTEREOF' > /root/deploy.sh\n{bash_script}\nMASTEREOF\nbash /root/deploy.sh")

print(stdout.read().decode(errors='replace'))
err = stderr.read().decode(errors='replace')
if err:
    print(f"Error: {err}")

ssh.close()
print("README Alignment Script Completed.")
