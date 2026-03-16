from app import create_app
from app.extensions import db
from app.models.user import User
from sqlalchemy import text

app = create_app()

def migrate_and_seed():
    with app.app_context():
        # 1. Alter Tables (PostgreSQL style assumed, catch error if already exists)
        try:
            db.session.execute(text("ALTER TABLE workers ADD COLUMN start_date DATE;"))
            print("Added start_date to workers table.")
        except Exception as e:
            db.session.rollback()
            print("Column start_date might already exist.")

        try:
            db.session.execute(text("ALTER TABLE users ADD COLUMN assigned_group INTEGER;"))
            print("Added assigned_group to users table.")
        except Exception as e:
            db.session.rollback()
            print("Column assigned_group might already exist.")

        db.session.commit()

        # 2. Seed Supervisors
        supervisors_data = [
            {'username': 'sup_ormeno', 'password': '123', 'full_name': 'ORMEÑO MENDOZA, WILLY ALBERTO', 'group': 1},
            {'username': 'sup_inape', 'password': '123', 'full_name': 'IÑAPE HIDALGO ARTURO', 'group': 2},
            {'username': 'sup_bellido', 'password': '123', 'full_name': 'BELLIDO TOLEDO, JORGE ADALBERTO', 'group': 3},
        ]

        for s_data in supervisors_data:
            existing = User.query.filter_by(username=s_data['username']).first()
            if not existing:
                u = User(
                    username=s_data['username'],
                    full_name=s_data['full_name'],
                    role='supervisor',
                    assigned_group=s_data['group']
                )
                u.set_password(s_data['password'])
                db.session.add(u)
                print(f"Created Supervisor: {s_data['full_name']} (Group {s_data['group']})")
            else:
                existing.role = 'supervisor'
                existing.assigned_group = s_data['group']
                print(f"Updated Supervisor: {s_data['full_name']} (Group {s_data['group']})")

        db.session.commit()
        print("Done!")

if __name__ == '__main__':
    migrate_and_seed()
