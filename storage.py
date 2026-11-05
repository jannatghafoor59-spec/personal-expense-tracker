
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "expenses.json"


def load_data():
    """Load saved expenses and budgets."""
    if not DATA_FILE.exists():
        return {"expenses": [], "budgets": {}}

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise RuntimeError(
            "The data file is damaged. Please check expenses.json."
        ) from error

    if not isinstance(data, dict):
        raise RuntimeError("Invalid data file structure.")

    if not isinstance(data.get("expenses"), list):
        raise RuntimeError("Invalid expenses data.")

    if not isinstance(data.get("budgets"), dict):
        raise RuntimeError("Invalid budgets data.")

    return data


def save_data(data):
    """Save expenses and budgets."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = DATA_DIR / "expenses.tmp"

    try:
        with temp_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        temp_file.replace(DATA_FILE)
    except OSError as error:
        raise RuntimeError("Could not save the data.") from error
