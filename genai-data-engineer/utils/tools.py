import logging
import json
import yaml
from typing import Dict, Any
from io import BytesIO
import pandas as pd
from google.cloud import bigquery
from google.cloud import storage
from langchain_core.tools import tool
from state.state import FileLoadParameters, FileWriteParameters, ExecutionOutput

logger = logging.getLogger(__name__)


@tool
def execute_query(sql: str, project_id: str) -> ExecutionOutput:
    """
    Execute a SQL query against BigQuery and return execution results.
    
    Args:
        sql: SQL query string to execute on BigQuery
        project_id: GCP project ID containing the BigQuery dataset
    
    Returns:
        ExecutionOutput object containing query results information:
        - type: 'table' if results saved to table, 'result' otherwise
        - uri: Reference to destination table or job ID
        - description: Summary of rows processed and bytes used
    
    Raises:
        Exception: If query execution fails in BigQuery
    """
    try:
        client    = bigquery.Client(project=project_id)
        query_job = client.query(sql)
        result    = query_job.result()
        
        destination_uri = None
        if query_job.destination:
            destination_uri = f"bq://{query_job.destination.project}.{query_job.destination.dataset_id}.{query_job.destination.table_id}"
        rows = result.total_rows if hasattr(result, 'total_rows') else None
        bytes_processed = query_job.total_bytes_processed or 0
        logger.info(f"Query executed successfully. Rows: {rows}, Bytes: {bytes_processed}")
        
        return ExecutionOutput(
            type="table" if destination_uri else "result",
            uri=destination_uri or f"job://{query_job.job_id}",
            role="final",
            description=f"Query executed: {rows} rows, {bytes_processed} bytes processed"
        )
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        raise


def _get_table_schema(table_fqn: str, project_id: str) -> Dict[str, Any]:
    try:
        client = bigquery.Client(project=project_id)
        parts  = table_fqn.split('.')
        if len(parts) == 2:
            dataset_id, table_id = parts
            table_ref = f"{project_id}.{dataset_id}.{table_id}"
        else:
            table_ref = table_fqn
        table = client.get_table(table_ref)        
        schema = {
            "name": table.table_id,
            "type": table.table_type,  # TABLE, VIEW, EXTERNAL, etc
            "columns": [
                {
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description or ""
                }
                for field in table.schema
            ],
            "row_count": table.num_rows if table.table_type == "TABLE" else None
        }
        if table.table_type == "VIEW":
            schema["view_definition"] = table.view_query
        logger.info(f"Retrieved schema for {table_fqn}: {len(schema['columns'])} columns")
        return schema
        
    except Exception as e:
        logger.error(f"Failed to get schema for {table_fqn}: {str(e)}")
        raise

def _get_dataset_schema(dataset_fqn: str, project_id: str) -> Dict[str, Dict[str, Any]]:
    try:
        client = bigquery.Client(project=project_id)
        parts  = dataset_fqn.split('.')
        if len(parts) == 1:
            dataset_ref = f"{project_id}.{dataset_fqn}"
        else:
            dataset_ref = dataset_fqn
        tables = client.list_tables(dataset_ref)
        schemas = {}
        for table_item in tables:
            table_fqn = f"{table_item.dataset_id}.{table_item.table_id}"
            schemas[table_item.table_id] = _get_table_schema(table_fqn, project_id)
        logger.info(f"Retrieved schemas for {len(schemas)} tables in {dataset_fqn}")
        return schemas
    except Exception as e:
        logger.error(f"Failed to get dataset schema for {dataset_fqn}: {str(e)}")
        raise





@tool
def get_table_schema(table_fqn: str, project_id: str) -> dict:
    """
    Retrieve schema information for a BigQuery table.
    
    Args:
        table_fqn: Fully qualified table name in format 'dataset.table' or 'project.dataset.table'.
                   If only 'dataset.table' provided, project_id is prepended.
        project_id: GCP project ID containing the table
    
    Returns:
        Dictionary containing:
        - name: Table name
        - type: Table type (TABLE, VIEW, EXTERNAL, etc.)
        - columns: List of column definitions with name, type, mode, and description
        - row_count: Number of rows (None for views)
        - view_definition: SQL query (only for views)
    
    Raises:
        Exception: If table not found or schema retrieval fails
    """
    return _get_table_schema(table_fqn, project_id)

@tool
def get_dataset_schema(dataset_fqn: str, project_id: str) -> dict:
    """
    Retrieve schema information for all tables in a BigQuery dataset.
    
    Args:
        dataset_fqn: Fully qualified dataset name in format 'dataset' or 'project.dataset'.
                     If only dataset name provided, project_id is prepended.
        project_id: GCP project ID containing the dataset
    
    Returns:
        Dictionary mapping table names to their schema information.
        Each value is a dict with table schema (see get_table_schema for structure).
    
    Raises:
        Exception: If dataset not found or schema retrieval fails
    """
    return _get_dataset_schema(dataset_fqn, project_id)


