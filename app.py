from flask import Flask, render_template_string, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
import requests
import threading
import time
import schedule
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

if not os.path.exists('static'):
    os.makedirs('static')

GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
DATA_FILE = 'employee_data.json'


TENANT_ID = os.environ.get('AZURE_TENANT_ID')
CLIENT_ID = os.environ.get('AZURE_CLIENT_ID')
CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET')

# Validate required environment variables
if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
    logger.warning("Missing Azure AD credentials in environment variables!")
    logger.warning("AZURE_TENANT_ID: " + ("Set" if TENANT_ID else "Not set"))
    logger.warning("AZURE_CLIENT_ID: " + ("Set" if CLIENT_ID else "Not set"))
    logger.warning("AZURE_CLIENT_SECRET: " + ("Set" if CLIENT_SECRET else "Not set"))
    logger.warning("Please check your .env file exists and contains the correct values")

# Set this to the email or ID of your CEO/top-level person
TOP_LEVEL_USER_EMAIL = os.environ.get('TOP_LEVEL_USER_EMAIL')
TOP_LEVEL_USER_ID = os.environ.get('TOP_LEVEL_USER_ID')

scheduler_running = False
scheduler_lock = threading.Lock()

def get_access_token():
    token_url = f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token'
    
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': 'https://graph.microsoft.com/.default'
    }
    
    try:
        token_r = requests.post(token_url, data=token_data)
        token = token_r.json().get('access_token')
        return token
    except Exception as e:
        logger.error(f"Error getting access token: {e}")
        return None

