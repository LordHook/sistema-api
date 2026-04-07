from app import create_app, db
from app.models.worker import Worker
from datetime import date

app = create_app()
with app.app_context():
    # Encuentra inactivos / deshabilitados sin fecha de cese
    legacy_workers = Worker.query.filter(
        Worker.status.in_(['inactivo', 'deshabilitado']),
        Worker.resignation_date.is_(None)
    ).all()
    
    count = 0
    for w in legacy_workers:
        w.resignation_date = date(2025, 1, 1)  # Default date far in the past to prevent leaking
        count += 1
        
    db.session.commit()
    print(f"Cleanup finished. Updated {count} legacy workers with default resignation dates.")
