import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, user, password, timeout=10)

cmd = """
# Drop connections to cco_db
su - postgres -c "psql -c \\"SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = 'cco_db' AND pid <> pg_backend_pid();\\""

# Drop and recreate the database correctly
su - postgres -c "psql -c \\"DROP DATABASE IF EXISTS cco_db;\\""
su - postgres -c "psql -c \\"CREATE DATABASE cco_db OWNER cco_user;\\""

echo "=== Rerunning Setup ==="
cd /opt/cco
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)

# Create tables
python3 -c "import sys; sys.path.append('/opt/cco'); from app import create_app; from app.extensions import db; from sqlalchemy import text; app = create_app(); ctx = app.app_context(); ctx.push(); db.create_all(); db.session.execute(text('ALTER TABLE workers ADD COLUMN IF NOT EXISTS start_date DATE;')); db.session.execute(text('ALTER TABLE workers ADD COLUMN IF NOT EXISTS allowed_shifts VARCHAR(20) DEFAULT \\'M,T,N\\';')); db.session.execute(text('ALTER TABLE workers ADD COLUMN IF NOT EXISTS resignation_date DATE;')); db.session.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS assigned_group INTEGER;')); db.session.commit()"

# Seed database
python3 seed_phase6.py
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("OUT:", stdout.read().decode('utf-8', 'replace'))
err = stderr.read().decode('utf-8', 'replace')
if err: print("ERR:", err)

ssh.close()
