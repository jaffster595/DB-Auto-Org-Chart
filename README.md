## What is DB-AutoOrgChart?
DB-AutoOrgChart is an application which connects to your Azure AD/Entra via Graph API, retrieves the appropriate information (employee name, title, department, 'reports to' etc.) then builds an interactive Organisation Chart based upon that information. It can be run as an App Service in Azure / Google Cloud etc or you can run it locally. NOTE: You will need the appropriate permissions in Azure to set up Graph API which is a requirement for this application to function. You only need to do this once, so someone with those permissions can set it up for you then provide the environment variables to you.

In short, these are the main features of DB-AutoOrgChart:

- Automatic organization hierarchy generation from Azure AD
- Real-time employee search functionality
- Interactive D3.js-based org chart with zoom and pan
- Detailed employee information panel
- Print-friendly org chart export
- Automatic daily updates at 8 PM
- Color-coded hierarchy levels
- Responsive design for mobile and desktop

  <img width="1640" height="527" alt="image" src="https://github.com/user-attachments/assets/f33719e6-cc03-40bc-89fc-72d9e0f58674" />


It makes one API call per day at 8PM and saves the acquired data within employee_data.json, which sits securely within the app service. When someone visits the org chart, it displays the Org data based upon the contents of employee_data.json rather than making constant API calls via Graph API. This way it makes a single API request, once per day, rather than making constant requests each time someone visit the page. This not only reduces the amount of traffic caused by this application, but also makes it faster and more responsive.

## Prerequisites
1. Python 3.8 or higher (Created with Python 3.10)
2. An Azure AD tenant with appropriate permissions
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

### Gunicorn Configuration (gunicorn_config.py)

  • Workers: Automatically calculated based on CPU cores

  • Port: 5000 (can be changed in the config file)

  • Timeout: 30 seconds

  • Logging: Configured for production use
  
### Update Schedule

The org chart updates automatically every day at 8:00 PM. To change this:

1. Edit app.py

2. Find the line: schedule.every().day.at("20:00").do(update_employee_data)

3. Change "20:00" to your desired time (24-hour format)

### Manual Update

You can trigger a manual update by simply restarting the application or sending a POST request to /api/update-now

### API Endpoints

  • GET / - Main web interface

  • GET /api/employees - Get complete org hierarchy

  • GET /api/search?q=query - Search employees

  • GET /api/employee/<id> - Get specific employee details

  • POST /api/update-now - Trigger manual data update

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

## How to customise and configure this application

Simply navigate to your Org Chart, then at the end of the web address add /config or /configure. So your web address will look something like this: http://127.0.0.1:5000/configure 

## Deploy to Azure as an App Service
TBC

## FAQ
TBC

## Troubleshooting
TBC

## To-Do list
- ~~Add the option to print the current view~~ DONE
- ~~Add zoom in/out buttons~~ DONE
- ~~Switch to Gunicorn (linux) and Waitress (Windows)~~ DONE
- ~~Create a logging function to record the outcome of each daily API update.~~ DONE
- ~~Create detailed instructions for the readme.md~~ DONE
- ~~Add a /config/ route for intial setup (upload a logo, changing header text, page name, update time, update frequency, refresh now, colour scheme and theme etc).~~ DONE
- Add an options panel for the user to customise the view (colours, depth, font size, card layout etc).
- Make the contact pop-out window to the right more visually appealing.
- The final level of each department to appear vertically rather than horizontally, to reclaim some page width.
- Build a docker image for convenience.
