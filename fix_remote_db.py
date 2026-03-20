import paramiko

def fix_remote():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('172.16.10.70', 22, 'root', 'soporte12#$')
    
    print("Executing ALTER TABLE workers ADD COLUMN allowed_shifts...")
    stdin, stdout, stderr = ssh.exec_command('su - postgres -c "psql -d cemovi_db -c \\"ALTER TABLE workers ADD COLUMN IF NOT EXISTS allowed_shifts VARCHAR(20) DEFAULT \'M,T,N\';\\""')
    print("OUT:", stdout.read().decode())
    print("ERR:", stderr.read().decode())

    print("Executing ALTER TABLE workers ADD COLUMN resignation_date...")
    stdin, stdout, stderr = ssh.exec_command('su - postgres -c "psql -d cemovi_db -c \\"ALTER TABLE workers ADD COLUMN IF NOT EXISTS resignation_date DATE;\\""')
    print("OUT:", stdout.read().decode())
    print("ERR:", stderr.read().decode())

    print("Running seed_phase6.py...")
    stdin, stdout, stderr = ssh.exec_command('cd /opt/cco && source .venv/bin/activate && export $(grep -v \'^#\' .env | xargs) && python3 seed_phase6.py')
    print("OUT:", stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print("ERR:", err)

    print("Restarting app...")
    ssh.exec_command('pkill -f run.py || true')
    ssh.exec_command('cd /opt/cco && source .venv/bin/activate && export $(grep -v \'^#\' .env | xargs) && nohup python3 run.py --host=0.0.0.0 --port=5000 > app.log 2>&1 &')
    print("Done")

if __name__ == '__main__':
    fix_remote()
