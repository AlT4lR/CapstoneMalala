import os
from website import create_app

# Get the configuration name from an environment variable, default to 'dev'
config_name = os.getenv('FLASK_CONFIG') or 'dev'
app = create_app(config_name)

if __name__ == '__main__':
    # The debug=True flag is useful for development. 
    # It enables the debugger and reloads the server when you make changes.
    # For production, you would use a proper WSGI server instead of app.run().
    app.run(debug=True)