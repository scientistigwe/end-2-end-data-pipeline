import os
import requests
from backend.backend.data_pipeline.source.file.file_manager import FileManager
from backend.backend.data_pipeline.source.file.file_fetcher import FileFetcher
from flask import current_app
import io
import pandas as pd


def handle_file_upload(file_content, filename):
    """
    Handle the logic for uploading and processing a file.
    This includes fetching file, processing, and retrieving metadata.
    """
    try:
        # Process the file in-memory, no need to save to disk
        file_io = io.BytesIO(file_content)

        # Process the file depending on its extension
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(file_io)
        elif filename.lower().endswith('.json'):
            df = pd.read_json(file_io)
        elif filename.lower().endswith('.xlsx'):
            df = pd.read_excel(file_io)
        elif filename.lower().endswith('.parquet'):
            df = pd.read_parquet(file_io)
        else:
            return {'filename': filename, 'status': 'error', 'message': 'Unsupported file format'}

        # Extract metadata directly from the file content
        metadata = extract_metadata_from_content(file_content, filename)

        if df is None:
            return {'filename': filename, 'status': 'error', 'message': 'Failed to read file content'}

        # Prepare the dataframe for further processing
        preparation_result = FileManager.prepare_for_orchestrator(df)

        result = {
            'filename': filename,
            'status': 'success',
            'metadata': metadata,
            'preparation_result': preparation_result
        }

        return result

    except Exception as e:
        return {'filename': filename, 'status': 'error', 'message': f'Error processing file: {str(e)}'}

def extract_metadata_from_content(file_content, filename):
    """
    Extract metadata directly from file content, depending on the file type.
    This can include file size, columns (for CSV), and other relevant info.
    """
    metadata = {
        'filename': filename,
        'file_size': len(file_content),  # Example: file size in bytes
        'file_type': filename.split('.')[-1]  # Get file extension type
    }

    try:
        if filename.lower().endswith('.csv'):
            # For CSV, extract column names as metadata
            file_io = io.BytesIO(file_content)
            df = pd.read_csv(file_io, nrows=1)  # Read only the first row to get the columns
            metadata['columns'] = list(df.columns)

        elif filename.lower().endswith('.json'):
            # For JSON, extract the keys of the first item as metadata (if it's an array of objects)
            file_io = io.BytesIO(file_content)
            data = pd.read_json(file_io)
            metadata['keys'] = list(data.iloc[0].keys()) if len(data) > 0 else []

        elif filename.lower().endswith('.xlsx'):
            # For Excel, extract sheet names and columns from the first sheet
            file_io = io.BytesIO(file_content)
            df = pd.read_excel(file_io, sheet_name=None)
            metadata['sheet_names'] = list(df.keys())
            metadata['columns'] = list(df[list(df.keys())[0]].columns)

        elif filename.lower().endswith('.parquet'):
            # For Parquet, extract schema information (columns and types)
            file_io = io.BytesIO(file_content)
            df = pd.read_parquet(file_io)
            metadata['columns'] = list(df.columns)

    except Exception as e:
        metadata['error'] = f"Error extracting metadata: {str(e)}"

    return metadata


def get_file_metadata(file_content, filename):
    """
    Retrieve metadata directly from file content without using file path.
    """
    try:
        metadata = extract_metadata_from_content(file_content, filename)

        return {
            'status': 'success',
            'metadata': metadata
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Error extracting metadata: {str(e)}"
        }

