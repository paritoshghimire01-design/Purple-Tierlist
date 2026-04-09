# Purple Tier Testing

A full-stack Minecraft PvP tier testing web application with private admin login, persistent SQLite storage, draggable tier reassignment, category-based tier boards, recent audit logs, and a responsive dark-themed UI.

## Pre-created Admin Accounts

- `purple123` / `hellofaabbccdd`
- `purple321` / `hellofaabbccdd`

## Tech Stack

- Backend: Flask
- Database: SQLite
- Frontend: Vanilla JavaScript SPA served by Flask

## Run Locally

1. Create a virtual environment:

```powershell
python -m venv .venv
```

2. Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Start the app:

```powershell
python app.py
```

5. Open `http://127.0.0.1:5000`

## Uploadable Hosting Package

This project is now prepared to be uploaded to Python hosting platforms.

Included deployment files:

- [render.yaml](C:\Users\nts\Documents\PURPEL%20TIER\render.yaml)
- [Procfile](C:\Users\nts\Documents\PURPEL%20TIER\Procfile)
- [wsgi.py](C:\Users\nts\Documents\PURPEL%20TIER\wsgi.py)
- [runtime.txt](C:\Users\nts\Documents\PURPEL%20TIER\runtime.txt)

These make it uploadable to services such as:

- Render
- Railway
- PythonAnywhere
- Heroku-compatible Python hosts

## Recommended Deploy: Render

1. Upload this project to GitHub.
2. Create a new Render Web Service or Blueprint from that repo.
3. Render will use:
   - `pip install -r requirements.txt`
   - `gunicorn wsgi:application`
4. Keep the persistent disk enabled so `data.db` survives restarts.

Important:

- For production, set a strong `SECRET_KEY`.
- SQLite is fine for a small deployment, but for larger scale you would eventually want Postgres.

## Manual Python Host Deploy

If your host lets you upload a ZIP or files directly:

1. Upload the whole project folder.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start with:

```bash
gunicorn wsgi:application
```

4. Set these environment variables if your host supports them:

```text
SECRET_KEY=change-this
DB_PATH=/path/to/persistent/data.db
PORT=5000
```

## Features

- Login-only access with hashed passwords
- Admin-only player creation, editing, tier movement, and deletion
- Separate lists for Crystal PvP, Sword PvP, Nethpot PvP, Axe PvP, and Mace PvP
- Search by player name
- Filter by tier
- Recent activity log
- Optional avatar URL support

## Notes

- Data is stored in `data.db` and is created automatically on first run.
- Set `SECRET_KEY` in your environment before deploying beyond local use.
