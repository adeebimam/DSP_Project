"""
Unit tests for Cloud Expense Tracker
Run with: python3 -m pytest tests.py -v
"""
import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'  # Force SQLite for tests
os.environ['FLASK_SECRET_KEY'] = 'test-secret-key'

import pytest
from app import app, db
from model import User, Expense
from datetime import date


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def client():
    """Create a test client with a fresh in-memory database for each test."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()


@pytest.fixture
def registered_user(client):
    """Register a test user and return their details."""
    with app.app_context():
        user = User(first_name='Test', last_name='User', email='test@test.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {'id': user_id, 'email': 'test@test.com', 'password': 'password123'}


@pytest.fixture
def logged_in_client(client, registered_user):
    """Return a client that is already logged in."""
    client.post('/login', data={
        'email': registered_user['email'],
        'password': registered_user['password']
    })
    return client


@pytest.fixture
def admin_client(client):
    """Return a client logged in as admin."""
    with app.app_context():
        admin = User(first_name='Admin', last_name='User', email='admin@admin.com')
        admin.set_password('adminpassword')
        db.session.add(admin)
        db.session.commit()
    client.post('/login', data={
        'email': 'admin@admin.com',
        'password': 'adminpassword'
    })
    return client


# ── Authentication Tests ──────────────────────────────────

class TestAuthentication:
    """Tests for login, signup, and logout."""

    def test_login_page_loads(self, client):
        """GET / should return 200 and show the login page."""
        response = client.get('/')
        assert response.status_code == 200

    def test_signup_page_loads(self, client):
        """GET /signup should return 200."""
        response = client.get('/signup')
        assert response.status_code == 200

    def test_signup_creates_user(self, client):
        """POST /signup with valid data should create a user and redirect."""
        response = client.post('/signup', data={
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@test.com',
            'password': 'securepass'
        }, follow_redirects=False)
        assert response.status_code == 302  # Redirect to login
        with app.app_context():
            user = User.query.filter_by(email='john@test.com').first()
            assert user is not None
            assert user.first_name == 'John'
            assert user.last_name == 'Doe'

    def test_signup_duplicate_email(self, client, registered_user):
        """POST /signup with an existing email should flash an error."""
        response = client.post('/signup', data={
            'first_name': 'Another',
            'last_name': 'User',
            'email': registered_user['email'],
            'password': 'anotherpass'
        }, follow_redirects=True)
        assert b'Email already registered' in response.data

    def test_login_valid_credentials(self, client, registered_user):
        """POST /login with correct credentials should redirect to dashboard."""
        response = client.post('/login', data={
            'email': registered_user['email'],
            'password': registered_user['password']
        }, follow_redirects=False)
        assert response.status_code == 302
        assert '/dashboard' in response.headers['Location']

    def test_login_invalid_password(self, client, registered_user):
        """POST /login with wrong password should flash an error."""
        response = client.post('/login', data={
            'email': registered_user['email'],
            'password': 'wrongpassword'
        }, follow_redirects=True)
        assert b'Invalid email or password' in response.data

    def test_login_nonexistent_email(self, client):
        """POST /login with unknown email should flash an error."""
        response = client.post('/login', data={
            'email': 'nobody@test.com',
            'password': 'anything'
        }, follow_redirects=True)
        assert b'Invalid email or password' in response.data

    def test_logout(self, logged_in_client):
        """GET /logout should clear session and redirect to login."""
        response = logged_in_client.get('/logout', follow_redirects=False)
        assert response.status_code == 302
        # After logout, accessing dashboard should redirect to login
        response = logged_in_client.get('/dashboard', follow_redirects=False)
        assert response.status_code == 302


# ── Dashboard Tests ───────────────────────────────────────

class TestDashboard:
    """Tests for the dashboard page."""

    def test_dashboard_requires_login(self, client):
        """GET /dashboard without login should redirect to login."""
        response = client.get('/dashboard', follow_redirects=False)
        assert response.status_code == 302

    def test_dashboard_loads_for_logged_in_user(self, logged_in_client):
        """GET /dashboard should return 200 for logged-in user."""
        response = logged_in_client.get('/dashboard')
        assert response.status_code == 200
        assert b'Welcome' in response.data

    def test_dashboard_shows_expenses(self, logged_in_client, registered_user):
        """Dashboard should display expenses after adding one."""
        logged_in_client.post('/add-expense', data={
            'amount': '25.50',
            'category': 'Food',
            'date': date.today().isoformat(),
            'payment_method': 'Cash',
            'merchant': 'Tesco'
        })
        response = logged_in_client.get('/dashboard')
        assert response.status_code == 200
        assert b'Tesco' in response.data
        assert b'Food' in response.data


# ── Expense CRUD Tests ────────────────────────────────────

class TestExpenseCRUD:
    """Tests for adding, editing, and deleting expenses."""

    def test_add_expense_page_loads(self, logged_in_client):
        """GET /add-expense should return 200."""
        response = logged_in_client.get('/add-expense')
        assert response.status_code == 200

    def test_add_expense_page_requires_login(self, client):
        """GET /add-expense without login should redirect."""
        response = client.get('/add-expense', follow_redirects=False)
        assert response.status_code == 302

    def test_add_expense_success(self, logged_in_client):
        """POST /add-expense with valid data should create an expense."""
        response = logged_in_client.post('/add-expense', data={
            'amount': '15.99',
            'category': 'Transport',
            'date': '2026-03-27',
            'payment_method': 'Debit Card',
            'merchant': 'Uber',
            'note': 'Ride to uni'
        }, follow_redirects=False)
        assert response.status_code == 302
        with app.app_context():
            expense = Expense.query.first()
            assert expense is not None
            assert expense.amount == 15.99
            assert expense.category == 'Transport'
            assert expense.merchant == 'Uber'
            assert expense.note == 'Ride to uni'

    def test_add_expense_missing_fields(self, logged_in_client):
        """POST /add-expense with missing required fields should show error."""
        response = logged_in_client.post('/add-expense', data={
            'amount': '10.00',
            'category': '',
            'date': '2026-03-27',
            'payment_method': 'Cash',
            'merchant': 'Shop'
        }, follow_redirects=True)
        assert b'All fields except note are required' in response.data

    def test_edit_expense_page_loads(self, logged_in_client):
        """GET /edit-expense/<id> should return 200 for owner."""
        logged_in_client.post('/add-expense', data={
            'amount': '20.00',
            'category': 'Food',
            'date': '2026-03-27',
            'payment_method': 'Cash',
            'merchant': 'Greggs'
        })
        with app.app_context():
            expense = Expense.query.first()
            expense_id = expense.id
        response = logged_in_client.get(f'/edit-expense/{expense_id}')
        assert response.status_code == 200

    def test_edit_expense_success(self, logged_in_client):
        """POST /edit-expense/<id> should update the expense."""
        logged_in_client.post('/add-expense', data={
            'amount': '20.00',
            'category': 'Food',
            'date': '2026-03-27',
            'payment_method': 'Cash',
            'merchant': 'Greggs'
        })
        with app.app_context():
            expense_id = Expense.query.first().id
        response = logged_in_client.post(f'/edit-expense/{expense_id}', data={
            'amount': '35.00',
            'category': 'Shopping',
            'date': '2026-03-26',
            'payment_method': 'Credit Card',
            'merchant': 'Amazon'
        }, follow_redirects=False)
        assert response.status_code == 302
        with app.app_context():
            expense = Expense.query.get(expense_id)
            assert expense.amount == 35.0
            assert expense.category == 'Shopping'
            assert expense.merchant == 'Amazon'

    def test_delete_expense(self, logged_in_client):
        """POST /delete-expense/<id> should remove the expense."""
        logged_in_client.post('/add-expense', data={
            'amount': '10.00',
            'category': 'Bills',
            'date': '2026-03-27',
            'payment_method': 'Online',
            'merchant': 'Netflix'
        })
        with app.app_context():
            expense_id = Expense.query.first().id
        response = logged_in_client.post(f'/delete-expense/{expense_id}', follow_redirects=False)
        assert response.status_code == 302
        with app.app_context():
            assert Expense.query.get(expense_id) is None

    def test_cannot_edit_other_users_expense(self, client, registered_user):
        """A user should not be able to edit another user's expense."""
        # Create a second user and an expense for them
        with app.app_context():
            user2 = User(first_name='Other', last_name='Person', email='other@test.com')
            user2.set_password('pass')
            db.session.add(user2)
            db.session.commit()
            expense = Expense(user_id=user2.id, amount=50, category='Food',
                              date=date.today(), payment_method='Cash', merchant='Shop')
            db.session.add(expense)
            db.session.commit()
            expense_id = expense.id
        # Login as the first user
        client.post('/login', data={
            'email': registered_user['email'],
            'password': registered_user['password']
        })
        response = client.get(f'/edit-expense/{expense_id}')
        assert response.status_code == 403


