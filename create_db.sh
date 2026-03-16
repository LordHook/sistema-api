cd /api
python3 -c "
import sys, os
from dotenv import load_dotenv
load_dotenv('/api/.env')
os.environ['SQLALCHEMY_DATABASE_URI'] = 'postgresql://cco_admin:Cco2026!@127.0.0.1:5432/cco_db'
import app
from app import create_app, db
application = create_app()
with application.app_context():
    db.create_all()
    print('Tables ready')
"
fuser -k 5000/tcp || true
nohup python3 run.py --host=0.0.0.0 --port=5000 > app.log 2>&1 &
echo "Deployment Finished Successfully!"
