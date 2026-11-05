
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import analytics
import storage
import tracker


def get_text(prompt):
    return input(prompt).strip()


def get_date():
    value = get_text(
        f"Date (YYYY-MM-DD, Enter for today {date.today()}): "
    )

    if not value:
        return date.today().isoformat()

    return value


def display_expenses(expenses):
    if not expenses:
        print("\nNo expenses found.")
        return

    print("\n" + "-" * 85)
    print(
        f"{'ID':10} {'Date':12} {'Amount':12} "
        f"{'Category':18} Description"
    )
    print("-" * 85)

    for item in expenses:
        print(
            f"{item['id'][:10]:10} "
            f"{item['date']:12} "
            f"Rs. {item['amount']:>8} "
            f"{item['category'][:18]:18} "
            f"{item['description']}"
        )

    print("-" * 85)


def show_menu():
    print("""
========================================
       PERSONAL EXPENSE TRACKER
========================================
1. Add Expense
2. View All Expenses
3. Search / Filter Expenses
4. Edit Expense
5. Delete Expense
6. View Weekly Summary
7. View Monthly Summary
8. Set Monthly Budget
9. View Budget Status
10. Exit
========================================
""")


def add_expense(data):
    expense = tracker.add_expense(
        data,
        get_date(),
        get_text("Amount (Rs.): "),
        get_text("Category: "),
        get_text("Description: ")
    )

    storage.save_data(data)
    print(f"\nExpense saved successfully. ID: {expense['id']}")


def filter_expenses(data):
    print("\n1. Filter by category")
    print("2. Filter by month")
    print("3. Filter by date range")

    choice = get_text("Choose filter: ")

    if choice == "1":
        result = tracker.filter_by_category(
            data, get_text("Category: ")
        )
    elif choice == "2":
        result = tracker.filter_by_month(
            data, get_text("Month (YYYY-MM): ")
        )
    elif choice == "3":
        start = get_text("Start date (YYYY-MM-DD): ")
        end = get_text("End date (YYYY-MM-DD): ")
        result = tracker.filter_by_date_range(data, start, end)
    else:
        print("Invalid filter choice.")
        return

    display_expenses(result)
    print(f"Matching expenses: {len(result)}")


def edit_expense(data):
    expense_id = get_text("Enter expense ID to edit: ")
    expense = tracker.find_expense(data, expense_id)

    if expense is None:
        print("Expense not found.")
        return

    print("Press Enter to keep an existing value.")

    new_date = get_text(
        f"Date [{expense['date']}]: "
    ) or expense["date"]

    new_amount = get_text(
        f"Amount [{expense['amount']}]: "
    ) or expense["amount"]

    new_category = get_text(
        f"Category [{expense['category']}]: "
    ) or expense["category"]

    new_description = get_text(
        f"Description [{expense['description']}]: "
    ) or expense["description"]

    tracker.edit_expense(
        data, expense_id, new_date, new_amount,
        new_category, new_description
    )

    storage.save_data(data)
    print("Expense updated successfully.")


def delete_expense(data):
    expense_id = get_text("Enter expense ID to delete: ")

    if tracker.find_expense(data, expense_id) is None:
        print("Expense not found.")
        return

    confirm = get_text("Delete this expense? (y/n): ").lower()

    if confirm == "y":
        tracker.delete_expense(data, expense_id)
        storage.save_data(data)
        print("Expense deleted successfully.")
    else:
        print("Deletion cancelled.")


def show_weekly_summary(data):
    result = analytics.weekly_summary(data["expenses"])

    print(f"\nWeek: {result['start']} to {result['end']}")
    print(f"Transactions: {result['count']}")
    print(f"Total spending: Rs. {result['total']:.2f}")


def get_month():
    month = get_text("Month (YYYY-MM): ")
    datetime.strptime(month, "%Y-%m")
    return month


def show_monthly_summary(data):
    month = get_month()
    result = analytics.monthly_summary(data["expenses"], month)

    print(f"\nMonthly Summary: {month}")
    print(f"Transactions: {result['count']}")
    print(f"Total spending: Rs. {result['total']:.2f}")

    print("\nCategory Breakdown:")

    if result["categories"]:
        for category, amount in result["categories"].items():
            print(f"{category}: Rs. {amount:.2f}")
    else:
        print("No expenses for this month.")

    largest = analytics.highest_expense(
        tracker.filter_by_month(data, month)
    )

    if largest:
        print(
            f"Largest expense: {largest['description']} "
            f"(Rs. {largest['amount']})"
        )


def set_budget(data):
    month = get_month()
    amount = Decimal(get_text("Monthly budget (Rs.): "))

    if not amount.is_finite() or amount < 0:
        raise ValueError("Budget cannot be negative.")

    amount = amount.quantize(Decimal("0.01"))
    data["budgets"][month] = str(amount)

    storage.save_data(data)
    print(f"Budget for {month} set to Rs. {amount:.2f}")


def show_budget_status(data):
    month = get_month()

    result = analytics.budget_status(
        data["expenses"], data["budgets"], month
    )

    print(f"\nBudget Status: {month}")
    print(f"Budget: Rs. {result['budget']:.2f}")
    print(f"Spent: Rs. {result['spent']:.2f}")
    print(f"Remaining: Rs. {result['remaining']:.2f}")

    if result["percentage"] is not None:
        print(f"Budget used: {result['percentage']:.1f}%")

    print(f"Status: {result['status']}")


def run_app():
    data = storage.load_data()

    while True:
        show_menu()
        choice = get_text("Enter your choice (1-10): ")

        try:
            if choice == "1":
                add_expense(data)
            elif choice == "2":
                display_expenses(
                    tracker.get_all_expenses(data)
                )
            elif choice == "3":
                filter_expenses(data)
            elif choice == "4":
                edit_expense(data)
            elif choice == "5":
                delete_expense(data)
            elif choice == "6":
                show_weekly_summary(data)
            elif choice == "7":
                show_monthly_summary(data)
            elif choice == "8":
                set_budget(data)
            elif choice == "9":
                show_budget_status(data)
            elif choice == "10":
                print("Thank you for using Personal Expense Tracker!")
                break
            else:
                print("Invalid choice. Please enter a number from 1 to 10.")

        except (ValueError, InvalidOperation) as error:
            print(f"Input error: {error}")
        except RuntimeError as error:
            print(f"Storage error: {error}")
        except OSError as error:
            print(f"File error: {error}")

        input("\nPress Enter to return to the menu...")


if __name__ == "__main__":
    try:
        run_app()
    except RuntimeError as error:
        print(f"Application could not start: {error}")
    except (EOFError, KeyboardInterrupt):
        print("\nApplication closed.")
