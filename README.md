# CEMOVI - Sistema de Gestión de Horarios y Control de Asistencia

Sistema web para generar roles de servicio mensuales y controlar la asistencia diaria del Centro de Monitoreo y Videovigilancia.

## Stack Tecnológico

- **Backend**: Python 3.12 + Flask 3.x
- **Base de Datos**: PostgreSQL 16 (producción) / SQLite (desarrollo)
- **ORM**: SQLAlchemy 2.x + Flask-Migrate
- **Frontend**: HTML5 + Vanilla JS + CSS
- **Gráficos**: Chart.js
- **Exportación**: openpyxl (Excel) + ReportLab (PDF)

## Instalación Local (Windows - Desarrollo)

```bash
cd c:\Users\Administrador\Documents\APi
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Abrir en el navegador: `http://localhost:5000`

**Credenciales por defecto:**
- Usuario: `admin`
- Contraseña: `admin123`

## Despliegue en RHEL 10 (Producción)

### 1. Instalar dependencias del sistema
```bash
sudo dnf install python3.12 python3.12-pip python3.12-devel postgresql-server postgresql-devel gcc nginx
```

### 2. Configurar PostgreSQL 16
```bash
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql
sudo -u postgres createuser cemovi_user -P
sudo -u postgres createdb cemovi_db -O cemovi_user
```

### 3. Configurar la aplicación
```bash
cd /opt/cemovi
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Crear .env desde template
cp .env.example .env
# Editar .env con las credenciales de PostgreSQL
```

### 4. Configurar Gunicorn como servicio
Crear `/etc/systemd/system/cemovi.service`:
```ini
[Unit]
Description=CEMOVI Flask App
After=network.target postgresql.service

[Service]
User=cemovi
WorkingDirectory=/opt/cemovi
ExecStart=/opt/cemovi/.venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now cemovi
```

### 5. Configurar Nginx
```nginx
server {
    listen 80;
    server_name cemovi.tudominio.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /opt/cemovi/app/static/;
    }
}
```

## Estructura del Proyecto

```
APi/
├── app/
│   ├── __init__.py          # App factory
│   ├── config.py            # Configuración
│   ├── extensions.py        # Flask extensions
│   ├── models/              # Modelos de BD
│   ├── routes/              # API endpoints
│   ├── services/            # Lógica de negocio
│   ├── static/              # CSS, JS, imágenes
│   └── templates/           # HTML templates
├── requirements.txt
├── run.py
└── README.md
```