# ── Budget Tests ──────────────────────────────────────────

class TestBudget:
    """Tests for the budget feature."""

    def test_set_budget(self, logged_in_client, registered_user):
        """POST /set-budget should update the user's monthly budget."""
        response = logged_in_client.post('/set-budget', data={
            'monthly_budget': '500.00'
        }, follow_redirects=False)
        assert response.status_code == 302
        with app.app_context():
            user = User.query.get(registered_user['id'])
            assert user.monthly_budget == 500.00

    def test_set_budget_requires_login(self, client):
        """POST /set-budget without login should redirect."""
        response = client.post('/set-budget', data={
            'monthly_budget': '500.00'
        }, follow_redirects=False)
        assert response.status_code == 302


# ── Account Management Tests ─────────────────────────────

class TestAccountManagement:
    """Tests for account settings and deletion."""

    def test_account_settings_loads(self, logged_in_client):
        """GET /account-settings should return 200."""
        response = logged_in_client.get('/account-settings')
        assert response.status_code == 200

    def test_account_settings_requires_login(self, client):
        """GET /account-settings without login should redirect."""
        response = client.get('/account-settings', follow_redirects=False)
        assert response.status_code == 302

    def test_delete_account(self, logged_in_client, registered_user):
        """POST /delete-account should remove the user and their expenses."""
        # Add an expense first
        logged_in_client.post('/add-expense', data={
            'amount': '10.00',
            'category': 'Food',
            'date': '2026-03-27',
            'payment_method': 'Cash',
            'merchant': 'Shop'
        })
        response = logged_in_client.post('/delete-account', follow_redirects=True)
        assert b'Your account has been deleted' in response.data
        with app.app_context():
            assert User.query.get(registered_user['id']) is None
            assert Expense.query.filter_by(user_id=registered_user['id']).count() == 0


