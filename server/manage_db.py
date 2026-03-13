# manage_db.py
# This script is for offline database management tasks:
# 1. Initializing the database schema.
# 2. Creating the initial admin user.
# 3. Adding new client users.
# 4. Resetting user passwords.
import os
from getpass import getpass
from dotenv import load_dotenv

load_dotenv()

import argparse
import logging
from application import create_app, db
from application.models import User
from application.extensions import bcrypt # For password hashing

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('manage_db')

app = create_app(os.getenv('FLASK_CONFIG') or 'development')

def init_db():
    with app.app_context():
        try:
            logger.info("Initializing database and dropping old tables if they exist...")
            db.drop_all()
            db.create_all()
            logger.info("Database initialized and tables created successfully.")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

def create_user_programmatically(username, password, is_admin):
    with app.app_context():
        logger.info(f"Attempting to create user: {username} (admin={is_admin})")
        if User.query.filter_by(username=username).first():
            logger.warning(f"User '{username}' already exists. Skipping.")
            return

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password_hash=hashed_password, is_admin=is_admin)

        try:
            db.session.add(user)
            db.session.commit()
            logger.info(f"User '{username}' created successfully.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user {username}: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Database Management Script")
    parser.add_argument('--init', action='store_true', help="Initialize the database (drops existing)")
    parser.add_argument('--admin', nargs=2, metavar=('USERNAME', 'PASSWORD'), help="Create an admin user")
    parser.add_argument('--client', nargs=2, metavar=('USERNAME', 'PASSWORD'), help="Create a client user")
    
    args = parser.parse_args()
    
    if args.init:
        init_db()
    if args.admin:
        create_user_programmatically(args.admin[0], args.admin[1], is_admin=True)
    if args.client:
        create_user_programmatically(args.client[0], args.client[1], is_admin=False)
    
    if not any(vars(args).values()):
        parser.print_help()
