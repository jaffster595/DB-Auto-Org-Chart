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
1) Python 3.8 or higher (Created with Python 3.10)
2) An Azure AD tenant with appropriate permissions
3) Azure AD App Registration with User.Read.All permissions and admin consent (a guide to set this up is below)

## Local installation
TBC

<img width="709" height="363" alt="image" src="https://github.com/user-attachments/assets/57d51dd5-c8a3-4f4c-89ac-ba2ad1d73747" />

<img width="942" height="682" alt="image" src="https://github.com/user-attachments/assets/6b3066bc-0376-462e-bdee-7c6f67834cbb" />



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
- Create detailed instructions for the readme.md 
- Add a /config/ route for intial setup (upload a logo, changing header text, page name, update time, update frequency, refresh now, colour scheme and theme etc).
- Add an options panel for the user to customise the view (colours, depth, font size, card layout etc).
- Make the contact pop-out window to the right more visually appealing.
- The final level of each department to appear vertically rather than horizontally, to reclaim some page width.
- Build a docker image for convenience.
