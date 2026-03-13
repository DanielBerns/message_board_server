import unittest
import json
import requests
import time
import logging
import subprocess

# Configure logging
logging.basicConfig(
    filename='test_heartbeat.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_client')

BASE_URL = 'http://127.0.0.1:5000'

class HeartbeatClientTestCase(unittest.TestCase):
    server_process = None

    @classmethod
    def setUpClass(cls):
        """Set up the database and users before running tests, and start the server."""
        logger.info("=== Setting up test database and users via manage_db.py ===")
        
        try:
            # 1. Delete previous database and initialize
            logger.info("Running manage_db.py --init")
            subprocess.run(['uv', 'run', 'server/manage_db.py', '--init'], check=True)
            
            # 2. Create admin user
            logger.info("Running manage_db.py --admin")
            subprocess.run(['uv', 'run', 'server/manage_db.py', '--admin', 'admin', 'adminpw'], check=True)
            
            # 3. Create test_client user
            logger.info("Running manage_db.py --client")
            subprocess.run(['uv', 'run', 'server/manage_db.py', '--client', 'test_client', 'password'], check=True)
            logger.info("Database setup complete.")
            
            # 4. Start the server
            logger.info("Starting the development server for testing...")
            cls.server_log_file = open('server_test_run.log', 'w')
            cls.server_process = subprocess.Popen(
                ['uv', 'run', 'server/run.py'],
                stdout=cls.server_log_file,
                stderr=subprocess.STDOUT
            )
            time.sleep(3) # Give server time to boot
            
        except Exception as e:
            logger.error(f"Failed to set up database or start server: {e}")
            if cls.server_process:
                cls.server_process.terminate()
            raise

    @classmethod
    def tearDownClass(cls):
        """Stop the server after tests."""
        if cls.server_process:
            logger.info("Terminating development server...")
            cls.server_process.terminate()
            cls.server_process.wait()
            if hasattr(cls, 'server_log_file') and cls.server_log_file:
                cls.server_log_file.close()

    def test_heartbeat_flow(self):
        logger.info("=== Starting heartbeat test flow ===")
        
        # --- Authentication ---
        # Login test_client
        client_login_url = f'{BASE_URL}/auth/login'
        logger.info(f"Attempting login for test_client at {client_login_url}")
        
        try:
            response = requests.post(client_login_url, json={'username': 'test_client', 'password': 'password'}, timeout=5)
            self.assertEqual(response.status_code, 200, f"Client Login failed: {response.text}")
            client_token = response.json()['access_token']
        except Exception as e:
            logger.error(f"test_client login failed: {e}")
            raise
            
        client_headers = {'Authorization': f'Bearer {client_token}'}

        # Login admin
        logger.info(f"Attempting login for admin at {client_login_url}")
        try:
            response = requests.post(client_login_url, json={'username': 'admin', 'password': 'adminpw'}, timeout=5)
            self.assertEqual(response.status_code, 200, f"Admin Login failed: {response.text}")
            admin_token = response.json()['access_token']
        except Exception as e:
            logger.error(f"admin login failed: {e}")
            raise
            
        admin_headers = {'Authorization': f'Bearer {admin_token}'}

        # --- Messaging Flow ---
        message_url = f'{BASE_URL}/api/messages/private'
        
        # test_client sends message to admin
        logger.info("test_client sending private message to admin")
        try:
            response = requests.post(message_url, headers=client_headers, json={
                "recipient_username": "admin",
                "content": "Hello Admin, this is a test message."
            }, timeout=5)
            self.assertEqual(response.status_code, 201, f"Failed to send message to admin: {response.text}")
        except Exception as e:
            logger.error(f"test_client message failed: {e}")
            raise

        # admin sends response to test_client
        logger.info("admin sending private message reply to test_client")
        try:
            response = requests.post(message_url, headers=admin_headers, json={
                "recipient_username": "test_client",
                "content": "Hello test_client, message received loud and clear."
            }, timeout=5)
            self.assertEqual(response.status_code, 201, f"Failed to send reply to test_client: {response.text}")
        except Exception as e:
            logger.error(f"admin message failed: {e}")
            raise

        # --- Heartbeat Flow ---
        heartbeat_url = f'{BASE_URL}/api/heartbeat'
        
        try:
            # 1. Get initial heartbeat
            logger.info(f"Fetching initial heartbeat at {heartbeat_url}")
            response = requests.get(heartbeat_url, headers=client_headers, timeout=5)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            
            user_data = next((u for u in data if u['username'] == 'test_client'), None)
            self.assertIsNotNone(user_data, "Test user not found in heartbeat list")
            
            # 2. Post heartbeat
            logger.info(f"Posting heartbeat to {heartbeat_url}")
            response = requests.post(heartbeat_url, headers=client_headers, timeout=5)
            self.assertEqual(response.status_code, 200)
            
            # 3. Get updated heartbeat
            response = requests.get(heartbeat_url, headers=client_headers, timeout=5)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            
            user_data_updated = next((u for u in data if u['username'] == 'test_client'), None)
            self.assertIsNotNone(user_data_updated)
            self.assertIsNotNone(user_data_updated['last_heartbeat'], "Heartbeat was not updated")

            # 4. Check if heartbeat updates after delay
            logger.info("Testing heartbeat timestamp iteration.")
            first_heartbeat = user_data_updated['last_heartbeat']
            time.sleep(1)
            
            response = requests.post(heartbeat_url, headers=client_headers, timeout=5)
            self.assertEqual(response.status_code, 200)

            response = requests.get(heartbeat_url, headers=client_headers, timeout=5)
            self.assertEqual(response.status_code, 200)
            
            user_data_final = next((u for u in response.json() if u['username'] == 'test_client'), None)
            self.assertNotEqual(first_heartbeat, user_data_final['last_heartbeat'])
            
            logger.info("Heartbeat timestamp updated successfully. Integration flow complete.")
        except Exception as e:
            logger.error(f"Heartbeat flow failed: {e}")
            raise

if __name__ == '__main__':
    unittest.main()
