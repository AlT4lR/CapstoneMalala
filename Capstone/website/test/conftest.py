# tests/conftest.py
import pytest
from website import create_app

@pytest.fixture(scope='module')
def app():
    """
    Provides a Flask application instance for testing.
    The scope='module' means the app is created once per test module.
    """
    app = create_app('test') 
    app.config.update({
        "TESTING": True,
        "RATELIMIT_ENABLED": False, 
    })

    # Optional: Set up test database or mock database interactions here if needed
    # Give the test client a way to access the app
    with app.app_context():
        yield app

@pytest.fixture(scope='module')
def client(app):
    """
    Provides a test client for the Flask application.
    The test client can make requests to the application.
    """
    with app.test_client() as client:
        yield client

@pytest.fixture(scope='module')
def runner(app):
    """
    Provides a runner for Flask CLI commands.
    """
    with app.test_cli_runner() as runner:
        yield runner