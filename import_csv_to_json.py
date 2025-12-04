"""
You only need to use this if you have your static org data in the required CSV format.
This will convert that CSV file into the correct JSON format and save it as employee_data.json.
IF YOU ALREADY HAVE AN EMPLOYEE_DATA.JSON FILE, BACK IT UP BEFORE RUNNING THIS.
"""

import csv
import json
import sys
import os
from collections import defaultdict

# Configuration
CSV_FILE = "employees.csv"          # Change this or pass as argument
OUTPUT_FILE = "employee_data.json"   # Must match what Flask app expects
ID_FIELD = "id"                      # Column name for unique ID
MANAGER_FIELD = "managerId"          # Column for manager's ID (empty for top)

def build_hierarchy(employees):
    """Build nested hierarchy from flat list of employees"""
    by_id = {}
    for emp in employees:
        emp_id = emp[ID_FIELD]
        emp["children"] = []
        by_id[emp_id] = emp

    root = None
    for emp in employees:
        manager_id = emp.get(MANAGER_FIELD)
        if not manager_id or manager_id not in by_id:
            if root is not None:
                print(f"Warning: Multiple potential roots found: {root['name']} and {emp['name']}")
            root = by_id[emp[ID_FIELD]]
        else:
            manager = by_id[manager_id]
            manager["children"].append(by_id[emp[ID_FIELD]])

    if root is None:
        raise ValueError("No root employee found! Make sure the top-level person has no managerId or an invalid one.")

    return root

def clean_value(value):
    """Clean empty strings, 'null', 'NULL', etc."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower() in ["", "null", "none", "n/a"]:
            return None
        return stripped
    return value

def get_file_info(path):
    """Get file size and existence info"""
    if os.path.exists(path):
        return f"exists (size: {os.path.getsize(path)} bytes)"
    return "does NOT exist"

def main(csv_path=None, output_path=None, force=False):
    csv_path = csv_path or CSV_FILE
    output_path = output_path or OUTPUT_FILE

    if not csv_path.endswith('.csv'):
        print("Please provide a .csv file")
        sys.exit(1)

    cwd = os.getcwd()
    print(f"Current working directory: {cwd}")
    print(f"CSV path: {os.path.abspath(csv_path)}")
    print(f"Output path: {os.path.abspath(output_path)}")
    print(f"Force overwrite: {force}")

    if force and os.path.exists(output_path):
        print(f"Force mode: Deleting existing {output_path}")
        os.remove(output_path)

    print(f"\nFile status BEFORE import:")
    print(f"  - {output_path}: {get_file_info(output_path)}")

    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)

    print(f"Reading employees from: {csv_path}")

    employees = []
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            expected_headers = {ID_FIELD, "name", MANAGER_FIELD}
            missing = expected_headers - set(reader.fieldnames or [])
            if missing:
                print(f"Error: Missing required columns: {missing}")
                print(f"Available columns: {list(reader.fieldnames)}")
                sys.exit(1)

            for row_num, row in enumerate(reader, start=2):
                if not row.get(ID_FIELD):
                    print(f"Warning: Row {row_num} has no ID, skipping")
                    continue
                if not row.get("name"):
                    print(f"Warning: Row {row_num} has no name, skipping")
                    continue

                emp = {
                    "id": str(row[ID_FIELD]).strip(),
                    "name": row["name"].strip(),
                    "title": clean_value(row.get("title", "")) or "Employee",
                    "department": clean_value(row.get("department", "")) or "Unassigned",
                    "email": clean_value(row.get("email")),
                    "phone": clean_value(row.get("phone")),
                    "location": clean_value(row.get("location")),
                    "managerId": clean_value(row.get(MANAGER_FIELD)),
                }
                employees.append(emp)

        print(f"Loaded {len(employees)} employees from CSV")

        root = build_hierarchy(employees)

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(root, f, indent=2, ensure_ascii=False)
            print(f"Write completed successfully.")
        except PermissionError as e:
            print(f"Permission denied writing to {output_path}: {e}")
            print("Try running as admin or check file locks.")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error writing file: {e}")
            sys.exit(1)

        print(f"Success: Org chart JSON saved to {output_path}")
        print(f"Root employee: {root['name']} ({root['title']})")

        print(f"\nFile status AFTER import:")
        print(f"  - {output_path}: {get_file_info(output_path)}")

        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Validation: Root ID={data['id']}, Name='{data['name']}', Children={len(data['children'])}")

    except FileNotFoundError:
        print(f"Error: File not found: {csv_path}")
        print("Make sure the CSV file exists and the path is correct.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    force = '--force' in sys.argv
    csv_arg = next((arg for arg in sys.argv if arg.endswith('.csv')), None)
    if csv_arg:
        main(csv_arg, force=force)
    else:
        main(force=force)