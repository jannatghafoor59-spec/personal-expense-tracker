
import os
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import (
    Flask, request, redirect, url_for,
    flash, render_template_string
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)

from models import db, User, Expense, Budget


app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "change-this-secret-before-deployment"
)

database_url = os.environ.get("DATABASE_URL")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://", "postgresql://", 1
        
    )

app.config["SQLALCHEMY_DATABASE_URI"] = (
    database_url or "sqlite:///expense_tracker.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to continue."


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


with app.app_context():
    db.create_all()


def money(value):
    return f"{Decimal(str(value)):.2f}"


def get_amount(value):
    try:
        amount = Decimal(value)
        if not amount.is_finite() or amount <= 0:
            return None
        return amount
    except (InvalidOperation, ValueError, TypeError):
        return None


def valid_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def dashboard_data(expenses=None):
    today = date.today()
    month = today.strftime("%Y-%m")

    all_expenses = Expense.query.filter_by(
        user_id=current_user.id
    ).all()

    if expenses is None:
        expenses = all_expenses

    total = sum(
        (Decimal(str(e.amount)) for e in expenses),
        Decimal("0")
    )

    monthly_expenses = [
        e for e in all_expenses if e.date.startswith(month)
    ]

    monday = today - timedelta(days=today.weekday())
    weekly_expenses = [
        e for e in all_expenses
        if valid_date(e.date)
        and monday <= datetime.strptime(e.date, "%Y-%m-%d").date() <= today
    ]

    monthly_total = sum(
        (Decimal(str(e.amount)) for e in monthly_expenses),
        Decimal("0")
    )

    weekly_total = sum(
        (Decimal(str(e.amount)) for e in weekly_expenses),
        Decimal("0")
    )

    budget_record = Budget.query.filter_by(
        user_id=current_user.id,
        month=month
    ).first()

    budget_amount = (
        Decimal(str(budget_record.amount))
        if budget_record else Decimal("0")
    )

    remaining = budget_amount - monthly_total
    percentage = (
        float(monthly_total / budget_amount * 100)
        if budget_amount > 0 else 0
    )

    if budget_amount == 0:
        status = "No budget set"
    elif remaining < 0:
        status = "Budget exceeded"
    else:
        status = "Within budget"

    category_totals = {}

    for expense in expenses:
        category_totals[expense.category] = (
            category_totals.get(expense.category, 0)
            + float(expense.amount)
        )

    return {
        "expenses": expenses,
        "total": total,
        "monthly_total": monthly_total,
        "weekly_total": weekly_total,
        "budget_amount": budget_amount,
        "remaining": remaining,
        "percentage": percentage,
        "status": status,
        "month": month,
        "today": today.isoformat(),
        "chart_labels": list(category_totals.keys()),
        "chart_values": list(category_totals.values())
    }


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if len(username) < 3 or len(username) > 80:
            flash("Username must be between 3 and 80 characters.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:
            flash("This username is already registered.")
            return redirect(url_for("register"))

        user = User(username=username)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Account created successfully! Please log in.")
        return redirect(url_for("login"))

    return render_template_string(AUTH_PAGE, heading="Create Account",
                                  action="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Welcome back!")
            return redirect(url_for("home"))

        flash("Incorrect username or password.")

    return render_template_string(AUTH_PAGE, heading="Login",
                                  action="login")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have logged out.")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    return render_template_string(
        PAGE, **dashboard_data(), money=money
    )


@app.route("/add", methods=["POST"])
@login_required
def add():
    expense_date = request.form.get("date", "")
    amount = get_amount(request.form.get("amount", ""))
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()

    if not valid_date(expense_date) or amount is None:
        flash("Please enter a valid date and positive amount.")
        return redirect(url_for("home"))

    if not category or not description:
        flash("Category and description are required.")
        return redirect(url_for("home"))

    expense = Expense(
        user_id=current_user.id,
        date=expense_date,
        amount=float(amount),
        category=category[:50],
        description=description[:200]
    )

    db.session.add(expense)
    db.session.commit()

    flash("Expense added successfully!")
    return redirect(url_for("home"))


@app.route("/edit/<int:expense_id>", methods=["POST"])
@login_required
def edit(expense_id):
    expense = Expense.query.filter_by(
        id=expense_id,
        user_id=current_user.id
    ).first_or_404()

    expense_date = request.form.get("date", "")
    amount = get_amount(request.form.get("amount", ""))
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()

    if not valid_date(expense_date) or amount is None:
        flash("Please enter a valid date and positive amount.")
        return redirect(url_for("home"))

    if not category or not description:
        flash("Category and description are required.")
        return redirect(url_for("home"))

    expense.date = expense_date
    expense.amount = float(amount)
    expense.category = category[:50]
    expense.description = description[:200]

    db.session.commit()
    flash("Expense updated successfully!")

    return redirect(url_for("home"))


@app.route("/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete(expense_id):
    expense = Expense.query.filter_by(
        id=expense_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(expense)
    db.session.commit()

    flash("Expense deleted successfully!")
    return redirect(url_for("home"))


@app.route("/budget", methods=["POST"])
@login_required
def set_budget():
    month = request.form.get("month", "")
    amount = get_amount(request.form.get("amount", ""))

    try:
        datetime.strptime(month, "%Y-%m")
    except (ValueError, TypeError):
        flash("Please select a valid month.")
        return redirect(url_for("home"))

    if amount is None:
        flash("Please enter a budget greater than zero.")
        return redirect(url_for("home"))

    budget = Budget.query.filter_by(
        user_id=current_user.id,
        month=month
    ).first()

    if budget:
        budget.amount = float(amount)
    else:
        budget = Budget(
            user_id=current_user.id,
            month=month,
            amount=float(amount)
        )
        db.session.add(budget)

    db.session.commit()
    flash("Monthly budget saved successfully!")

    return redirect(url_for("home"))


@app.route("/filter")
@login_required
def filter_expenses():
    query = Expense.query.filter_by(user_id=current_user.id)

    category = request.args.get("category", "").strip()
    month = request.args.get("month", "").strip()

    if category:
        query = query.filter(Expense.category.ilike(f"%{category}%"))

    if month:
        try:
            datetime.strptime(month, "%Y-%m")
            query = query.filter(Expense.date.startswith(month))
        except ValueError:
            flash("Invalid month selected.")

    expenses = query.order_by(Expense.date.desc()).all()

    return render_template_string(
        PAGE, **dashboard_data(expenses), money=money
    )


AUTH_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>{{ heading }} - Expense Tracker</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {
    background: #f4f5fa;
    font-family: Arial, sans-serif;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    margin: 0;
}
.card {
    background: white;
    padding: 35px;
    border-radius: 14px;
    width: 320px;
    max-width: 85%;
    box-shadow: 0 3px 15px #00000012;
}
h2 { color: #29264b; }
input {
    width: 100%;
    padding: 12px;
    margin: 9px 0 17px;
    border: 1px solid #ddd;
    border-radius: 7px;
    box-sizing: border-box;
}
button {
    width: 100%;
    padding: 12px;
    background: #6555c7;
    color: white;
    border: 0;
    border-radius: 7px;
    cursor: pointer;
}
a { color: #6555c7; }
.notice {
    padding: 10px;
    background: #e8f6ed;
    margin-bottom: 10px;
    border-radius: 7px;
}
</style>
</head>
<body>
<div class="card">
<h2>💰 {{ heading }}</h2>
{% for message in get_flashed_messages() %}
<div class="notice">{{ message }}</div>
{% endfor %}
<form method="POST">
<label>Username</label>
<input name="username" required minlength="3" maxlength="80"
       autocomplete="username">
<label>Password</label>
<input type="password" name="password" required
       autocomplete="new-password" minlength="8">
<button type="submit">{{ heading }}</button>
</form>
{% if action == "register" %}
<p>Already have an account? <a href="{{ url_for('login') }}">Login</a></p>
{% else %}
<p>New user? <a href="{{ url_for('register') }}">Create account</a></p>
{% endif %}
</div>
</body>
</html>
"""


PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>Personal Expense Tracker</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    background: #f4f5fa;
    font-family: Arial, sans-serif;
    color: #25263a;
}
header {
    background: #29264b;
    color: white;
    padding: 23px 7%;
    font-size: 21px;
    font-weight: bold;
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
}
header a { color: white; font-size: 14px; }
.container {
    max-width: 1150px;
    margin: 30px auto;
    padding: 0 18px;
}
.cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 17px;
}
.card {
    background: white;
    padding: 23px;
    border-radius: 13px;
    box-shadow: 0 3px 12px #0000000b;
}
.card p { color: #777; margin: 0 0 12px; }
.card h2 { margin: 0; color: #29264b; font-size: 25px; }
.layout {
    display: grid;
    grid-template-columns: 1fr 1.5fr;
    gap: 20px;
    margin-top: 23px;
}
h3 { margin-top: 0; color: #29264b; }
input {
    width: 100%;
    padding: 11px;
    margin: 7px 0 13px;
    border: 1px solid #ddd;
    border-radius: 7px;
}
button {
    background: #6555c7;
    color: white;
    border: 0;
    padding: 11px 16px;
    border-radius: 7px;
    cursor: pointer;
}
button:hover { background: #493ba7; }
.danger { background: #d94e5b; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td {
    padding: 12px 8px;
    text-align: left;
    border-bottom: 1px solid #eee;
}
th { color: #777; }
.notice {
    padding: 12px;
    background: #e8f6ed;
    color: #24733f;
    border-radius: 7px;
    margin-bottom: 15px;
}
.small { font-size: 12px; color: #777; }
.status { font-weight: bold; color: #27834a; }
.actions { display: flex; gap: 5px; flex-wrap: wrap; }
.chart-container { max-width: 550px; height: 320px; margin: auto; }
@media(max-width: 750px) {
    .layout { grid-template-columns: 1fr; }
    .container { margin: 15px auto; }
    table { font-size: 11px; }
}
</style>
</head>
<body>
<header>
<span>💰 Personal Expense Tracker</span>
<span>Welcome, {{ current_user.username }} |
<a href="{{ url_for('logout') }}">Logout</a></span>
</header>

<div class="container">
{% for message in get_flashed_messages() %}
<div class="notice">{{ message }}</div>
{% endfor %}

<h2>Dashboard</h2>
<p class="small">Manage your private daily expenses.</p>

<div class="cards">
<div class="card"><p>All Expenses</p><h2>Rs. {{ money(total) }}</h2></div>
<div class="card"><p>Monthly Spending</p><h2>Rs. {{ money(monthly_total) }}</h2></div>
<div class="card"><p>Weekly Spending</p><h2>Rs. {{ money(weekly_total) }}</h2></div>
<div class="card"><p>Remaining Budget</p><h2>Rs. {{ money(remaining) }}</h2></div>
</div>

<div class="card" style="margin-top:23px;">
<h3>🥧 Expense Distribution</h3>
<div class="chart-container"><canvas id="expensePieChart"></canvas></div>
</div>

<div class="layout">
<div class="card">
<h3>➕ Add New Expense</h3>
<form action="{{ url_for('add') }}" method="POST">
<label>Date</label>
<input type="date" name="date" value="{{ today }}" required>
<label>Amount (Rs.)</label>
<input type="number" name="amount" min="0.01" step="0.01" placeholder="500" required>
<label>Category</label>
<input type="text" name="category" placeholder="Food, Transport..." required>
<label>Description</label>
<input type="text" name="description" placeholder="Lunch..." required>
<button type="submit">Save Expense</button>
</form>

<hr>
<h3>🎯 Monthly Budget</h3>
<form action="{{ url_for('set_budget') }}" method="POST">
<label>Month</label>
<input type="month" name="month" value="{{ month }}" required>
<label>Budget (Rs.)</label>
<input type="number" name="amount" min="0.01" step="0.01" placeholder="5000" required>
<button type="submit">Set Budget</button>
</form>
<p class="small">Budget status: <span class="status">{{ status }}</span></p>
<p class="small">Budget used: {{ "%.1f"|format(percentage) }}%</p>
</div>

<div class="card">
<h3>📊 Expense History</h3>
<form action="{{ url_for('filter_expenses') }}" method="GET">
<label>Search by category</label>
<input type="text" name="category" placeholder="Food">
<label>Filter by month</label>
<input type="month" name="month">
<button type="submit">Search / Filter</button>
<a href="{{ url_for('home') }}" style="margin-left:10px;">Clear</a>
</form>

<div style="overflow-x:auto;">
<table>
<thead>
<tr><th>Date</th><th>Category</th><th>Amount</th><th>Description</th><th>Action</th></tr>
</thead>
<tbody>
{% for e in expenses %}
<tr>
<td>{{ e.date }}</td>
<td>{{ e.category }}</td>
<td>Rs. {{ money(e.amount) }}</td>
<td>{{ e.description }}</td>
<td>
<div class="actions">
<details>
<summary style="cursor:pointer;color:#6555c7;">Edit</summary>
<form action="{{ url_for('edit', expense_id=e.id) }}" method="POST">
<input type="date" name="date" value="{{ e.date }}" required>
<input type="number" name="amount" step="0.01" min="0.01" value="{{ e.amount }}" required>
<input type="text" name="category" value="{{ e.category }}" required>
<input type="text" name="description" value="{{ e.description }}" required>
<button type="submit">Update</button>
</form>
</details>
<form action="{{ url_for('delete', expense_id=e.id) }}" method="POST"
onsubmit="return confirm('Delete this expense?')">
<button class="danger" type="submit">Delete</button>
</form>
</div>
</td>
</tr>
{% else %}
<tr><td colspan="5">No expenses found.</td></tr>
{% endfor %}
</tbody>
</table>
</div>
</div>
</div>

<p class="small" style="text-align:center;margin:30px;">
Personal Expense Tracker | Python + Flask
</p>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const labels = {{ chart_labels | tojson }};
const values = {{ chart_values | tojson }};

if (labels.length > 0) {
    new Chart(document.getElementById('expensePieChart'), {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    '#6555c7', '#36A2EB', '#FFCE56',
                    '#FF6384', '#4BC0C0', '#9966FF', '#FF9F40'
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom' } }
        }
    });
} else {
    document.getElementById('expensePieChart').outerHTML =
        '<p>No expenses available for chart.</p>';
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
