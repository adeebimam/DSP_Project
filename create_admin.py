from app import app, db
from model import User

with app.app_context():
    db.create_all()  # Ensure tables are created

    # Check if admin already exists
    existing = User.query.filter_by(email="admin@admin.com").first()
    if existing:
        print("Admin user already exists!")
    else:
        admin = User(
            first_name="Admin",
            last_name="User",
            email="admin@admin.com",
            is_admin=True
        )
        admin.set_password("adminpassword")  # Change this to a secure password

        db.session.add(admin)
        db.session.commit()
        print("✅ Admin user created with is_admin=True!")