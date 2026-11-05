# BlogSpace — Flask Blogging Platform

## Features
- User registration, login and logout
- Password hashing
- Create, read, update and delete blog posts
- Comments and comment deletion
- Search posts by title or content
- SQLite database using Flask-SQLAlchemy
- Responsive HTML/CSS interface
- Users can edit/delete only their own posts

## Run on Windows (PowerShell)

1. Open this folder in VS Code.
2. Activate your existing virtual environment:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   If you extracted this project into a new folder without a virtual environment:
   ```powershell
   py -3.12 -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
4. Start the app:
   ```powershell
   python app.py
   ```
5. Open http://127.0.0.1:5000

The SQLite database is created automatically in the `instance` folder.

## Important
- Keep the `venv` folder out of GitHub.
- Do not upload your real database or passwords to a public repository.
- Before deployment, set a long random `SECRET_KEY` using an environment variable and turn off debug mode.
- This is a learning project. Add CSRF protection (for example Flask-WTF) and production server configuration before public deployment.
