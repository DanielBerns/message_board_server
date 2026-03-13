# run.py
# This file is used to run the Flask development server.
import os
from dotenv import load_dotenv

import logging

def main():
    load_dotenv()
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    from application import create_app

    config_name = os.getenv('FLASK_CONFIG', 'development')
    app = create_app(config_name)

    # Debug mode should be False in production
    app.run(host='0.0.0.0', port=5000, debug=app.config.get('DEBUG', False))

if __name__ == '__main__':
    main()
