# main.py
# This file is located *outside* the 'website' package folder

from website import create_app # Import create_app from your package

# Call the factory function to create the app instance
app = create_app()

if __name__ == '__main__':
    # Run the development server
    app.run(debug=True) # debug=True is only for development