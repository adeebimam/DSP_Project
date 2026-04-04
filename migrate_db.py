"""
Database migration script — safely adds any missing columns to existing tables.
Run this after deploying new model changes to a production database.

Usage:
    python migrate_db.py

This is called automatically by build.sh on Render deployments.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from app import app, db
from sqlalchemy import text, inspect

def migrate():
    with app.app_context():
        inspector = inspect(db.engine)

        # ── User table migrations ──
        if 'user' in inspector.get_table_names():
            existing_columns = [col['name'] for col in inspector.get_columns('user')]
            print(f"Existing 'user' columns: {existing_columns}")

            # Add is_admin column if missing
            if 'is_admin' not in existing_columns:
                print("Adding 'is_admin' column to user table...")
                db.session.execute(text(
                    "ALTER TABLE \"user\" ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE"
                ))
                db.session.commit()
                print("✅ 'is_admin' column added successfully.")
            else:
                print("✅ 'is_admin' column already exists.")

            # Add monthly_budget column if missing
            if 'monthly_budget' not in existing_columns:
                print("Adding 'monthly_budget' column to user table...")
                db.session.execute(text(
                    "ALTER TABLE \"user\" ADD COLUMN monthly_budget FLOAT DEFAULT 0"
                ))
                db.session.commit()
                print("✅ 'monthly_budget' column added successfully.")
            else:
                print("✅ 'monthly_budget' column already exists.")
        else:
            print("User table does not exist yet — db.create_all() will handle it.")

        # Ensure all tables exist (creates any brand new tables)
        db.create_all()
        print("✅ Database migration complete.")

if __name__ == '__main__':
    migrate()
