# app/user/__init__.py

from flask import Blueprint
import os

# Get the absolute path to the templates folder
template_folder = os.path.join(os.path.dirname(__file__), 'templates')

user_bp = Blueprint('user', __name__, template_folder=template_folder)

from app.user import routes