# ── Password Reset Tests ─────────────────────────────────

class TestPasswordReset:
    """Tests for forgot/reset password."""

    def test_forgot_password_page_loads(self, client):
        """GET /forgot-password should return 200."""
        response = client.get('/forgot-password')
        assert response.status_code == 200

    def test_forgot_password_valid_email(self, client, registered_user):
        """POST /forgot-password with valid email should redirect to reset."""
        response = client.post('/forgot-password', data={
            'email': registered_user['email']
        }, follow_redirects=False)
        assert response.status_code == 302
        assert 'reset-password' in response.headers['Location']

    def test_forgot_password_invalid_email(self, client):
        """POST /forgot-password with unknown email should flash error."""
        response = client.post('/forgot-password', data={
            'email': 'nobody@test.com'
        }, follow_redirects=True)
        assert b'No account found with that email' in response.data

    def test_reset_password(self, client, registered_user):
        """POST /reset-password should update the password."""
        response = client.post(
            f'/reset-password?email={registered_user["email"]}',
            data={'new_password': 'newpassword123'},
            follow_redirects=True
        )
        assert b'Password updated' in response.data
        # Verify new password works
        response = client.post('/login', data={
            'email': registered_user['email'],
            'password': 'newpassword123'
        }, follow_redirects=False)
        assert response.status_code == 302
        assert '/dashboard' in response.headers['Location']


# ── Admin Tests ───────────────────────────────────────────

class TestAdmin:
    """Tests for admin functionality."""

    def test_admin_redirects_to_admin_page(self, admin_client):
        """Admin user accessing /dashboard should be redirected to /admin."""
        response = admin_client.get('/dashboard', follow_redirects=False)
        assert response.status_code == 302
        assert '/admin' in response.headers['Location']

    def test_admin_page_loads(self, admin_client):
        """GET /admin should return 200 for admin user."""
        response = admin_client.get('/admin')
        assert response.status_code == 200

    def test_non_admin_cannot_access_admin_page(self, logged_in_client):
        """Non-admin user accessing /admin should be redirected to dashboard."""
        response = logged_in_client.get('/admin', follow_redirects=False)
        assert response.status_code == 302
        assert '/dashboard' in response.headers['Location']

    def test_admin_delete_user(self, admin_client, registered_user):
        """POST /admin-delete-user/<id> should delete the user."""
        response = admin_client.post(
            f'/admin-delete-user/{registered_user["id"]}',
            follow_redirects=False
        )
        assert response.status_code == 302
        with app.app_context():
            assert User.query.get(registered_user['id']) is None


# ── Model Tests ───────────────────────────────────────────

class TestModels:
    """Tests for the database models."""

    def test_user_password_hashing(self, client):
        """User password should be hashed and verifiable."""
        with app.app_context():
            user = User(first_name='A', last_name='B', email='a@b.com')
            user.set_password('mypassword')
            assert user.password_hash != 'mypassword'
            assert user.check_password('mypassword') is True
            assert user.check_password('wrongpassword') is False

    def test_user_default_budget(self, client):
        """New user should have a default budget of 0."""
        with app.app_context():
            user = User(first_name='A', last_name='B', email='a@b.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()
            assert user.monthly_budget == 0

    def test_expense_creation(self, client):
        """Expense should store all fields correctly."""
        with app.app_context():
            user = User(first_name='A', last_name='B', email='a@b.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()
            expense = Expense(
                user_id=user.id, amount=42.50, category='Books',
                date=date(2026, 3, 27), payment_method='Online',
                merchant='Amazon', note='Textbook'
            )
            db.session.add(expense)
            db.session.commit()
            saved = Expense.query.first()
            assert saved.amount == 42.50
            assert saved.category == 'Books'
            assert saved.merchant == 'Amazon'
            assert saved.note == 'Textbook'
            assert saved.user_id == user.id
