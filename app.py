from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, Response, jsonify
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from model import db, Expense, User
from datetime import date, datetime
from collections import defaultdict
import csv
import io
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file for local development

app = Flask(__name__)

# Trust reverse proxy headers (Render, Heroku, etc.)
# This ensures Flask sees the correct HTTPS scheme, host, and client IP
# so that session cookies, CSRF checks, and url_for() work correctly.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Database configuration — supports PostgreSQL (Render) and SQLite (local)
database_url = os.environ.get('DATABASE_URL', 'sqlite:///expenses.db')
# Render uses "postgres://" but SQLAlchemy requires "postgresql://"
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'fallback-dev-key-change-me')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db.init_app(app)
csrf = CSRFProtect(app)

import logging

# Set up logging for production debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 Internal Server Error: {error}", exc_info=True)
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
        session['is_admin'] = user.is_admin
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
    """Admin-only: delete a user and all their expenses."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not session.get('is_admin'):
        return redirect(url_for('dashboard'))
    user = User.query.get(user_id)
    if user:
        Expense.query.filter_by(user_id=user.id).delete()  # Delete all expenses for this user first
        db.session.delete(user)
        db.session.commit()
        session['admin_flash'] = 'User deleted.'
    return redirect(url_for('admin_page'))

@app.route('/admin-toggle-role/<int:user_id>', methods=['POST'])
def admin_toggle_role(user_id):
    """Admin-only: promote a user to admin or demote them back to regular user."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not session.get('is_admin'):
        return redirect(url_for('dashboard'))
    # Prevent admin from demoting themselves
    if user_id == session['user_id']:
        session['admin_flash'] = 'You cannot change your own role.'
        return redirect(url_for('admin_page'))
    user = User.query.get(user_id)
    if user:
        user.is_admin = not user.is_admin
        db.session.commit()
        action = 'promoted to Admin' if user.is_admin else 'demoted to User'
        session['admin_flash'] = f'{user.first_name} {user.last_name} has been {action}.'
    return redirect(url_for('admin_page'))

@app.route('/admin')
def admin_page():
    """Admin dashboard — view all users and manage roles."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not session.get('is_admin'):
        return redirect(url_for('dashboard'))
    users = User.query.all()
    admin_flash = session.pop('admin_flash', None)
    return render_template('admin_page.html', users=users, admin_flash=admin_flash)

@app.route('/dashboard')
def dashboard():
    """Main dashboard — shows expenses, charts, budget, and AI prediction."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('is_admin'):
        return redirect(url_for('admin_page'))
    user_name = session.get('user_name', 'User')
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

@app.route('/export-csv')
def export_csv():
    """Export the current user's expenses as a CSV file."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    expenses = Expense.query.filter_by(user_id=user_id).order_by(Expense.date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Category', 'Merchant', 'Payment Method', 'Amount', 'Note'])
    for e in expenses:
        writer.writerow([
            e.date.strftime('%Y-%m-%d'),
            e.category,
            e.merchant or '',
            e.payment_method or '',
            f'{e.amount:.2f}',
            e.note or ''
        ])

    csv_data = output.getvalue()
    output.close()
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=expenses_{date.today().isoformat()}.csv'}
    )

@app.route('/export-pdf')
def export_pdf():
    """Export the current user's expenses as a styled PDF report."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = User.query.get(user_id)
    expenses = Expense.query.filter_by(user_id=user_id).order_by(Expense.date.desc()).all()

    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title
    pdf.set_font('Helvetica', 'B', 18)
    pdf.cell(0, 12, 'Expense Report', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f'{user.first_name} {user.last_name}  |  Generated {date.today().strftime("%d %B %Y")}', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.ln(6)

    # Summary
    current_date = date.today()
    monthly_total = sum(
        e.amount for e in expenses
        if e.date.year == current_date.year and e.date.month == current_date.month
    )
    total_all = sum(e.amount for e in expenses)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 8, f'Total Expenses: {len(expenses)}    |    This Month: GBP {monthly_total:.2f}    |    All Time: GBP {total_all:.2f}', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.ln(4)

    if expenses:
        # Table header
        col_widths = [24, 28, 38, 30, 24, 46]
        headers = ['Date', 'Category', 'Merchant', 'Payment', 'Amount', 'Note']

        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_fill_color(79, 70, 229)
        pdf.set_text_color(255, 255, 255)
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 8, header, border=1, fill=True, align='C')
        pdf.ln()

        # Table rows
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(0, 0, 0)
        fill = False
        for e in expenses:
            if pdf.get_y() > 260:
                pdf.add_page()
                # Repeat header on new page
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_fill_color(79, 70, 229)
                pdf.set_text_color(255, 255, 255)
                for i, header in enumerate(headers):
                    pdf.cell(col_widths[i], 8, header, border=1, fill=True, align='C')
                pdf.ln()
                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(0, 0, 0)
                fill = False

            if fill:
                pdf.set_fill_color(245, 247, 250)
            else:
                pdf.set_fill_color(255, 255, 255)

            row = [
                e.date.strftime('%d %b %Y'),
                e.category or '',
                (e.merchant or '-')[:20],
                (e.payment_method or '-'),
                f'GBP {e.amount:.2f}',
                (e.note or '-')[:28],
            ]
            for i, val in enumerate(row):
                pdf.cell(col_widths[i], 7, val, border=1, fill=True, align='C' if i == 4 else 'L')
            pdf.ln()
            fill = not fill
    else:
        pdf.ln(10)
        pdf.set_font('Helvetica', 'I', 11)
        pdf.cell(0, 10, 'No expenses recorded yet.', new_x='LMARGIN', new_y='NEXT', align='C')

    pdf_bytes = bytes(pdf.output())
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename=expenses_{date.today().isoformat()}.pdf'}
    )