#TODO: add a check on file size and raise error if it is too large
@tool
def read_file(params: FileLoadParameters) -> ExecutionOutput:
    """
    Read a file from Google Cloud Storage.
    
    Args:
        params: FileLoadParameters object containing:
                - path: GCS URI path in format 'gs://bucket-name/path/to/file'
    
    Returns:
        ExecutionOutput object containing:
        - type: 'file'
        - uri: The GCS path of the read file
        - content: Raw bytes of the file content
        - description: Summary of file read operation
    
    Raises:
        ValueError: If path doesn't start with 'gs://'
        Exception: If file read from GCS fails
    """
    try:
        if not params.path.startswith("gs://"):
            raise ValueError(f"Path must start with gs://: {params.path}")

        path_parts = params.path[5:].split("/", 1)
        bucket_name = path_parts[0]
        blob_name = path_parts[1] if len(path_parts) > 1 else ""

        client  = storage.Client()
        bucket  = client.bucket(bucket_name)
        blob    = bucket.blob(blob_name)
        content = blob.download_as_bytes()
        logger.info(f"Read file from {params.path}: {len(content)} bytes")
        output = ExecutionOutput(
            type="file",
            uri=params.path,
            role="final",  # temp/staging/final depending on context
            description=f"Read file from GCS: {params.path}",
            content=content
        )
        return output
    except Exception as e:
        logger.error(f"Failed to read from {params.path}: {str(e)}")
        raise

@tool
def write_file(params: FileWriteParameters) -> ExecutionOutput:
    """
    Write a file to Google Cloud Storage in the specified format.
    
    Args:
        params: FileWriteParameters object containing:
                - path: GCS URI path in format 'gs://bucket-name/path/to/file.ext'
                - content: File content (format depends on 'format' parameter):
                          - csv: pandas DataFrame or string
                          - parquet: pandas DataFrame
                          - json: dict, list, or string
                          - yaml: dict or string
                          - other: string or bytes
                - format: File format ('csv', 'parquet', 'json', 'yaml', or other)
    
    Returns:
        ExecutionOutput object containing:
        - type: 'file'
        - uri: The GCS path where file was written
        - description: Summary including format of written file
    
    Raises:
        ValueError: If path doesn't start with 'gs://' or format requirements not met
        Exception: If file write to GCS fails
    """
    try:
        # Parse GCS path (gs://bucket/path/file.ext)
        if not params.path.startswith('gs://'):
            raise ValueError(f"Path must start with gs://: {params.path}")
        
        path_parts = params.path[5:].split('/', 1)
        bucket_name = path_parts[0]
        blob_name = path_parts[1] if len(path_parts) > 1 else ""
        
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob   = bucket.blob(blob_name)
        
        if params.format == "csv":
            # Assume content is DataFrame or string
            if isinstance(params.content, pd.DataFrame):
                csv_string = params.content.to_csv(index=False)
            else:
                csv_string = params.content
            blob.upload_from_string(csv_string, content_type='text/csv')
            logger.info(f"Wrote CSV to {params.path}")
            
        elif params.format == "parquet":
            # Assume content is DataFrame
            if isinstance(params.content, pd.DataFrame):
                from io import BytesIO
                buffer = BytesIO()
                params.content.to_parquet(buffer)
                blob.upload_from_string(buffer.getvalue(), content_type='application/octet-stream')
                logger.info(f"Wrote Parquet to {params.path}")
            else:
                raise ValueError("Parquet format requires DataFrame content")
            
        elif params.format == "json":
            # Assume content is dict or string
            if isinstance(params.content, (dict, list)):
                json_string = json.dumps(params.content, indent=2)
            else:
                json_string = params.content
            blob.upload_from_string(json_string, content_type='application/json')
            logger.info(f"Wrote JSON to {params.path}")
            
        elif params.format == "yaml":
            # Assume content is dict or string
            if isinstance(params.content, dict):
                yaml_string = yaml.dump(params.content)
            else:
                yaml_string = params.content
            blob.upload_from_string(yaml_string, content_type='text/yaml')
            logger.info(f"Wrote YAML to {params.path}")
            
        else:
            # Default: write as string or bytes
            blob.upload_from_string(params.content)
            logger.info(f"Wrote file to {params.path}")
        
        return ExecutionOutput(
            type="file",
            uri=params.path,
            role="final",
            description=f"File written: {params.format} format"
        )
    except Exception as e:
        logger.error(f"Failed to write to {params.path}: {str(e)}")
        raise

AVAILABLE_TOOLS = [write_file, read_file, get_dataset_schema, get_table_schema, execute_query]