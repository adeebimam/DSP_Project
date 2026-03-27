"""
Utility to inspect the cloud PostgreSQL database on Render.
Usage: python3 inspect_cloud_db.py

Set the DATABASE_URL environment variable to your Render External Database URL, 
or paste it below.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

os.environ['DATABASE_URL'] = 'postgresql://adeeb_imam:k8qaUYDj1M4uxidZQV2jEkuyD1y25vB3@dpg-d7337hngi27c73cstmkg-a.frankfurt-postgres.render.com/expense_tracker_fgad'

from app import app, db
from model import User, Expense

def inspect():
    with app.app_context():
        print("-" * 60)
        print("CLOUD DATABASE INSPECTION")
        print("-" * 60)
        
        # Users
        users = User.query.all()
        print(f"\nUsers ({len(users)}):")
        print("-" * 60)
        for u in users:
            print(f"  ID: {u.id} | {u.first_name} {u.last_name} | {u.email} | Budget: £{u.monthly_budget or 0:.2f}")
        
        # Expenses
        expenses = Expense.query.order_by(Expense.date.desc()).all()
        print(f"\nExpenses ({len(expenses)}):")
        print("-" * 60)
        for e in expenses:
            print(f"  ID: {e.id} | User {e.user_id} | £{e.amount:.2f} | {e.category} | {e.date} | {e.merchant} | {e.payment_method}")
        
        if not users and not expenses:
            print("\n  (Database is empty — no users or expenses yet)")
        
        print("\n" + "=" * 60)

if __name__ == '__main__':
    inspect()
