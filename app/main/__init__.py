from flask import Blueprint
import os

# Get the absolute path to the templates folder
template_folder = os.path.join(os.path.dirname(__file__), 'templates')

main_bp = Blueprint('main', __name__, template_folder=template_folder)

from app.main import routes
