Flit Rovers
Flit Rovers is a web application designed to help users plan their bike travel itineraries with ease. It allows users to sign up or log in using Firebase authentication, access a planner page to create and manage itineraries, and store preferences in a SQLite database. The app is built with Flask, styled with CSS, and deployed on Render.
Features

User Authentication: Secure signup and login using Firebase Authentication (email/password).
Planner Page: A dedicated page for users to plan their bike travel itineraries, select bike models, and save preferences.
Database Storage: SQLite database to store user itineraries and preferences.
Responsive Design: Clean and user-friendly UI with a gradient background and centered layout.
Deployment: Hosted on Render for easy access.

Tech Stack

Backend: Flask (Python)
Frontend: HTML, CSS, JavaScript
Authentication: Firebase Authentication
Database: SQLite
Deployment: Render
Version Control: Git and GitHub

Prerequisites
Before setting up the project, ensure you have the following installed:

Python 3.8 or higher
Git
Node.js (for Firebase dependencies, if needed)
A Firebase project with Authentication enabled
A Render account for deployment (optional)

Setup Instructions
1. Clone the Repository
Clone the Flit Rovers repository to your local machine:
git clone https://github.com/Lawrencesumith/Flit-Rovers-New.git
cd Flit-Rovers-New

2. Set Up a Virtual Environment
Create and activate a virtual environment to manage dependencies:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install Dependencies
Install the required Python packages using requirements.txt:
pip install -r requirements.txt

The requirements.txt file includes dependencies like:

Flask
firebase-admin
python-dotenv
gunicorn (for deployment)

4. Configure Firebase

Create a Firebase project in the Firebase Console.

Enable Email/Password authentication in the Authentication section.

Download the Firebase Admin SDK service account key (firebase-adminsdk.json).

Secure Storage: Do not commit firebase-adminsdk.json to the repository. Instead:

Place it in the project root directory temporarily for local development.
Add it to .gitignore:firebase-adminsdk.json


For production, use environment variables (see Deployment section).


Add Firebase client-side configuration to your signup.html and login.html templates:

In the Firebase Console, go to Project Settings > General > Your Apps.
Add a web app and copy the Firebase configuration snippet.
Include it in your HTML files (e.g., signup.html):<script src="https://www.gstatic.com/firebasejs/9.6.1/firebase-app.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.6.1/firebase-auth.js"></script>
<script>
  const firebaseConfig = {
    apiKey: "your-api-key",
    authDomain: "your-auth-domain",
    projectId: "your-project-id",
    storageBucket: "your-storage-bucket",
    messagingSenderId: "your-messaging-sender-id",
    appId: "your-app-id"
  };
  firebase.initializeApp(firebaseConfig);
</script>





5. Set Up Environment Variables
Create a .env file in the project root and add the following:
FLASK_APP=app.py
FLASK_ENV=development
FLASK_SECRET_KEY=your-fixed-secret-key-for-development
DB_PATH=flit_rovers.db


FLASK_SECRET_KEY: A secure key for Flask sessions.
DB_PATH: Path to the SQLite database (e.g., flit_rovers.db).

Add .env to .gitignore:
.env

6. Initialize the Database
Run the Flask app to create the SQLite database (flit_rovers.db):
python app.py

The app initializes the database on the first run if it doesn’t exist.
7. Run the Application Locally
Start the Flask development server:
python app.py


Open your browser and navigate to http://127.0.0.1:5000.
You should see the homepage. From there, you can sign up or log in.

Project Structure
Flit-Rovers-New/
│
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── flit_rovers.db          # SQLite database (created after first run)
├── static/                 # Static files (CSS, JavaScript, images)
│   └── style.css           # Global styles
├── templates/              # HTML templates
│   ├── index.html          # Homepage
│   ├── signup.html         # Signup page
│   ├── login.html          # Login page
│   ├── success.html        # Success page after signup/login
│   └── planner.html        # Planner page for itinerary planning
├── .env                    # Environment variables (not committed)
├── .gitignore              # Git ignore file
└── README.md               # This file

Usage

Homepage: Visit the root URL (/) to access the homepage.
Signup/Login:
Navigate to /signup to create a new account using email and password.
Navigate to /login to log in with existing credentials.
Firebase Authentication handles user management.


Planner Page:
After successful signup or login, you’ll be redirected to /success.
Click "Go to planner" to access the /planner page (requires login).
Select bike models, plan your itinerary, and save preferences.


Logout: (If implemented) Use the logout functionality to end your session.

Deployment on Render
Flit Rovers is deployed on Render at https://flit-rovers.onrender.com. To deploy your own instance:
1. Prepare for Deployment

Ensure requirements.txt is up to date:pip freeze > requirements.txt


Add a Procfile in the project root:web: gunicorn app:app


Add a runtime.txt to specify the Python version:python-3.9.6



2. Push to GitHub

Commit and push your changes to GitHub:git add .
git commit -m "Prepare for Render deployment"
git push origin main



3. Deploy on Render

Log in to Render and create a new Web Service.
Connect your GitHub repository (Lawrencesumith/Flit-Rovers-New).
Configure the service:
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
Environment Variables:
FLASK_APP: app.py
FLASK_ENV: production
FLASK_SECRET_KEY: your-fixed-secret-key-for-production
DB_PATH: /path/to/flit_rovers.db (Render uses ephemeral storage, so consider using a managed database in production)
Firebase Credentials: Instead of firebase-adminsdk.json, set the credentials as an environment variable:
GOOGLE_CREDENTIALS: (Paste the contents of firebase-adminsdk.json as a single-line JSON string)
In app.py, load the credentials:import os
import json
from firebase_admin import credentials

google_credentials = os.getenv("GOOGLE_CREDENTIALS")
cred_dict = json.loads(google_credentials)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)








Deploy the service and wait for the build to complete.
Access your app at the provided Render URL (e.g., https://flit-rovers.onrender.com).

4. Post-Deployment Notes

Database Persistence: Render’s filesystem is ephemeral, so the SQLite database (flit_rovers.db) will be reset on each deploy. For production, consider using a managed database like PostgreSQL.
Scaling: Adjust Render’s instance type if you expect higher traffic.

Troubleshooting

Signup/Login Fails:
Ensure Firebase is configured correctly (API keys, service account credentials).
Check browser console for JavaScript errors.
Verify the /set_session route logs for errors.


Redirected to Login Page:
Session might not be set. Check logs for session setup (session['user_id']).
Ensure FLASK_SECRET_KEY is consistent across restarts.


Database Issues:
Verify DB_PATH points to the correct location.
Ensure the database schema is initialized.


Push Blocked by GitHub:
If you accidentally commit firebase-adminsdk.json, GitHub’s Push Protection will block the push. Remove the file from history:git filter-repo --path firebase-adminsdk.json --invert-paths
git push origin main --force





Contributing
Contributions are welcome! To contribute:

Fork the repository.
Create a new branch (git checkout -b feature/your-feature).
Make your changes and commit (git commit -m "Add your feature").
Push to your fork (git push origin feature/your-feature).
Open a Pull Request.

License
This project is licensed under the MIT License. See the LICENSE file for details.
Contact
For questions or feedback, reach out to Lawrencesumith.

