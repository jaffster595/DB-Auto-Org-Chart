from flask import Flask, render_template_string, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
import requests
import threading
import time
import schedule
import logging
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import shutil

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

if not os.path.exists('static'):
    os.makedirs('static')

GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
DATA_FILE = 'employee_data.json'
SETTINGS_FILE = 'app_settings.json'

# Configuration for file uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
MAX_FILE_SIZE = 5 * 1024 * 1024

TENANT_ID = os.environ.get('AZURE_TENANT_ID')
CLIENT_ID = os.environ.get('AZURE_CLIENT_ID')
CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET')

if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
    logger.warning("Missing Azure AD credentials in environment variables!")
    logger.warning("AZURE_TENANT_ID: " + ("Set" if TENANT_ID else "Not set"))
    logger.warning("AZURE_CLIENT_ID: " + ("Set" if CLIENT_ID else "Not set"))
    logger.warning("AZURE_CLIENT_SECRET: " + ("Set" if CLIENT_SECRET else "Not set"))
    logger.warning("Please check your .env file exists and contains the correct values")

TOP_LEVEL_USER_EMAIL = os.environ.get('TOP_LEVEL_USER_EMAIL')
TOP_LEVEL_USER_ID = os.environ.get('TOP_LEVEL_USER_ID')

scheduler_running = False
scheduler_lock = threading.Lock()

# Default settings
DEFAULT_SETTINGS = {
    'chartTitle': 'DB Auto Org Chart',
    'headerColor': '#0078d4',
    'logoPath': '/static/icon.png',
    'nodeColors': {
        'level0': '#90EE90',
        'level1': '#FFFFE0',
        'level2': '#E0F2FF',
        'level3': '#FFE4E1',
        'level4': '#E8DFF5',
        'level5': '#FFEAA7'
    },
    'autoUpdateEnabled': True,
    'updateTime': '20:00',
    'collapseLevel': '2',
    'searchAutoExpand': True,
    'searchHighlight': True,
    'showDepartments': True,
    'showEmployeeCount': True,
    'showProfileImages': True,
    'printOrientation': 'landscape',
    'printSize': 'a4',
    'topUserEmail': TOP_LEVEL_USER_EMAIL or '',
    'highlightNewEmployees': True,
    'newEmployeeMonths': 3
}

