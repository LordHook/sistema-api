from app import create_app
from app.models.attendance import AttendanceRecord

app = create_app()
with app.app_context():
    all_records = AttendanceRecord.query.all()
    failed = 0
    for r in all_records:
        try:
            d = r.attendance_date.day
        except Exception as e:
            print(f"Record {r.id} has invalid date type: {type(r.attendance_date)} - {r.attendance_date}")
            failed += 1
    print(f"Total checked: {len(all_records)}. Failed: {failed}")
