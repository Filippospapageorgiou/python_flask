# Δημιούργησε virtual environment
python -m venv .venv

# Ενεργοποίησέ το
.venv\Scripts\activate  # Windows

# Εγκατάστησε dependencies
pip install flask flask-sqlalchemy flask-migrate python-dotenv psycopg2

pip freeze > requirments.txt 

#2. Αρχικοποίηση database migrations
flask db init #Δημιουργεί το migrations/ folder
flask db migrate -m "Initial migration" # Δημιουργεί το migration script από τα models
flask db upgrade # Εκτελεί το script και δημιουργεί τους πίνακες στο PostgreSQL