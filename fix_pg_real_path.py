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

# Correct path for RHEL 10 default Postgres: /var/lib/pgsql/data/pg_hba.conf
command = """
PG_HBA="/var/lib/pgsql/data/pg_hba.conf"
if [ -f "$PG_HBA" ]; then
    echo "Found pg_hba.conf at $PG_HBA"
    cp "$PG_HBA" "${PG_HBA}.bak_final"
    sed -i 's/ident/trust/g' "$PG_HBA"
    sed -i 's/peer/trust/g' "$PG_HBA"
    systemctl restart postgresql
    echo "Postgres restarted with trust authentication."
else
    echo "$PG_HBA not found. Trying search..."
    PG_HBA=$(find /var/lib/pgsql -name pg_hba.conf | head -n 1)
    if [ -n "$PG_HBA" ]; then
        sed -i 's/ident/trust/g' "$PG_HBA"
        sed -i 's/peer/trust/g' "$PG_HBA"
        systemctl restart postgresql
        echo "Found at $PG_HBA and updated."
    fi
fi
"""

stdin, stdout, stderr = ssh.exec_command(command)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print(f"Error: {err}")

ssh.close()