def load_settings():
    """Load settings from file or return defaults"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                for key in DEFAULT_SETTINGS:
                    if key not in settings:
                        settings[key] = DEFAULT_SETTINGS[key]
                return settings
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Save settings to file"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    users_url = f'{GRAPH_API_ENDPOINT}/users?$select=id,displayName,jobTitle,department,mail,mobilePhone,officeLocation,employeeHireDate&$expand=manager($select=id,displayName)'
    
    while users_url:
        try:
            response = requests.get(users_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if 'value' in data:
                for user in data['value']:
                    if user.get('displayName'):
                        hire_date_str = user.get('employeeHireDate')
                        is_new = False
                        hire_date = None
                        
                        if hire_date_str:
                            try:
                                if 'T' in hire_date_str:
                                    hire_date = datetime.fromisoformat(hire_date_str.replace('Z', '+00:00'))
                                else:
                                    hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d')
                                    hire_date = hire_date.replace(tzinfo=None)
                                
                                settings = load_settings()
                                months_threshold = settings.get('newEmployeeMonths', 3)
                                
                                if hire_date.tzinfo:
                                    cutoff_date = datetime.now(hire_date.tzinfo) - timedelta(days=months_threshold * 30)
                                else:
                                    cutoff_date = datetime.now() - timedelta(days=months_threshold * 30)
                                
                                is_new = hire_date > cutoff_date
                            except Exception as e:
                                logger.warning(f"Error parsing hire date for user {user.get('displayName')}: {e}")
                        
                        employee = {
                            'id': user.get('id'),
                            'name': user.get('displayName') or 'Unknown',
                            'title': user.get('jobTitle') or 'No Title',
                            'department': user.get('department') or 'No Department',
                            'email': user.get('mail') or '',
                            'phone': user.get('mobilePhone') or '',
                            'location': user.get('officeLocation') or '',
                            'managerId': user.get('manager', {}).get('id') if user.get('manager') else None,
                            'employeeHireDate': hire_date_str,
                            'hireDate': hire_date.isoformat() if hire_date else None,
                            'isNewEmployee': is_new,
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
    
    settings = load_settings()
    top_user_email = settings.get('topUserEmail') or TOP_LEVEL_USER_EMAIL
    
    emp_dict = {emp['id']: emp.copy() for emp in employees}
    
    for emp_id in emp_dict:
        if 'children' not in emp_dict[emp_id]:
            emp_dict[emp_id]['children'] = []
    
    root = None
    if TOP_LEVEL_USER_ID and TOP_LEVEL_USER_ID in emp_dict:
        root = emp_dict[TOP_LEVEL_USER_ID]
        logger.info(f"Using configured top-level user by ID: {root['name']}")
    elif top_user_email:
        for emp in employees:
            if emp.get('email') == top_user_email:
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
                settings = load_settings()
                months_threshold = settings.get('newEmployeeMonths', 3)
                
                def update_new_status(node):
                    if node.get('hireDate'):
                        try:
                            hire_date = datetime.fromisoformat(node['hireDate'])
                            if hire_date.tzinfo:
                                cutoff_date = datetime.now(hire_date.tzinfo) - timedelta(days=months_threshold * 30)
                            else:
                                cutoff_date = datetime.now() - timedelta(days=months_threshold * 30)
                            node['isNewEmployee'] = hire_date > cutoff_date
                        except:
                            node['isNewEmployee'] = False
                    else:
                        node['isNewEmployee'] = False
                    
                    if node.get('children'):
                        for child in node['children']:
                            update_new_status(child)
                
                update_new_status(hierarchy)
                
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
    
    settings = load_settings()
    
    if os.environ.get('RUN_INITIAL_UPDATE', 'true').lower() == 'true':
        logger.info(f"[{datetime.now()}] Running initial employee data update on startup...")
        update_employee_data()
    
    if settings.get('autoUpdateEnabled', True):
        update_time = settings.get('updateTime', '20:00')
        schedule.every().day.at(update_time).do(update_employee_data)
        logger.info(f"Scheduled daily updates at {update_time}")
    
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

def restart_scheduler():
    """Restart scheduler with new settings"""
    stop_scheduler()
    time.sleep(2)
    schedule.clear()
    start_scheduler()

def get_template(template_name):
    """Load HTML template from file"""
    possible_paths = [
        f'templates/{template_name}',
        template_name,
        os.path.join(os.path.dirname(__file__), 'templates', template_name),
        os.path.join(os.path.dirname(__file__), template_name)
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    logger.info(f"Loading template from: {path}")
                    return f.read()
            except Exception as e:
                logger.error(f"Error reading {path}: {e}")
    
    logger.error(f"{template_name} not found in any expected location")
    return f"<h1>Error: {template_name} not found</h1>"

@app.route('/')
def index():
    return render_template_string(get_template('index.html'))

@app.route('/configure')
def configure():
    return render_template_string(get_template('configureme.html'))

@app.route('/static/<path:filename>')
def serve_static(filename):
    if filename == 'icon.png':
        custom_logo = os.path.join('static', 'icon_custom.png')
        if os.path.exists(custom_logo):
            return send_from_directory('static', 'icon_custom.png')
    return send_from_directory('static', filename)

@app.route('/api/employees')
def get_employees():
    try:
        if not os.path.exists(DATA_FILE):
            update_employee_data()
        
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        if data:
            settings = load_settings()
            months_threshold = settings.get('newEmployeeMonths', 3)
            
            def update_new_status(node):
                if node.get('hireDate'):
                    try:
                        hire_date = datetime.fromisoformat(node['hireDate'])
                        if hire_date.tzinfo:
                            cutoff_date = datetime.now(hire_date.tzinfo) - timedelta(days=months_threshold * 30)
                        else:
                            cutoff_date = datetime.now() - timedelta(days=months_threshold * 30)
                        node['isNewEmployee'] = hire_date > cutoff_date
                    except:
                        node['isNewEmployee'] = False
                else:
                    node['isNewEmployee'] = False
                
                if node.get('children'):
                    for child in node['children']:
                        update_new_status(child)
            
            update_new_status(data)
        
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

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'GET':
        settings = load_settings()
        return jsonify(settings)
    
    elif request.method == 'POST':
        try:
            new_settings = request.json
            current_settings = load_settings()
            
            current_settings.update(new_settings)
            
            if save_settings(current_settings):
                if ('updateTime' in new_settings or 'autoUpdateEnabled' in new_settings):
                    threading.Thread(target=restart_scheduler).start()
                
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Failed to save settings'}), 500
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return jsonify({'error': str(e)}), 500

@app.route('/api/upload-logo', methods=['POST'])
def upload_logo():
    try:
        if 'logo' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['logo']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            custom_logo_path = os.path.join('static', 'icon_custom.png')
            file.save(custom_logo_path)
            settings = load_settings()
            settings['logoPath'] = '/static/icon.png'
            save_settings(settings)
            
            return jsonify({'success': True, 'path': '/static/icon.png'})
        else:
            return jsonify({'error': 'Invalid file type'}), 400
    except Exception as e:
        logger.error(f"Error uploading logo: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset-logo', methods=['POST'])
def reset_logo():
    try:
        custom_logo_path = os.path.join('static', 'icon_custom.png')
        if os.path.exists(custom_logo_path):
            os.remove(custom_logo_path)
        
        settings = load_settings()
        settings['logoPath'] = '/static/icon.png'
        save_settings(settings)
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error resetting logo: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset-all-settings', methods=['POST'])
def reset_all_settings():
    try:
        custom_logo_path = os.path.join('static', 'icon_custom.png')
        if os.path.exists(custom_logo_path):
            os.remove(custom_logo_path)
        
        save_settings(DEFAULT_SETTINGS)
        
        threading.Thread(target=restart_scheduler).start()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error resetting all settings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search')
def search_employees():
    query = request.args.get('q', '').lower()
    
    if len(query) < 2:
        return jsonify([])
    
    try:
        if not os.path.exists(DATA_FILE):
            logger.warning(f"Data file {DATA_FILE} not found, attempting to fetch data")
            update_employee_data()
        
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
        else:
            logger.error("Could not create or find employee data file")
            return jsonify([])
        
        def flatten(node, results=None):
            if results is None:
                results = []
            if node and isinstance(node, dict):
                results.append(node)
                children = node.get('children', [])
                if children and isinstance(children, list):
                    for child in children:
                        flatten(child, results)
            return results
        
        all_employees = flatten(data)
        
        results = []
        for emp in all_employees:
            if emp and isinstance(emp, dict):
                name = emp.get('name') or ''
                title = emp.get('title') or ''
                department = emp.get('department') or ''
                
                name_match = query in name.lower()
                title_match = query in title.lower()
                dept_match = query in department.lower()
                
                if name_match or title_match or dept_match:
                    results.append(emp)
        
        return jsonify(results[:10])
    except FileNotFoundError as e:
        logger.error(f"File not found in search: {e}")
        return jsonify([])
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in search: {e}")
        return jsonify([])
    except AttributeError as e:
        logger.error(f"Attribute error in search (likely None value): {e}")
        logger.error(f"Query was: {query}")
        try:
            for emp in all_employees:
                if emp:
                    logger.debug(f"Employee data: name={emp.get('name')}, title={emp.get('title')}, dept={emp.get('department')}")
        except:
            pass
        return jsonify([])
    except Exception as e:
        logger.error(f"Error in search_employees: {e}")
        logger.error(f"Query was: {query}")
        import traceback
        logger.error(traceback.format_exc())
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

@app.route('/search-test')
def search_test():
    return render_template_string(get_template('search_test.html'))

@app.route('/api/debug-search')
def debug_search():
    """Debug endpoint to check search functionality"""
    try:
        info = {
            'data_file_exists': os.path.exists(DATA_FILE),
            'data_file_path': os.path.abspath(DATA_FILE) if os.path.exists(DATA_FILE) else 'Not found',
            'data_file_size': os.path.getsize(DATA_FILE) if os.path.exists(DATA_FILE) else 0,
        }
        
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                
                def count_employees(node):
                    count = 1
                    for child in node.get('children', []):
                        count += count_employees(child)
                    return count
                
                info['total_employees'] = count_employees(data) if data else 0
                info['root_employee'] = data.get('name', 'Unknown') if data else 'No data'
                info['has_children'] = bool(data.get('children')) if data else False
                
                def flatten(node, results=None):
                    if results is None:
                        results = []
                    if node and isinstance(node, dict):
                        results.append({
                            'id': node.get('id'),
                            'name': node.get('name'),
                            'title': node.get('title'),
                            'department': node.get('department')
                        })
                        children = node.get('children', [])
                        if children and isinstance(children, list):
                            for child in children:
                                flatten(child, results)
                    return results
                
                all_employees = flatten(data)
                info['sample_employees'] = all_employees[:5] if all_employees else []
                info['searchable_count'] = len(all_employees)
        else:
            info['error'] = 'Data file does not exist. Try triggering an update.'
            
        return jsonify(info)
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/force-update', methods=['POST'])
def force_update():
    """Force an immediate update and wait for completion"""
    try:
        logger.info("Force update requested")
        update_employee_data()
        
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                
            def count_employees(node):
                if not node:
                    return 0
                count = 1
                for child in node.get('children', []):
                    count += count_employees(child)
                return count
                
            total = count_employees(data)
            return jsonify({
                'success': True,
                'message': f'Data updated successfully. {total} employees in hierarchy.',
                'file_created': True
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Update completed but no data file created. Check Azure AD credentials.',
                'file_created': False
            })
    except Exception as e:
        logger.error(f"Force update error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

OFFLINE_MODE = os.environ.get('OFFLINE_MODE') == 'true'

if __name__ != '__main__':
    if not OFFLINE_MODE:
        start_scheduler()
    else:
        logger.info("OFFLINE_MODE enabled: Scheduler and auto-updates disabled.")

if __name__ == '__main__':
    if not OFFLINE_MODE:
        start_scheduler()
    else:
        logger.info("OFFLINE_MODE enabled: Scheduler and auto-updates disabled.")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=8080)
    finally:
        if not OFFLINE_MODE:
            stop_scheduler()
