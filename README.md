## What is DB-AutoOrgChart?

A demo of DBAutoOrgChart is available here (with fictitious data): https://org.d4nny.co.uk/

DB-AutoOrgChart is an application which connects to your Azure AD/Entra via Graph API, retrieves the appropriate information (employee name, title, department, 'reports to' etc.) then builds an interactive Organisation Chart based upon that information. It can be run as an App Service in Azure / Google Cloud etc or you can run it locally. NOTE: You will need the appropriate permissions in Azure to set up Graph API which is a requirement for this application to function. You only need to do this once, so someone with those permissions can set it up for you then provide the environment variables to you.

In short, these are the main features of DB-AutoOrgChart:

- Automatic organization hierarchy generation from Azure AD
- Real-time employee search functionality (employee directory)
- Completely configurable with zero coding knowledge via configureme page
- Interactive D3.js-based org chart with zoom and pan
- Detailed employee information panel
- Print-friendly org chart export
- Automatic daily updates at 8 PM
- Color-coded hierarchy levels
- Responsive design for mobile and desktop

  <img width="1640" height="527" alt="image" src="https://github.com/user-attachments/assets/f33719e6-cc03-40bc-89fc-72d9e0f58674" />


It makes one API call per day at 8PM and saves the acquired data within employee_data.json, which sits securely within the app service. When someone visits the org chart, it displays the Org data based upon the contents of employee_data.json rather than making constant API calls via Graph API. This way it makes a single API request, once per day, rather than making constant requests each time someone visit the page. This not only reduces the amount of traffic caused by this application, but also makes it faster and more responsive.

## Prerequisites
1. Python 3.8 or higher (Created with Python 3.10, so start there if unsure)
2. An Azure AD tenant with appropriate permissions to:
  a. Register an App in Azure for Graph API
  b. Create an App Service in Azure (optional but recommended)
3. Azure AD App Registration with User.Read.All permissions and admin consent (a guide to set this up is below)

## Local installation

1. Clone this repository:
```
git clone https://github.com/yourusername/db-autoorgchart.git
```

2. Open a terminal/powershell window from the base directory of the repo (where app.py is present) then create your virtual environment:

#### On Linux/Mac:
```
python3 -m venv venv
source venv/bin/activate
```

#### On Windows:
```
python -m venv venv
venv\Scripts\activate
```

3. Install the Python dependencies:
```
pip install -r requirements.txt
```

4. Configure environment variables:

See the 'Environment Variables' section further down this page.

## Configuration for local install

Check 'gunicorn_config.py' if you're on Linux, 'run_waitress.py' if you're on Windows.

For reference:

### Gunicorn Configuration (gunicorn_config.py)

  • Workers: Automatically calculated based on CPU cores

  • Port: 5000 (can be changed in the config file)

  • Timeout: 30 seconds

  • Logging: Configured for production use

### API Endpoints

  • GET / - Main web interface

  • GET /api/employees - Get complete org hierarchy

  • GET /api/search?q=query - Search employees

  • GET /api/employee/<id> - Get specific employee details

  • POST /api/update-now - Trigger manual data update

  ### Configureme.html - Customise the appearance and behaviour of the app

You can configure various aspects of the application by adding '/configure' to the end of the web address, so http://127.0.0.1:5000/ would become http://127.0.0.1:5000/configure

You will be taken to the configuration page, with the first section allowing you to amend the appeareance of the Application (colours, custom logo etc) and the second section giving you options to amend the behaviour of the application:

<img width="1167" height="1183" alt="image" src="https://github.com/user-attachments/assets/2797ed6f-c7dd-4eb1-88a7-fd8bd252bc75" />

Everything here should be self-explanatory.

### Manual Update

You can trigger a manual update by doing any of the following:
1) Restart the application
2) Send a POST request to /api/update-now
3) Go to /configure and click 'Update now'


## Running the application locally:

Make sure you have populated your .env file with the details from your Azure tenant, then follow the appropriate section depending upon your OS:

### Production Mode:

**Use the provided startup scripts:**

Linux/Mac (with Gunicorn):
```
chmod +x run.sh
./run.sh
```

Windows (with Waitress):
```
run.bat
```

**Or start the application manually:**

Linux/Mac (with Gunicorn):
```
gunicorn --config gunicorn_config.py app:app
```

Windows (with waitress)
```
python run_waitress.py
```

Note: Windows uses Waitress instead of Gunicorn as Gunicorn is not compatible with Windows.

### Development Mode:

```
python app.py
```

**Check out your Org Chart!:**

The Org Chart will be available at http://localhost:5000 (amend if you changed the port number)


## Registering the application in Azure

### 1. Create an App Registration in Azure AD:

