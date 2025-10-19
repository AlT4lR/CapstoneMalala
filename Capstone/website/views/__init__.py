# website/views/__init__.py

from flask import Blueprint

# Define the main blueprint that all other view modules will use
main = Blueprint('main', __name__)

# Import the route modules to register their routes with the blueprint
from . import core, transactions, schedules, invoices, billings, analytics