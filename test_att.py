from app import create_app
from app.extensions import db
from app.models.attendance import AttendanceRecord
from sqlalchemy import extract

app = create_app()

with app.app_context():
    try:
        year = 2026
        month = 3
        records = AttendanceRecord.query.filter(
            extract('year', AttendanceRecord.attendance_date) == year,
            extract('month', AttendanceRecord.attendance_date) == month
        ).all()
        print("Queries OK. Records:", len(records))
    except Exception as e:
        import traceback
        traceback.print_exc()
