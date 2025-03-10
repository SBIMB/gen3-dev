import logging
import os
import requests
from requests.auth import HTTPBasicAuth
import sys
import hashlib
import json
import re
from pathlib import Path

from csv import  DictReader, DictWriter
from datetime import timedelta
from uuid import uuid4
from minio import Minio
from dotenv import load_dotenv
from boto3 import client, resource
from gen3.auth import Gen3Auth, get_access_token_with_client_credentials, get_access_token_with_key
from gen3.tools.indexing.index_manifest import index_object_manifest
from gen3.index import Gen3Index
from gen3.file import Gen3File
from gen3.submission import Gen3Submission
from gen3minioclient.minioclient import MinioClient
from gen3minioclient.gen3client import Gen3Client

logging.basicConfig(filename="output.log", level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

class Gen3MinioClient:
    def __init__(self, gen3_minio_json_file):
        # MinioClient.configure_minio_client(gen3_minio_json_file)
        # Gen3Client.configure_gen3_client(gen3_minio_json_file)
        MinioClient.__init__(gen3_minio_json_file)
        Gen3Client.__init__(gen3_minio_json_file)
        print(f"Initialising Gen3MinioClient from credentials file 'gen3-minio-credentials.json'...")

        
    def upload_file_and_update_record(self, file_path: str, old_manifest_file):
        print("Extracting file name from file path...")
        upload_path = Path(file_path)
        file_name = upload_path.name
        size_of_file = MinioClient.calculate_size_of_file(file_path)
        print(f"Name of file to be uploaded: '{file_name}'.")
        
        print("Checking if file already exists in MinIO bucket...")
        file_exists = MinioClient.check_if_object_is_in_minio_bucket(file_name)
        if file_exists:
            print(f"File '{file_name}' already exists in MinIO bucket. Process stopped.")
            return f"File '{file_name}' already exists in MinIO bucket. Process stopped."
        try:
            print(f"Creating blank record for '{file_name}'...")
            blank_index_response = Gen3Client.create_blank_index(file_name)
            blank_index_json_response = blank_index_response.json()
            did = str(blank_index_json_response["did"])
            rev = str(blank_index_json_response["rev"])
            path_in_minio_bucket = os.path.join(did, file_name)
            
            try:
                print("Uploading file to MinIO bucket...")
                result = MinioClient.client.fput_object(
                    bucket_name=MinioClient.minio_bucket_name, 
                    object_name=path_in_minio_bucket, 
                    file_path=file_path,
                )
                
                minio_object = {
                    "guid": str(uuid4()),
                    "file_name": file_name,
                    "md5": str(result.etag,).strip('"'),
                    "size": size_of_file,
                    "acl": ["*"],
                    "urls": [f"https://{MinioClient.minio_api_endpoint}/{MinioClient.minio_bucket_name}/{path_in_minio_bucket}"],
                }
                print(minio_object)
                print(f"Object '{minio_object["file_name"]}' has been uploaded")
            except:
                print(f"Failed to upload file '{minio_object["file_name"]}'")
            
            print("Updating manifest with metadata about newly uploaded minio object...")
            MinioClient.update_minio_manifest_file(old_manifest_file)
            
            try:
                if did and rev:
                    print(f"Updating indexd database record for uploaded file with did '{did}' and rev '{rev}'...")
                    Gen3Client.update_blank_index(did, rev, minio_object)
            except:
                print(f"Failed to update blank index with GUID of '{minio_object["file_name"]}'.")
        except:
            print(f"Failed to create blank index for file '{file_name}'.")
                
        return f"File '{file_name}' uploaded successfully and indexd database records updated."
                        