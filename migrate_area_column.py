import sys
import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from sqlalchemy import text

def migrate_area():
    app = create_app()
    with app.app_context():
        try:
            db.session.execute(text("ALTER TABLE monthly_worker_status ADD COLUMN area VARCHAR(50);"))
            db.session.commit()
            print("Column 'area' added to monthly_worker_status successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding column (maybe it already exists?): {e}")

if __name__ == '__main__':
    migrate_area()
