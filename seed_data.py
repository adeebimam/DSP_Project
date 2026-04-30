from datetime import datetime
from app import app
from model import db, User, Expense

mock_expenses = [
    # ===== JANUARY =====
    {"amount": 10.50, "category": "Food", "date": "2026-01-03", "note": "Breakfast", "payment_method": "Cash", "merchant": "Greggs"},
    {"amount": 60.00, "category": "Transport", "date": "2026-01-05", "note": "Fuel", "payment_method": "Card", "merchant": "Shell"},
    {"amount": 120.00, "category": "Bills", "date": "2026-01-07", "note": "Electricity bill", "payment_method": "Direct Debit", "merchant": "Octopus Energy"},
    {"amount": 25.00, "category": "Entertainment", "date": "2026-01-10", "note": "Cinema", "payment_method": "Card", "merchant": "Vue Cinema"},
    {"amount": 75.00, "category": "Shopping", "date": "2026-01-12", "note": "Clothes", "payment_method": "Card", "merchant": "Zara"},
    {"amount": 15.99, "category": "Subscriptions", "date": "2026-01-15", "note": "Netflix", "payment_method": "Card", "merchant": "Netflix"},
    {"amount": 9.99, "category": "Subscriptions", "date": "2026-01-15", "note": "Spotify", "payment_method": "Card", "merchant": "Spotify"},

    # ===== FEBRUARY =====
    {"amount": 12.00, "category": "Food", "date": "2026-02-02", "note": "Lunch", "payment_method": "Card", "merchant": "Pret"},
    {"amount": 30.00, "category": "Transport", "date": "2026-02-05", "note": "Taxi", "payment_method": "Card", "merchant": "Uber"},
    {"amount": 95.00, "category": "Bills", "date": "2026-02-07", "note": "Water bill", "payment_method": "Direct Debit", "merchant": "Thames Water"},
    {"amount": 20.00, "category": "Entertainment", "date": "2026-02-10", "note": "Bowling", "payment_method": "Card", "merchant": "Hollywood Bowl"},
    {"amount": 80.00, "category": "Shopping", "date": "2026-02-12", "note": "Jacket", "payment_method": "Card", "merchant": "H&M"},
    {"amount": 10.99, "category": "Subscriptions", "date": "2026-02-15", "note": "Amazon Prime", "payment_method": "Card", "merchant": "Amazon"},

    # ===== MARCH =====
    {"amount": 14.00, "category": "Food", "date": "2026-03-02", "note": "Lunch", "payment_method": "Card", "merchant": "Pret"},
    {"amount": 40.00, "category": "Transport", "date": "2026-03-03", "note": "Fuel", "payment_method": "Card", "merchant": "BP"},
    {"amount": 100.00, "category": "Bills", "date": "2026-03-07", "note": "Internet bill", "payment_method": "Direct Debit", "merchant": "BT"},
    {"amount": 20.00, "category": "Entertainment", "date": "2026-03-10", "note": "Bowling", "payment_method": "Card", "merchant": "Hollywood Bowl"},
    {"amount": 60.00, "category": "Shopping", "date": "2026-03-12", "note": "Clothes", "payment_method": "Card", "merchant": "Uniqlo"},
    {"amount": 150.00, "category": "Travel", "date": "2026-03-15", "note": "Flight booking", "payment_method": "Card", "merchant": "Skyscanner"},
    {"amount": 10.99, "category": "Subscriptions", "date": "2026-03-18", "note": "Amazon Prime", "payment_method": "Card", "merchant": "Amazon"},

    # ===== APRIL (MOST DATA FOR DEMO) =====
    {"amount": 12.50, "category": "Food", "date": "2026-04-01", "note": "Lunch", "payment_method": "Card", "merchant": "Pret"},
    {"amount": 45.00, "category": "Transport", "date": "2026-04-02", "note": "Bus pass", "payment_method": "Card", "merchant": "First Bus"},
    {"amount": 89.99, "category": "Shopping", "date": "2026-04-03", "note": "T-shirt", "payment_method": "Card", "merchant": "Nike"},
    {"amount": 6.80, "category": "Food", "date": "2026-04-03", "note": "Coffee", "payment_method": "Apple Pay", "merchant": "Starbucks"},
    {"amount": 120.00, "category": "Bills", "date": "2026-04-05", "note": "Electricity", "payment_method": "Direct Debit", "merchant": "Octopus Energy"},
    {"amount": 15.99, "category": "Subscriptions", "date": "2026-04-06", "note": "Netflix", "payment_method": "Card", "merchant": "Netflix"},
    {"amount": 9.99, "category": "Subscriptions", "date": "2026-04-06", "note": "Spotify", "payment_method": "Card", "merchant": "Spotify"},
    {"amount": 25.00, "category": "Entertainment", "date": "2026-04-07", "note": "Cinema", "payment_method": "Apple Pay", "merchant": "Vue Cinema"},
    {"amount": 200.00, "category": "Travel", "date": "2026-04-08", "note": "Train", "payment_method": "Card", "merchant": "Trainline"},
    {"amount": 18.40, "category": "Food", "date": "2026-04-09", "note": "Dinner", "payment_method": "Card", "merchant": "Nando's"},
    {"amount": 70.00, "category": "Shopping", "date": "2026-04-10", "note": "Shoes", "payment_method": "Card", "merchant": "JD Sports"},
    {"amount": 30.00, "category": "Healthcare", "date": "2026-04-11", "note": "Pharmacy", "payment_method": "Cash", "merchant": "Boots"},
    {"amount": 10.00, "category": "Transport", "date": "2026-04-12", "note": "Uber", "payment_method": "Card", "merchant": "Uber"},
    {"amount": 55.00, "category": "Education", "date": "2026-04-13", "note": "Course", "payment_method": "Card", "merchant": "Coursera"},
    {"amount": 8.20, "category": "Food", "date": "2026-04-14", "note": "Breakfast", "payment_method": "Apple Pay", "merchant": "Greggs"},
]

with app.app_context():
    user = User.query.filter_by(email="adeeb@imam.com").first()

    if not user:
        user = User(
            first_name="Adeeb",
            last_name="Imam",
            email="adeeb@imam.com",
            monthly_budget=1200,
            is_admin=False
        )
        user.set_password("Adeeb@2711")
        db.session.add(user)
        db.session.commit()

    for item in mock_expenses:
        expense = Expense(
            user_id=user.id,
            amount=item["amount"],
            category=item["category"],
            date=datetime.strptime(item["date"], "%Y-%m-%d").date(),
            note=item["note"],
            payment_method=item["payment_method"],
            merchant=item["merchant"]
        )
        db.session.add(expense)

    db.session.commit()
    print("Mock data added successfully.")