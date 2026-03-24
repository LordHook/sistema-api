import traceback

try:
    from app import create_app
    from app.models.user import User

    app = create_app()
    with app.test_client() as client:
        with app.app_context():
            user = User.query.first()
        
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
        
        response = client.get('/api/attendance/grid?year=2026&month=3')
        print("Status code:", response.status_code)
        if response.status_code != 200:
            print("Response:", response.data.decode('utf-8'))
except Exception as e:
    traceback.print_exc()
