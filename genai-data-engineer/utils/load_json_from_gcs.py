import logging
import json
import yaml
from google.cloud import storage

logger = logging.getLogger(__name__)

def load_json_from_gcs(gcs_uri: str) -> dict:
    """
    Load and parse a JSON file from Google Cloud Storage.
    
    Args:
        gcs_uri: Full GCS URI path in format 'gs://bucket-name/path/to/file.json'
    
    Returns:
        Parsed JSON content as a dictionary or list
    
    Raises:
        ValueError: If the GCS URI format is invalid (must start with 'gs://')
    """
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")
    
    uri = gcs_uri.replace("gs://", "")
    bucket_name, blob_path = uri.split("/", 1)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    content = blob.download_as_text()
    return json.loads(content)