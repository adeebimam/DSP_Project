from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from model import db, Expense, User
from datetime import date, datetime
from collections import defaultdict
import json
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file for local development

app = Flask(__name__)

# Database configuration — supports PostgreSQL (Render) and SQLite (local)
database_url = os.environ.get('DATABASE_URL', 'sqlite:///expenses.db')
# Render uses "postgres://" but SQLAlchemy requires "postgresql://"
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'fallback-dev-key-change-me')

db.init_app(app)

@app.errorhandler(500)
def internal_error(error):
    return f"<h1>500 Internal Server Error</h1><pre>{error}</pre>", 500

@app.route('/', methods=['GET'])
def login():
    print('Login route accessed')
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login_post():
    email = request.form['email']
    password = request.form['password']
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        session['user_id'] = user.id
        session['user_name'] = f"{user.first_name} {user.last_name}"
        return redirect(url_for('dashboard'))
    flash('Invalid email or password')
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('signup'))
        user = User(first_name=first_name, last_name=last_name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/admin-delete-user/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_name = session.get('user_name', '')
    if not user_name.lower().startswith('admin'):
        return redirect(url_for('dashboard'))
    user = User.query.get(user_id)
    if user:
        Expense.query.filter_by(user_id=user.id).delete()  # Delete all expenses for this user first
        db.session.delete(user)
        db.session.commit()
        session['admin_flash'] = 'User deleted.'
    return redirect(url_for('admin_page'))

@app.route('/admin')
def admin_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_name = session.get('user_name', '')
    if not user_name.lower().startswith('admin'):
        return redirect(url_for('dashboard'))
    users = User.query.all()
    admin_flash = session.pop('admin_flash', None)
    return render_template('admin_page.html', users=users, admin_flash=admin_flash)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_name = session.get('user_name', 'User')
    if user_name.lower().startswith('admin'):
        return redirect(url_for('admin_page'))
    user_id = session['user_id']
    expenses = Expense.query.filter_by(user_id=user_id).order_by(Expense.date.desc()).all()
    current_date = date.today()
    monthly_total = sum(
        e.amount for e in expenses
        if e.date.year == current_date.year and e.date.month == current_date.month
    )

    # --- Chart Data ---
    # 1. Spending by category (pie chart)
    category_totals = defaultdict(float)
    for e in expenses:
        if e.date.year == current_date.year and e.date.month == current_date.month:
            category_totals[e.category] += float(e.amount)
    category_labels = list(category_totals.keys())
    category_values = list(category_totals.values())

    # 2. Daily spending this month (bar chart)
    daily_totals = defaultdict(float)
    for e in expenses:
        if e.date.year == current_date.year and e.date.month == current_date.month:
            daily_totals[e.date.strftime('%Y-%m-%d')] += float(e.amount)
    daily_labels = sorted(daily_totals.keys())
    daily_values = [daily_totals[d] for d in daily_labels]

    # 3. Monthly spending trend (last 6 months, line chart)
    monthly_totals = defaultdict(float)
    for e in expenses:
        key = e.date.strftime('%Y-%m')
        monthly_totals[key] += float(e.amount)
    all_months = sorted(monthly_totals.keys())[-6:]
    monthly_labels = all_months
    monthly_values = [monthly_totals[m] for m in all_months]

    # 4. Spending by payment method (doughnut chart)
    payment_totals = defaultdict(float)
    for e in expenses:
        if e.date.year == current_date.year and e.date.month == current_date.month:
            method = e.payment_method or 'Unknown'
            payment_totals[method] += float(e.amount)
    payment_labels = list(payment_totals.keys())
    payment_values = list(payment_totals.values())

    # Get user budget
    user = User.query.get(user_id)
    monthly_budget = user.monthly_budget if user.monthly_budget else 0
    budget_remaining = monthly_budget - monthly_total if monthly_budget else None

    dashboard_flash = session.pop('dashboard_flash', None)
    return render_template('dashboard.html',
        expenses=expenses,
        user_name=user_name,
        current_date=current_date,
        monthly_total=monthly_total,
        category_labels=json.dumps(category_labels),
        category_values=json.dumps(category_values),
        daily_labels=json.dumps(daily_labels),
        daily_values=json.dumps(daily_values),
        monthly_labels=json.dumps(monthly_labels),
        monthly_values=json.dumps(monthly_values),
        payment_labels=json.dumps(payment_labels),
        payment_values=json.dumps(payment_values),
        monthly_budget=monthly_budget,
        budget_remaining=budget_remaining,
        dashboard_flash=dashboard_flash
    )

@app.route('/set-budget', methods=['POST'])
def set_budget():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    budget = request.form.get('monthly_budget', 0)
    try:
        budget = float(budget)
    except ValueError:
        budget = 0
    user = User.query.get(session['user_id'])
    user.monthly_budget = budget
    db.session.commit()
    session['dashboard_flash'] = 'Budget updated successfully!'
    return redirect(url_for('dashboard'))

@app.route('/add-expense', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        amount = request.form['amount']
        category = request.form['category']
        date_str = request.form['date']
        payment_method = request.form.get('payment_method')
        merchant = request.form.get('merchant')
        note = request.form.get('note')
        # Backend validation for required fields (note is optional)
        if not all([amount, category, date_str, payment_method, merchant]):
            flash('All fields except note are required.')
            return render_template('add-expense.html', amount=amount, category=category, date=date_str, payment_method=payment_method, merchant=merchant, note=note)
        try:
            expense_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            expense_date = date.today()
        expense = Expense(
            user_id=session['user_id'],
            amount=amount,
            category=category,
            date=expense_date,
            note=note,
            payment_method=payment_method,
            merchant=merchant
        )
        db.session.add(expense)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add-expense.html', current_date=date.today().isoformat())

@app.route('/edit-expense/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != session['user_id']:
        abort(403)
    if request.method == 'POST':
        amount = request.form['amount']
        category = request.form['category']
        date_str = request.form['date']
        payment_method = request.form.get('payment_method')
        merchant = request.form.get('merchant')
        note = request.form.get('note')
        if not all([amount, category, date_str, payment_method, merchant]):
            flash('All fields except note are required.')
            return render_template('edit-expense.html', expense=expense)
        expense.amount = amount
        expense.category = category
        try:
            expense.date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            expense.date = date.today()
        expense.note = note
        expense.payment_method = payment_method
        expense.merchant = merchant
        db.session.commit()
        session['dashboard_flash'] = 'Expense updated!'
        return redirect(url_for('dashboard'))
    return render_template('edit-expense.html', expense=expense)

@app.route('/delete-expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != session['user_id']:
        abort(403)
    db.session.delete(expense)
    db.session.commit()
    session['dashboard_flash'] = 'Expense deleted.'
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/account-settings')
def account_settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('account_settings.html', user=user)

@app.route('/delete-account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    # Delete all expenses for this user first
    Expense.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    session.clear()
    flash('Your account has been deleted.')
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            # Redirect to password reset page (to be implemented)
            return redirect(url_for('reset_password', email=email))
        else:
            flash('No account found with that email.')
            return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = request.args.get('email')
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Invalid password reset request.')
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        new_password = request.form['new_password']
        user.set_password(new_password)
        db.session.commit()
        flash('Password updated! You can now log in.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', email=email)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_ENV') == 'development')
