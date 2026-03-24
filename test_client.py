from app import create_app
from app.models.user import User
from flask_login import login_user

app = create_app()
app.config['TESTING'] = True

with app.test_client() as client:
    with app.app_context():
        # Get first user to login
        user = User.query.first()
    
    # Login the user
    # We can mock the session or just login via test client
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True
    
    # Make request
    response = client.get('/api/attendance/grid?year=2026&month=3')
    print("Status code:", response.status_code)
    if response.status_code == 500:
        print("Response:", response.data.decode('utf-8'))
