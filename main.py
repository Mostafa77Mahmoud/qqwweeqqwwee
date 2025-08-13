from app import create_app
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

app = create_app()

if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs('exports', exist_ok=True)
    os.makedirs('backups', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
