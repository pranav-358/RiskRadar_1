# app/admin/__init__.py

from flask import Blueprint
import os

# Get the absolute path to the templates folder
template_folder = os.path.join(os.path.dirname(__file__), 'templates')

admin_bp = Blueprint('admin', __name__, template_folder=template_folder)

from app.admin import routes
