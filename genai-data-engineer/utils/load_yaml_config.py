# utils/load_yaml_config.py

import os
import yaml
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

def load_config(path: str = "config.yaml") -> Dict[str, Any]:

    if not os.path.exists(path):
        raise FileNotFoundError(f"Configuration file not found: {path}")

    try:
        with open(path, "r") as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Loaded configuration from {path}")
        return config
    
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML file {path}: {e}")
        raise
