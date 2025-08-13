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

It makes one API call per day at 8PM and saves the acquired data within employee_data.json, which sits securely within the app service. When someone visits the org chart, it displays the Org data based upon the contents of employee_data.json rather than making constant API calls via Graph API. This way it makes a single API request, once per day, rather than making constant requests each time someone visit the page. This not only reduces the amount of traffic caused by this application, but also makes it faster and more responsive.
