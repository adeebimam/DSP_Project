# Cloud Expense Tracker

A **cloud-based multiuser expense management system** built with Flask and PostgreSQL. Track your daily spending, set budgets, visualise your finances with interactive charts, and manage your account — all from a modern, responsive web interface.

---

## Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Usage](#-usage)
- [Screenshots](#-screenshots)
- [Database Schema](#-database-schema)
- [Routes & API](#-routes--api)
- [Future Improvements](#-future-improvements)

---

## Features

### Core Functionality
- **Multi-user authentication** — Sign up, log in, log out with secure password hashing (Werkzeug)
- **CSRF protection** — All forms protected with Flask-WTF CSRF tokens
- **Expense CRUD** — Add, edit, and delete expenses with category, payment method, merchant, date, and notes
- **Dashboard** — At-a-glance summary cards showing monthly spending, budget, remaining balance, and total expenses
- **Budget monitoring** — Set a monthly budget, see a progress bar, and receive warnings when nearing or exceeding the limit
- **Export to CSV** — Download all your expenses as a CSV file
- **Export to PDF** — Download a styled PDF expense report with summary and table

### Data Visualisation (Chart.js)
-  **Pie chart** — Spending by category (current month)
-  **Bar chart** — Daily spending breakdown (current month)
-  **Line chart** — Monthly spending trend (last 6 months)
-  **Doughnut chart** — Spending by payment method (current month)

### OCR Receipt Scanning (Tesseract)
- Upload a receipt photo and automatically extract amount, merchant, and date
- Parsed data pre-fills the Add Expense form for quick entry
- Supports common image formats (PNG, JPG, TIFF, etc.)

### AI Spending Prediction (scikit-learn)
- Linear Regression model predicts next month's spending based on historical data
- Shows model confidence (R² score) on the dashboard
- Requires at least 2 months of data to generate a prediction

### Admin Panel
- **Role-based access control** — `is_admin` flag on the User model (not name-based)
- Admin users can view all registered users, delete accounts, and promote/demote other users to/from admin
- Admins cannot change their own role (self-demotion protection)
- Only existing admins can assign the admin role — no hardcoded credentials

### Account Management
- View account settings (name, email)
- Delete your own account (with confirmation)
- Forgot password / reset password flow

### UI/UX
- Modern, responsive design using **Inter** font (Google Fonts)
- Consistent navigation bar across all pages via a Jinja2 base template
- Flash messages for success, warnings, and errors
- Mobile-friendly layout with CSS Grid and Flexbox

---

## Tech Stack

| Layer        | Technology                                |
|--------------|-------------------------------------------|
| **Backend**  | Python 3, Flask, SQLAlchemy, Gunicorn     |
| **Database** | PostgreSQL (Render) / SQLite (local dev)  |
| **Frontend** | HTML5, CSS3, Jinja2 templates             |
| **Charts**   | Chart.js (CDN)                            |
| **OCR**      | Tesseract OCR, pytesseract, Pillow        |
| **AI/ML**    | scikit-learn (Linear Regression), NumPy   |
| **PDF**      | fpdf2                                     |
| **Security** | Werkzeug password hashing, Flask-WTF CSRF |
| **Fonts**    | Google Fonts (Inter)                      |
| **Hosting**  | Render (Web Service + PostgreSQL)         |
| **Testing**  | pytest (60 tests)                         |

---

## Project Structure

```
DSP_final_project/
├── app.py                  # Main Flask application (routes & logic)
├── model.py                # SQLAlchemy database models (User, Expense)
├── tests.py                # pytest unit tests (49 tests)
├── requirements.txt        # Python dependencies
├── build.sh                # Render build script
├── render.yaml             # Render deployment blueprint
├── create_admin.py         # Script to create an admin user
├── find_and_inspect_db.py  # Utility to inspect the database
├── .env                    # Local environment variables (not committed)
├── .gitignore              # Git ignore rules
├── instance/
│   └── expenses.db         # SQLite database (local dev, auto-generated)
├── static/
│   └── style.css           # All CSS styles
└── templates/
    ├── base.html            # Base template with navbar & flash messages
    ├── index.html           # Login page
    ├── signup.html          # Sign up page
    ├── dashboard.html       # Main dashboard with charts & budget
    ├── add-expense.html     # Add new expense form
    ├── edit-expense.html    # Edit existing expense form
    ├── account_settings.html# Account settings page
    ├── admin_page.html      # Admin dashboard
    ├── scan_receipt.html    # OCR receipt scanning page
    ├── forgot_password.html # Forgot password page
    └── reset_password.html  # Reset password page
```

---

## Installation

### Prerequisites
- Python 3.10+
- pip

### Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   cd YOUR_REPO_NAME
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python3 app.py
   ```

5. **Open in browser:**
   ```
   http://127.0.0.1:5000
   ```

The database (`instance/expenses.db`) will be created automatically on first run (SQLite for local dev).

### Running Tests

```bash
python3 -m pytest tests.py -v
```

### Cloud Deployment (Render)

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → **New** → **Blueprint**
3. Connect your GitHub repo — Render will auto-detect `render.yaml`
4. Render will:
   - Create a PostgreSQL database
   - Set `DATABASE_URL`, `FLASK_SECRET_KEY` automatically
   - Build with `build.sh` and start with `gunicorn app:app`
5. Your app will be live at `https://your-app.onrender.com`

> **Manual setup:** If not using Blueprint, create a **Web Service** and a **PostgreSQL** database on Render. Set `DATABASE_URL` (from DB), `FLASK_SECRET_KEY` (generate one), and `FLASK_ENV=production` as environment variables.

---

## Usage

### Workflow
1. **Sign up** or **log in** with your credentials
2. **Set a monthly budget** on the dashboard
3. **Add expenses** with amount, category, payment method, merchant, date, and optional notes
4. **View charts** to understand your spending patterns
5. **Edit or delete** expenses from the dashboard table
6. **Monitor your budget** — warnings appear when you're close to or over budget

---

## Database Schema

### User
| Column          | Type         | Description                  |
|-----------------|--------------|------------------------------|
| id              | Integer (PK) | Auto-increment primary key   |
| first_name      | String(50)   | User's first name            |
| last_name       | String(50)   | User's last name             |
| email           | String(120)  | Unique email address         |
| password_hash   | String(256)  | Hashed password (Werkzeug)   |
| monthly_budget  | Float        | Monthly budget amount        |
| is_admin        | Boolean      | Admin role flag (default: false) |

### Expense
| Column          | Type         | Description                  |
|-----------------|--------------|------------------------------|
| id              | Integer (PK) | Auto-increment primary key   |
| user_id         | Integer (FK) | References User.id           |
| amount          | Float        | Expense amount               |
| category        | String(50)   | Expense category             |
| date            | Date         | Date of expense              |
| note            | String(200)  | Optional note                |
| payment_method  | String(30)   | Cash, Credit Card, etc.      |
| merchant        | String(100)  | Where the purchase was made  |
| created_at      | DateTime     | Auto-set on creation         |

---

## Routes & API

| Method | Route                           | Description                     | Auth Required |
|--------|---------------------------------|---------------------------------|---------------|
| GET    | `/`                             | Login page                      | No            |
| POST   | `/login`                        | Process login                   | No            |
| GET/POST | `/signup`                     | Sign up page & form             | No            |
| GET    | `/dashboard`                    | Main dashboard with charts      | Yes           |
| GET/POST | `/add-expense`                | Add new expense                 | Yes           |
| GET/POST | `/edit-expense/<id>`          | Edit an expense                 | Yes           |
| POST   | `/delete-expense/<id>`          | Delete an expense               | Yes           |
| POST   | `/set-budget`                   | Set monthly budget              | Yes           |
| GET    | `/export-csv`                   | Download expenses as CSV        | Yes           |
| GET    | `/export-pdf`                   | Download expenses as PDF report | Yes           |
| GET/POST | `/scan-receipt`               | OCR receipt scanning            | Yes           |
| GET    | `/predict-spending`             | AI spending prediction (JSON)   | Yes           |
| GET    | `/account-settings`             | View account info               | Yes           |
| POST   | `/delete-account`               | Delete your account             | Yes           |
| GET    | `/admin`                        | Admin dashboard                 | Admin         |
| POST   | `/admin-delete-user/<id>`       | Delete a user (admin only)      | Admin         |
| POST   | `/admin-toggle-role/<id>`       | Promote/demote user role        | Admin         |
| GET/POST | `/forgot-password`            | Forgot password flow            | No            |
| GET/POST | `/reset-password`             | Reset password flow             | No            |
| GET    | `/logout`                       | Log out and clear session       | Yes           |

---

## Future Improvements

- [x] Cloud database migration (PostgreSQL via Render)
- [x] Cloud deployment (Render with Gunicorn)
- [x] Unit testing with pytest (60 tests)
- [x] Secure secret key via environment variables
- [x] CSRF protection (Flask-WTF)
- [x] Receipt scanning (OCR via Tesseract)
- [x] AI-powered spending predictions (scikit-learn)
- [x] Export expenses to CSV
- [x] Export expenses to PDF
- [ ] Email notifications for budget alerts

---

## License

This project was developed as part of a university Digital Solutions Project (DSP).

---

## Author

**Adeeb Imam**  
Computer Science — Year 3