a. Go to Azure Portal > Azure Active Directory > App registrations

b. Click "New registration"

c. Name your app (e.g., "DB AutoOrgChart")

d. Select "Accounts in this organizational directory only"

e. No redirect URL needed for this application


### 2. Configure API Permissions:

a. In your app registration, go to "API permissions"

b. Click "Add a permission" > "Microsoft Graph" > "Application permissions"

c. Select User.Read.All

d. Click "Grant admin consent" (requires admin privileges)


### 3. Create Client Secret:

a. Go to "Certificates & secrets"

b. Click "New client secret"

c. Choose an expiration period

d. Copy the secret value IMMEDIATELY (it won't be shown again) **this is your 'AZURE_CLIENT_SECRET'**


### 4. Note Your IDs:

From the Overview page, copy:

- Application (client) ID **this is your 'AZURE_CLIENT_ID'** 

- Directory (tenant) ID **this is your 'AZURE_TENANT_ID'**

## Environment variables

Open '.env.template' and save a new version (to the same folder) naming it '.env', then edit .env with notepad/notepad++/whatever and populate it with your details:

```
AZURE_TENANT_ID=your-tenant-id

AZURE_CLIENT_ID=your-client-id

AZURE_CLIENT_SECRET=your-client-secret

TOP_LEVEL_USER_EMAIL=ceo@yourcompany.com

TOP_LEVEL_USER_ID=optional-user-id
```

<img width="709" height="363" alt="image" src="https://github.com/user-attachments/assets/57d51dd5-c8a3-4f4c-89ac-ba2ad1d73747" />

For AZURE_TENANT_ID, AZURE_CLIENT_ID and AZURE_CLIENT_SECRET check the 'registering the application in Azure' section.

To obtain the values for TOP_LEVEL_USER_EMAIL and TOP_LEVEL_USER_ID you need to open Azure AD/Entra and locate your most senior employee (whoever will appear at the very top of the Org Chart), open their 'properties' tab and get the following bits of info:

<img width="942" height="682" alt="image" src="https://github.com/user-attachments/assets/6b3066bc-0376-462e-bdee-7c6f67834cbb" />




<img width="709" height="363" alt="image" src="https://github.com/user-attachments/assets/57d51dd5-c8a3-4f4c-89ac-ba2ad1d73747" />

<img width="942" height="682" alt="image" src="https://github.com/user-attachments/assets/6b3066bc-0376-462e-bdee-7c6f67834cbb" />

## Deploy to Azure as an App Service
TBC

## FAQ

**How can I change the logo or user icon images?**
You can replace the logo on the /configure page, but if that is not working for you then simply replace 'icon.png' in the /static/ folder with your own version. I recommend keeping to the resolution of 678 x 246.
Replacing the user icon is a similar process, just replace 'usericon.png' with your own version and stick to 128 x 128.

TBC - Will continue to populate with real questions if/when they arise.

## Troubleshooting

**Changes that I've made aren't updating on the chart:**
Load the page with a fresh cache (Ctrl + F5) as your browser will be holding on to the old Javascript. Any errors communicating with Azure via Graph API will be shown in the terminal.

**Problems with the search feature:**
Navigate to /search-test to open search_test.html. Here you'll find various tools to check the status of your employee data and also to test the data directly from employee_data.json.

TBC - Will continue to populate if/when anybody has issues

## To-Do list
- ~~Add the option to print the current view~~ DONE
- ~~Add zoom in/out buttons~~ DONE
- ~~Switch to Gunicorn (linux) and Waitress (Windows)~~ DONE
- ~~Create a logging function to record the outcome of each daily API update.~~ DONE
- ~~Create detailed instructions for the readme.md~~ DONE
- ~~Add a /config/ route for intial setup (upload a logo, changing header text, page name, update time, update frequency, refresh now, colour scheme and theme etc).~~ DONE
- ~~Add more navigation options such as fit to screen, collapse all, expand all etc.~~ DONE
- Add an 'options' panel for the user to customise the view (colours, depth, font size, card layout etc).
- Make the contact pop-out window to the right more visually appealing.
- The final level of each department to appear vertically rather than horizontally, to reclaim some page width.
- Build a docker image for convenience.
- Create an 'installer' script which will automatically run through the process of setting up Graph API and/or App Service using Powershell.
- Import employee photos from Graph API, cached locally, failback to current icon if no image found.
- Option to export a high quality PDF of the entire collapsed Org Chart.
- Add statistics box/page which shows headcount trends over time, average team sizes by level, department distribution etc.
- Add 'New hire indicators' (bold/enhanced card that stands out) for those who have joined within the last 3 months.
- Text only view for compact exporting and printing.
- Split out the styling from index.html to keep things compact.


