import paramiko
import os
import sys

host = '172.16.10.70'
port = 22
user = 'root'
password = 'soporte12#$'

print("Iniciando transferencia SFTP de emergencia hacia el servidor...")

transport = paramiko.Transport((host, port))
transport.connect(username=user, password=password)
sftp = paramiko.SFTPClient.from_transport(transport)

remote_base = '/api'
local_base = os.getcwd()

# Lista de carpetas/archivos clave a subir para la Fase 19
targets = [
    'app/templates/schedule.html',
    'app/static/css/style.css',
    'app/models/schedule.py',
    'app/services/schedule_generator.py',
]

for target in targets:
    local_path = os.path.join(local_base, target)
    remote_path = f"{remote_base}/{target}"
    
    # Check if we need to create remote dirs
    remote_dir = os.path.dirname(remote_path)
    try:
        sftp.stat(remote_dir)
    except IOError:
        # Create dir (simple 1-level for this case, or ignore if we know /api/app/ routes exist)
        pass

    try:
        sftp.put(local_path, remote_path)
        print(f"Subido exitosamente: {target}")
    except Exception as e:
        print(f"Error subiendo {target}: {e}")

sftp.close()
transport.close()
print("SFTP Finalizado.")
