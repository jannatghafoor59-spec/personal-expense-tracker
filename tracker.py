
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import uuid4


def validate_expense(date, amount, category, description):
    """Check that expense details are valid."""

    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Date must use YYYY-MM-DD format.")

    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, ValueError):
        raise ValueError("Please enter a valid amount.")

    if not amount.is_finite() or amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    amount = amount.quantize(Decimal("0.01"))

    if amount <= 0:
        raise ValueError("Amount must be at least 0.01.")

    category = category.strip()
    description = description.strip()

    if not category:
        raise ValueError("Category cannot be empty.")

    if not description:
        raise ValueError("Description cannot be empty.")

    return {
        "date": date,
        "amount": str(amount),
        "category": category,
        "description": description
    }


def add_expense(data, date, amount, category, description):
    expense = validate_expense(date, amount, category, description)
    expense["id"] = uuid4().hex[:8].upper()
    data["expenses"].append(expense)
    return expense


def get_all_expenses(data):
    return sorted(
        data["expenses"],
        key=lambda expense: (expense["date"], expense["id"]),
        reverse=True
    )


def find_expense(data, expense_id):
    for expense in data["expenses"]:
        if expense["id"].upper() == expense_id.strip().upper():
            return expense
    return None


def edit_expense(data, expense_id, date, amount, category, description):
    expense = find_expense(data, expense_id)

    if expense is None:
        return False

    updated = validate_expense(date, amount, category, description)
    expense.update(updated)
    return True


def delete_expense(data, expense_id):
    expense = find_expense(data, expense_id)

    if expense is None:
        return False

    data["expenses"].remove(expense)
    return True


def filter_by_category(data, category):
    return [
        expense for expense in get_all_expenses(data)
        if expense["category"].casefold() == category.strip().casefold()
    ]


def filter_by_month(data, month):
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise ValueError("Month must use YYYY-MM format.")

    return [
        expense for expense in get_all_expenses(data)
        if expense["date"].startswith(month)
    ]


def filter_by_date_range(data, start_date, end_date):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Dates must use YYYY-MM-DD format.")

    if start > end:
        raise ValueError("Start date cannot be after end date.")

    return [
        expense for expense in get_all_expenses(data)
        if start <= datetime.strptime(
            expense["date"], "%Y-%m-%d"
        ).date() <= end
    ]
