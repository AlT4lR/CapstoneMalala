import os
from website import create_app

app = create_app(os.getenv('FLASK_CONFIG') or 'dev')

if __name__ == '__main__':
    app.run(debug=True)