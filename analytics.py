
from datetime import date, datetime, timedelta
from decimal import Decimal


def calculate_total(expenses):
    return sum(
        (Decimal(item["amount"]) for item in expenses),
        Decimal("0.00")
    )


def monthly_summary(expenses, month):
    selected = [
        item for item in expenses
        if item["date"].startswith(month)
    ]

    return {
        "month": month,
        "total": calculate_total(selected),
        "count": len(selected),
        "categories": category_summary(selected)
    }


def weekly_summary(expenses, selected_date=None):
    if selected_date is None:
        selected_date = date.today()

    if isinstance(selected_date, str):
        selected_date = datetime.strptime(
            selected_date, "%Y-%m-%d"
        ).date()

    monday = selected_date - timedelta(
        days=selected_date.weekday()
    )
    next_monday = monday + timedelta(days=7)

    selected = [
        item for item in expenses
        if monday <= datetime.strptime(
            item["date"], "%Y-%m-%d"
        ).date() < next_monday
    ]

    return {
        "start": monday,
        "end": next_monday - timedelta(days=1),
        "total": calculate_total(selected),
        "count": len(selected)
    }


def category_summary(expenses):
    summary = {}

    for item in expenses:
        category = item["category"]
        amount = Decimal(item["amount"])

        summary[category] = (
            summary.get(category, Decimal("0.00")) + amount
        )

    return summary


def highest_expense(expenses):
    if not expenses:
        return None

    return max(
        expenses,
        key=lambda item: Decimal(item["amount"])
    )


def budget_status(expenses, budgets, month):
    budget = Decimal(budgets.get(month, "0.00"))

    monthly_expenses = [
        item for item in expenses
        if item["date"].startswith(month)
    ]

    spent = calculate_total(monthly_expenses)
    remaining = budget - spent

    if budget == 0:
        percentage = None
        status = "No budget set"
    else:
        percentage = spent / budget * 100

        if spent > budget:
            status = "Over budget"
        elif percentage >= 80:
            status = "Budget nearly exhausted"
        else:
            status = "Within budget"

    return {
        "month": month,
        "budget": budget,
        "spent": spent,
        "remaining": remaining,
        "percentage": percentage,
        "status": status
    }
