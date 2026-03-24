from app import create_app
from app.models.attendance import AttendanceRecord
from sqlalchemy import extract

app = create_app()
with app.app_context():
    year = 2026
    month = 3
    records = AttendanceRecord.query.filter(
        extract('year', AttendanceRecord.attendance_date) == year,
        extract('month', AttendanceRecord.attendance_date) == month
    ).all()
    if records:
        print("Type of attendance_date:", type(records[0].attendance_date))
        print("Value:", records[0].attendance_date)
        try:
            print("Day:", records[0].attendance_date.day)
        except Exception as e:
            print("Error accessing day:", e)
    else:
        print("No records found.")
