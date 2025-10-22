# main.py
import os
from website import create_app

# Use the FLASK_CONFIG environment variable if it's set, otherwise default to 'dev'
config_name = os.getenv('FLASK_CONFIG', 'dev')
app = create_app(config_name)

if __name__ == '__main__':
    # This configuration is the most stable for Windows development:
    # host='0.0.0.0': Makes the server accessible on your network, fixing ERR_FAILED.
    # use_reloader=False: Prevents the OSError [WinError 10038] socket crash.
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)