from app import create_app
from app.routes.attendance import get_attendance_grid
from app.models.user import User

app = create_app()

with app.app_context():
    try:
        # Mock current_user
        class MockUser:
            def __init__(self, role, assigned_group, is_admin):
                self.role = role
                self.assigned_group = assigned_group
                self.is_admin = is_admin
        
        # We have to patch current_user
        from unittest.mock import patch
        with patch('app.routes.attendance.current_user', MockUser('admin', None, True)):
            # Mock request
            with app.test_request_context('/api/attendance/grid?year=2026&month=3'):
                res = get_attendance_grid()
                print("Grid OK.")
    except Exception as e:
        import traceback
        traceback.print_exc()