# ── OCR Receipt Scanning ──────────────────────────────────

@app.route('/scan-receipt', methods=['GET', 'POST'])
def scan_receipt():
    """Upload a receipt image and extract expense details using OCR."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files.get('receipt')
        if not file or file.filename == '':
            flash('Please select a receipt image to upload.')
            return render_template('scan_receipt.html')

        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in allowed_extensions:
            flash('Invalid file type. Please upload an image (PNG, JPG, etc.).')
            return render_template('scan_receipt.html')

        try:
            from PIL import Image
            import pytesseract

            image = Image.open(file.stream)
            raw_text = pytesseract.image_to_string(image)

            # Parse amount — look for currency patterns like £12.99, $5.00, 12.99, Total: 15.50
            amount = None
            amount_patterns = [
                r'(?:total|amount|sum|due|paid|balance|grand\s*total)[:\s]*[£$€]?\s*(\d+[.,]\d{2})',
                r'[£$€]\s*(\d+[.,]\d{2})',
                r'(\d+[.,]\d{2})',
            ]
            for pattern in amount_patterns:
                matches = re.findall(pattern, raw_text, re.IGNORECASE)
                if matches:
                    # Take the last match (often the total at the bottom of a receipt)
                    amount = matches[-1].replace(',', '.')
                    break

            # Parse merchant — typically the first non-empty line
            merchant = None
            lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
            if lines:
                merchant = lines[0][:100]  # Cap at 100 chars to match model

            # Parse date — look for date patterns
            receipt_date = None
            date_patterns = [
                r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
                r'(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})',
            ]
            for pattern in date_patterns:
                match = re.search(pattern, raw_text)
                if match:
                    date_str = match.group(1)
                    # Try to parse various date formats
                    for fmt in ('%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y', '%Y/%m/%d'):
                        try:
                            receipt_date = datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            continue
                    if receipt_date:
                        break

            return render_template('scan_receipt.html',
                ocr_text=raw_text,
                extracted_amount=amount,
                extracted_merchant=merchant,
                extracted_date=receipt_date or date.today().isoformat()
            )

        except Exception as e:
            flash(f'Error processing receipt: {str(e)}')
            return render_template('scan_receipt.html')

    return render_template('scan_receipt.html')

# ── AI Spending Prediction ────────────────────────────────

@app.route('/predict-spending')
def predict_spending():
    """Use linear regression to predict next month's spending."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    expenses = Expense.query.filter_by(user_id=user_id).all()

    # Aggregate monthly totals
    monthly_totals = defaultdict(float)
    for e in expenses:
        key = e.date.strftime('%Y-%m')
        monthly_totals[key] += float(e.amount)

    sorted_months = sorted(monthly_totals.keys())

    # Need at least 2 months of data to make a prediction
    if len(sorted_months) < 2:
        return jsonify({
            'prediction': None,
            'message': 'Need at least 2 months of expense data to generate a prediction.',
            'history': {}
        })

    try:
        from sklearn.linear_model import LinearRegression
        import numpy as np

        # X = month index (0, 1, 2, ...), y = monthly total
        X = np.arange(len(sorted_months)).reshape(-1, 1)
        y = np.array([monthly_totals[m] for m in sorted_months])

        model = LinearRegression()
        model.fit(X, y)

        # Predict next month
        next_index = np.array([[len(sorted_months)]])
        prediction = float(model.predict(next_index)[0])
        prediction = max(prediction, 0)  # Can't predict negative spending

        # Calculate R² score for confidence
        r2_score = float(model.score(X, y))

        # Determine next month label
        last_month = datetime.strptime(sorted_months[-1], '%Y-%m')
        if last_month.month == 12:
            next_month_label = f'{last_month.year + 1}-01'
        else:
            next_month_label = f'{last_month.year}-{last_month.month + 1:02d}'

        return jsonify({
            'prediction': round(prediction, 2),
            'next_month': next_month_label,
            'confidence': round(r2_score, 2),
            'message': f'Based on {len(sorted_months)} months of data',
            'history': {m: round(monthly_totals[m], 2) for m in sorted_months}
        })

    except Exception as e:
        return jsonify({
            'prediction': None,
            'message': f'Could not generate prediction: {str(e)}',
            'history': {}
        })

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
    # Support pre-filling from receipt scanner via query params
    prefill_amount = request.args.get('amount', '')
    prefill_merchant = request.args.get('merchant', '')
    prefill_date = request.args.get('date', date.today().isoformat())
    return render_template('add-expense.html',
        current_date=date.today().isoformat(),
        amount=prefill_amount,
        merchant=prefill_merchant,
        date=prefill_date
    )

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

def init_db():
    """Initialize database tables with retry logic for cloud deployments."""
    import time
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with app.app_context():
                db.create_all()
            print("✅ Database tables created successfully.")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # Exponential backoff: 1, 2, 4, 8, 16 seconds
                print(f"⏳ Database not ready (attempt {attempt + 1}/{max_retries}), retrying in {wait}s... Error: {e}")
                time.sleep(wait)
            else:
                print(f"❌ Could not connect to database after {max_retries} attempts: {e}")
                raise

init_db()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_ENV') == 'development')
