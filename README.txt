# Δημιούργησε virtual environment
python -m venv .venv

# Ενεργοποίησέ το
.venv\Scripts\activate  # Windows

# Εγκατάστησε dependencies
pip install flask flask-sqlalchemy flask-migrate python-dotenv psycopg2

pip freeze > requirments.txt 