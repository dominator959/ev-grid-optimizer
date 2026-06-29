import os
import mysql.connector
from mysql.connector import Error

def load_env():
    """
    Manually parses a local .env file if it exists and populates os.environ
    to avoid needing external dependencies like python-dotenv.
    """
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        key, val = parts[0].strip(), parts[1].strip()
                        # Remove quotes if present
                        if val.startswith(('"', "'")) and val.endswith(('"', "'")):
                            val = val[1:-1]
                        os.environ[key] = val

# Load env variables on module import
load_env()

def get_db_connection():
    """
    Establishes a connection to the MySQL database.
    Configures settings from environment variables with no hardcoded secrets.
    """
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_name = os.environ.get('DB_NAME', 'EV_Grid_Optimizer')
    db_user = os.environ.get('DB_USER', 'root')
    db_pass = os.environ.get('DB_PASS')  # No fallback password default
    db_port = os.environ.get('DB_PORT', '3306')

    try:
        connection = mysql.connector.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_pass,
            port=db_port
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Database Connection Error: {e}")
        print("\nTip: Check that your local '.env' file exists and contains the correct DB_PASS.")
        return None
