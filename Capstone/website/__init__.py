# website/__init__.py

from flask import Flask

def create_app():
    """
    Factory function to create the Flask application instance.
    """
    app = Flask(__name__)
    # Configure the app - SECRET_KEY is essential for sessions
    app.config['SECRET_KEY'] = 'lilac' # Replace with a real secret key in production!

    # Import and register Blueprints
    # The 'auth' blueprint handles login, register, logout
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint) # Registers routes like /login, /register

    # The 'main' blueprint handles general views like the dashboard
    from .views import main as main_blueprint
    app.register_blueprint(main_blueprint) # Registers routes like /dashboard, /

    # NOTE: In a real app, you would also initialize databases here (e.g., db.init_app(app))

    return app