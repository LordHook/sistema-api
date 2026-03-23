from app import create_app
from app.extensions import db
from app.models.schedule import ScheduleEntry

app = create_app()

with app.app_context():
    count = ScheduleEntry.query.count()
    if count > 0:
        ScheduleEntry.query.delete()
        db.session.commit()
        print(f"Borrados {count} registros de horarios.")
    else:
        print("La base de datos de horarios ya está vacía.")
