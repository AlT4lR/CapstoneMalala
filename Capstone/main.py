import os
from website import create_app

config_name = os.getenv('FLASK_CONFIG', 'dev')
app = create_app(config_name)

if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)