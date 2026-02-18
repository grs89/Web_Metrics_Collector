import os
import yaml
import logging

def load_config(path=None):
    if path is None:
        path = os.getenv("CONFIG_FILE", "hosts.yml")
    if not os.path.exists(path):
        logging.warning("hosts.yml not found, using empty config")
        return {"hosts": []}
    
    with open(path, "r") as f:
        return yaml.safe_load(f)

def get_db_params():
    return {
        "database": os.getenv("DB_NAME", "wmc_db"),
        "user": os.getenv("DB_USER", "wmc_user"),
        "password": os.getenv("DB_PASSWORD", "wmc_password"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
    }
