import paramiko
import sys

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

def ssh_interactive_handler(title, instructions, prompt_list):
    return [password for _ in prompt_list]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(host, port, user, password, timeout=10)
except paramiko.ssh_exception.AuthenticationException:
    t = paramiko.Transport((host, port))
    t.connect()
    t.auth_interactive(user, ssh_interactive_handler)
    ssh._transport = t

# Set all local connections to md5
command = """
PG_HBA=$(find /var/lib/pgsql -name pg_hba.conf | head -n 1)
if [ -n "$PG_HBA" ]; then
    echo "Found pg_hba.conf at $PG_HBA"
    # Backup
    cp "$PG_HBA" "${PG_HBA}.bak2"
    
    # Replace ident/peer with md5 for local, 127.0.0.1, and ::1
    sed -i '/^local/s/peer/trust/g' "$PG_HBA"
    sed -i '/^local/s/ident/trust/g' "$PG_HBA"
    sed -i '/^host.*127.0.0.1/s/ident/md5/g' "$PG_HBA"
    sed -i '/^host.*::1/s/ident/md5/g' "$PG_HBA"
    
    # Also just in case, catch any other ident
    sed -i 's/ident/md5/g' "$PG_HBA"
    
    systemctl restart postgresql
    echo "Postgres restarted with md5/trust authentication."
    echo "Current pg_hba.conf (filtered):"
    grep -v '^#' "$PG_HBA" | grep -v '^$'
else
    echo "pg_hba.conf not found."
fi
"""

stdin, stdout, stderr = ssh.exec_command(command)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print(f"Error: {err}")

ssh.close()
