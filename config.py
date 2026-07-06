import oracledb

DB_CONFIG = {
    "user": "system",
    "password": "new12345",
    "dsn": "localhost:1521/XEPDB1"
}

def get_connection():
    return oracledb.connect(**DB_CONFIG)