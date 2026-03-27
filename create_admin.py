from app import app, db
from model import User

with app.app_context():
    db.create_all()  # Ensure tables are created

    admin = User(first_name="Admin", last_name="User", email="admin@admin.com")
    admin.set_password("adminpassword")  # Set a secure password

    db.session.add(admin)
    db.session.commit()
    print("Admin user created!")