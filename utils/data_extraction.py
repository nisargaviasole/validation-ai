from azure.storage.blob import BlobServiceClient
from io import BytesIO
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv()

connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME')


def get_storage_client(blob_name):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)
    return blob_client


def upload_to_azure_space(file_bytes: BytesIO) -> str:
    try:
        file_name = "uploaded_file.xlsx"
        blob_client = get_storage_client(file_name)

        blob_client.upload_blob(file_bytes, overwrite=True)

        return blob_client.url

    except Exception as e:
        raise Exception(f"Azure upload failed: {str(e)}")


def download_from_storage() -> pd.DataFrame:
    try:
        object_name = "uploaded_file.xlsx"
        
        blob_client = get_storage_client(object_name)
        blob_data = blob_client.download_blob()
        buffer = BytesIO(blob_data.readall())
        
        df = pd.read_excel(buffer, engine="openpyxl")
        
        return df
    except Exception as e:
        return None

    
def clean_column_values(df):
    df.fillna("", inplace=True)
    for col in df.columns:
        if col == "Agent NPN":
            df[col] = df[col].apply(lambda x: str(x).split(".")[0].strip() if str(x).replace('.', '', 1).isdigit() else str(x).strip())
        else:
            df[col] = df[col].apply(lambda x: str(x).strip())
    return df