def fetch_all_employees():
    token = get_access_token()
    if not token:
        logger.error("Failed to get access token")
        return []
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    employees = []
    users_url = f'{GRAPH_API_ENDPOINT}/users?$select=id,displayName,jobTitle,department,mail,mobilePhone,officeLocation&$expand=manager($select=id,displayName)'
    
    while users_url:
        try:
            response = requests.get(users_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if 'value' in data:
                for user in data['value']:
                    if user.get('displayName'):
                        employee = {
                            'id': user.get('id'),
                            'name': user.get('displayName'),
                            'title': user.get('jobTitle', 'No Title'),
                            'department': user.get('department', 'No Department'),
                            'email': user.get('mail'),
                            'phone': user.get('mobilePhone'),
                            'location': user.get('officeLocation'),
                            'managerId': user.get('manager', {}).get('id') if user.get('manager') else None,
                            'children': []
                        }
                        employees.append(employee)
            
            users_url = data.get('@odata.nextLink')
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching employees: {e}")
            if response.status_code == 401:
                logger.error("Authentication failed. Please check your credentials.")
            elif response.status_code == 403:
                logger.error("Permission denied. Ensure User.Read.All permission is granted.")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            break
    
    logger.info(f"Fetched {len(employees)} employees from Graph API")
    return employees

def build_org_hierarchy(employees):
    if not employees:
        return None
    
    emp_dict = {emp['id']: emp.copy() for emp in employees}
    
    for emp_id in emp_dict:
        if 'children' not in emp_dict[emp_id]:
            emp_dict[emp_id]['children'] = []
    
    root = None
    if TOP_LEVEL_USER_ID and TOP_LEVEL_USER_ID in emp_dict:
        root = emp_dict[TOP_LEVEL_USER_ID]
        logger.info(f"Using configured top-level user by ID: {root['name']}")
    elif TOP_LEVEL_USER_EMAIL:
        for emp in employees:
            if emp.get('email') == TOP_LEVEL_USER_EMAIL:
                root = emp_dict[emp['id']]
                logger.info(f"Using configured top-level user by email: {root['name']}")
                break
    
    root_candidates = []
    
    for emp in employees:
        emp_copy = emp_dict[emp['id']]
        if emp['managerId'] and emp['managerId'] in emp_dict:
            manager = emp_dict[emp['managerId']]
            if emp_copy not in manager['children']:
                manager['children'].append(emp_copy)
        else:
            if not emp['managerId'] and emp_copy not in root_candidates:
                root_candidates.append(emp_copy)
    
    if not root:
        if root_candidates:
            ceo_keywords = ['chief executive', 'ceo', 'president', 'chair', 'director', 'head']
            for candidate in root_candidates:
                title_lower = (candidate.get('title') or '').lower()
                if any(keyword in title_lower for keyword in ceo_keywords):
                    root = candidate
                    logger.info(f"Auto-detected top-level user: {root['name']} - {root.get('title')}")
                    break
            
            if not root and root_candidates:
                root = root_candidates[0]
                logger.info(f"Using first root candidate as top-level: {root['name']}")
        else:
            max_reports = 0
            for emp_id, emp in emp_dict.items():
                if len(emp['children']) > max_reports:
                    max_reports = len(emp['children'])
                    root = emp
            
            if root:
                logger.info(f"Using person with most reports as top-level: {root['name']} ({max_reports} reports)")
    
    if not root and employees:
        root = emp_dict[employees[0]['id']]
        logger.info(f"Using first employee as root: {root['name']}")
    
    return root

def update_employee_data():
    try:
        logger.info(f"[{datetime.now()}] Starting employee data update...")
        employees = fetch_all_employees()
        
        if employees:
            hierarchy = build_org_hierarchy(employees)
            
            if hierarchy:
                with open(DATA_FILE, 'w') as f:
                    json.dump(hierarchy, f, indent=2)
                logger.info(f"[{datetime.now()}] Successfully updated employee data. Total employees: {len(employees)}")
            else:
                logger.error(f"[{datetime.now()}] Could not build hierarchy from employee data")
        else:
            logger.error(f"[{datetime.now()}] No employees fetched from Graph API")
    except Exception as e:
        logger.error(f"[{datetime.now()}] Error updating employee data: {e}")

def schedule_updates():
    global scheduler_running
    
    # Run initial update on startup if enabled
    if os.environ.get('RUN_INITIAL_UPDATE', 'true').lower() == 'true':
        logger.info(f"[{datetime.now()}] Running initial employee data update on startup...")
        update_employee_data()
    
    # This sets the update time each day. Change the value below to amend the update time each day.
    schedule.every().day.at("20:00").do(update_employee_data)
    
    while scheduler_running:
        schedule.run_pending()
        time.sleep(60)

def start_scheduler():
    global scheduler_running
    with scheduler_lock:
        if not scheduler_running:
            scheduler_running = True
            scheduler_thread = threading.Thread(target=schedule_updates, daemon=True)
            scheduler_thread.start()
            logger.info("Scheduler started")

def stop_scheduler():
    global scheduler_running
    with scheduler_lock:
        scheduler_running = False
        logger.info("Scheduler stopped")

# Read the HTML template from the file
def get_index_html():
    # Try multiple locations for the template
    possible_paths = [
        'templates/index.html',  # Standard Flask location
        'index.html',            # Root directory
        os.path.join(os.path.dirname(__file__), 'templates', 'index.html'),  # Absolute path
        os.path.join(os.path.dirname(__file__), 'index.html')  # Absolute path in root
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    logger.info(f"Loading template from: {path}")
                    return f.read()
            except Exception as e:
                logger.error(f"Error reading {path}: {e}")
    
    logger.error("index.html not found in any expected location")
    return "<h1>Error: index.html not found</h1><p>Looked in: templates/index.html and ./index.html</p>"

@app.route('/')
def index():
    return render_template_string(get_index_html())

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/api/employees')
def get_employees():
    try:
        if not os.path.exists(DATA_FILE):
            update_employee_data()
        
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        if not data:
            logger.warning("No hierarchical data available")
            employees = fetch_all_employees()
            if employees:
                data = {
                    'id': 'root',
                    'name': 'Organization',
                    'title': 'All Employees',
                    'department': '',
                    'email': '',
                    'phone': '',
                    'location': '',
                    'children': employees
                }
            else:
                data = {
                    'id': 'root',
                    'name': 'No Data',
                    'title': 'Please check configuration',
                    'children': []
                }
        
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error in get_employees: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search')
def search_employees():
    query = request.args.get('q', '').lower()
    
    if len(query) < 2:
        return jsonify([])
    
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        def flatten(node, results=None):
            if results is None:
                results = []
            results.append(node)
            for child in node.get('children', []):
                flatten(child, results)
            return results
        
        all_employees = flatten(data)
        
        results = [
            emp for emp in all_employees
            if query in emp.get('name', '').lower() or
               query in emp.get('title', '').lower() or
               query in emp.get('department', '').lower()
        ]
        
        return jsonify(results[:10])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/employee/<employee_id>')
def get_employee(employee_id):
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        def find_employee(node, target_id):
            if node.get('id') == target_id:
                return node
            for child in node.get('children', []):
                result = find_employee(child, target_id)
                if result:
                    return result
            return None
        
        employee = find_employee(data, employee_id)
        
        if employee:
            return jsonify(employee)
        else:
            return jsonify({'error': 'Employee not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-now', methods=['POST'])
def trigger_update():
    try:
        threading.Thread(target=update_employee_data).start()
        return jsonify({'message': 'Update started'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug')
def debug_data():
    try:
        employees = fetch_all_employees()
        hierarchy = build_org_hierarchy(employees)
        
        return jsonify({
            'total_employees': len(employees),
            'raw_employees': employees,
            'hierarchy': hierarchy,
            'has_managers': any(emp.get('managerId') for emp in employees)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Initialize scheduler when module is imported (for Gunicorn)
if __name__ != '__main__':
    start_scheduler()

# For development server
if __name__ == '__main__':
    start_scheduler()
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        stop_scheduler()