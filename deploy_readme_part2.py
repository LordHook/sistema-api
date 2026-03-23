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

bash_script = """#!/bin/bash
set -e

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
rm -f /etc/nginx/conf.d/default.conf

cat << 'EOF3' > /etc/nginx/conf.d/cco.conf
server {
    listen 80;
    server_name _; 

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \\$host;
        proxy_set_header X-Real-IP \\$remote_addr;
    }

    location /static/ {
        alias /opt/cco/app/static/;
    }
}
EOF3

setsebool -P httpd_can_network_connect 1 || true

systemctl enable --now nginx
systemctl restart nginx

echo "=== ALIGNMENT COMPLETE ==="
"""

stdin, stdout, stderr = ssh.exec_command(f"cat << 'MASTEREOF' > /root/deploy_part2.sh\n{bash_script}\nMASTEREOF\nbash /root/deploy_part2.sh")

print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print(f"Error: {err}")

ssh.close()
