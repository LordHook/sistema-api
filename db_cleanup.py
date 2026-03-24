import sys
import os

from app import create_app
from app.extensions import db
from app.models.worker import Worker
from app.models.schedule import ScheduleEntry
from app.models.attendance import AttendanceRecord

app = create_app()

def clean_duplicates():
    with app.app_context():
        # Find workers: VASQUEZ ESTRELLA and GUERRERO VALLEJO
        targets = ['VASQUEZ ESTRELLA', 'GUERRERO VALLEJO']
        
        for t in targets:
            workers = Worker.query.filter(Worker.last_name.ilike(f'%{t}%')).order_by(Worker.id).all()
            print(f"Found {len(workers)} records for {t}: {[w.id for w in workers]}")
            
            if len(workers) > 1:
                # Keep the first one, delete the rest
                keep_worker = workers[0]
                delete_workers = workers[1:]
                
                print(f"Keeping ID {keep_worker.id}, deleting {[(w.id, w.full_name) for w in delete_workers]}")
                
                # Make sure the kept one is active and in section D (or TD initially, we map dynamically but let's set it to TD in DB just in case)
                keep_worker.section = 'TD'
                db.session.add(keep_worker)

                for w in delete_workers:
                    # Optional: Reassign schedule entries to the keep_worker if needed, or simply delete them
                    # Since it's a cleanup, we probably want to delete or reassign. Let's delete the duplicate's schedules
                    ScheduleEntry.query.filter_by(worker_id=w.id).delete()
                    AttendanceRecord.query.filter_by(worker_id=w.id).delete()
                    
                    db.session.delete(w)
                    
        db.session.commit()
        print("Cleanup applied.")

if __name__ == '__main__':
    clean_duplicates()
