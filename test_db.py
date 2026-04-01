
from app import create_app
from app.models.worker import Worker
app = create_app()
with app.app_context():
    workers = Worker.query.order_by(Worker.order_number).limit(6).all()
    for w in workers:
        print(f"ID:{w.id}, ONum:{w.order_number}, Name:{w.full_name}, Status: '{w.status}', Resign: '{w.resignation_date}'")
