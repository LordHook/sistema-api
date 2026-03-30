import sys
import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models.worker import Worker, MonthlyWorkerStatus
from app.models.schedule import ScheduleEntry

def migrate_and_seed():
    app = create_app()
    with app.app_context():
        # Create missing tables
        db.create_all()
        print("Tables created.")
        
        # Seed existing history into MonthlyWorkerStatus
        periods = db.session.query(ScheduleEntry.year, ScheduleEntry.month).distinct().all()
        workers = Worker.query.all()
        
        count = 0
        for y, m in periods:
            for w in workers:
                exists = MonthlyWorkerStatus.query.filter_by(worker_id=w.id, year=y, month=m).first()
                if not exists:
                    snap = MonthlyWorkerStatus(
                        worker_id=w.id, year=y, month=m, 
                        section=w.section, group_number=w.group_number
                    )
                    db.session.add(snap)
                    count += 1
        db.session.commit()
        print(f"Seeded {count} snapshot records safely.")

if __name__ == '__main__':
    migrate_and_seed()
