#Imports
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

def index():
    return "Testing 123"