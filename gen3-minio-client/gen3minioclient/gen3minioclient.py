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

logging.basicConfig(filename="output.log", level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

class Gen3MinioClient:
    MANIFEST = "data/manifest/output_manifest_file.tsv"
    COMPLETED = "data/manifest/output_manifest_file.tsv"
    MANIFEST_FIELDS = ['guid', 'file_name', 'md5', 'size', 'acl', 'urls']

    minio_bucket_name = os.getenv("MINIO_BUCKET_NAME")
    minio_api_endpoint = os.getenv("MINIO_ENDPOINT")
    minio_access_key = os.getenv("MINIO_ACCESS_KEY")
    minio_secret_key = os.getenv("MINIO_SECRET_KEY")
    gen3_commons_url = os.getenv("GEN3_COMMONS_URL")
    gen3_credentials = os.getenv("GEN3_CREDENTIALS_PATH")
    gen3_username = os.getenv("GEN3_USERNAME")
    manifest_file_location = os.getenv("MANIFEST_FILE_LOCATION")
    
    client = Minio(
        endpoint=minio_api_endpoint,
        access_key=minio_access_key,
        secret_key=minio_secret_key,
        cert_check=False,
    )

    def __init__(self):
        print(f"Initialising Gen3MinioClient with bucket {self.minio_bucket_name} and endpoint https://{self.minio_api_endpoint} for uploader {self.gen3_username}...")
        
    def configure_gen3_minio_client(self, gen3_minio_json_file):
        # opening JSON file containing credentials
        f = open(gen3_minio_json_file)

        # returns JSON object as 
        # a dictionary
        json_values = json.load(f)
        
        if not json_values["minio_bucket_name"] or json_values["minio_bucket_name"] == "":
            return f"'minio_bucket_name' attribute has not been specified"
        
        if not json_values["minio_endpoint"] or json_values["minio_endpoint"] == "":
            return f"'minio_endpoint' attribute has not been specified"
        
        if not json_values["minio_access_key"] or json_values["minio_access_key"] == "":
            return f"'minio_access_key' attribute has not been specified"
        
        if not json_values["minio_secret_key"] or json_values["minio_secret_key"] == "":
            return f"'minio_secret_key' attribute has not been specified"
        
        if not json_values["gen3_commons_url"] or json_values["gen3_commons_url"] == "":
            return f"'gen3_commons_url' attribute has not been specified"
        
        if not json_values["gen3_username"] or json_values["gen3_username"] == "":
            return f"'gen3_username' attribute has not been specified"
        
        if not (json_values["gen3_credentials_path"] or json_values["api_key"]) or json_values["gen3_credentials_path"] == "":
            return f"Either the 'gen3_credentials_path' attribute or the 'api_key' and 'key_id' combination of attributes needs to be specified."
        
        self.minio_bucket_name = json_values["minio_bucket_name"]
        self.minio_api_endpoint = json_values["minio_endpoint"]
        self.minio_access_key = json_values["minio_access_key"]
        self.minio_secret_key = json_values["minio_secret_key"]
        self.gen3_commons_url = json_values["gen3_commons_url"]
        self.gen3_credentials = json_values["gen3_credentials_path"]
        self.gen3_username = json_values["gen3_username"]
        
        self.client = Minio(
            endpoint=self.minio_api_endpoint,
            access_key=self.minio_access_key,
            secret_key=self.minio_secret_key,
            cert_check=False,
        )
    
        return f"Credentials for the 'gen3-minio-client' CLI tool has been successfully initialised."
        
        
    def get_gen3_commons_access_token(self):
        url = f"{self.gen3_commons_url}/user/credentials/cdis/access_token"
        
        # opening JSON file containing Api Key
        f = open(self.gen3_credentials)

        # returns JSON object as 
        # a dictionary
        creds = json.load(f)
        data = {
            "api_key": creds["api_key"],
            "key_id": creds["key_id"]
        }
        response = requests.post(
            url,
            data=data,
            verify=False
        )
        response_json = json.loads(response.content)
        access_token = response_json["access_token"]
        print("Fetching access token...")
        return access_token
        
    def get_minio_objects(self):
        objects = self.client.list_objects(self.minio_bucket_name, recursive=True)
        minio_objects = []
        for obj in objects:
            object_name = obj.object_name
            guid = str(uuid4())
            index = object_name.rfind('/')
            if (index != -1):
                object_name = object_name[index+1:]
            minio_object = {
                "guid": guid,
                "file_name": object_name,
                "md5": str(obj.etag).strip('"'),
                "size": obj.size,
                "acl": ["*"],
                "urls": [f"https://{self.minio_api_endpoint}/{self.minio_bucket_name}/{obj.object_name}"],
            }
            minio_objects.append(minio_object)
        return minio_objects

    def get_minio_objects_by_prefix(self, prefix: str):
        objects = self.client.list_objects(self.minio_bucket_name, prefix=prefix, recursive=True)
        minio_objects = []
        for obj in objects:
            object_name = obj.object_name
            # did = str(uuid4())
            last_index = object_name.rfind('/')
            if (last_index != -1):
                # did = object_name[ object_name.find("/")+1 : object_name.rfind("/") ]
                object_name = object_name[last_index+1:]
            minio_object = {
                "guid": str(uuid4()),
                "file_name": object_name,
                "md5": str(obj.etag).strip('"'),
                "size": obj.size,
                "acl": ["*"],
                "urls": [f"https://{self.minio_api_endpoint}/{self.minio_bucket_name}/{obj.object_name}"],
            }
            minio_objects.append(minio_object)
        return minio_objects
    
    def get_minio_object_names(self):
        objects = self.client.list_objects(self.minio_bucket_name, recursive=True)
        object_names = []
        for obj in objects:
            object_name = obj.object_name
            index = object_name.rfind('/')
            if (index != -1):
                object_name = object_name[index+1:]
            object_names.append(object_name)
            print(object_name)
        return object_names
    
    def get_minio_object_names_by_prefix(self, prefix: str):
        objects = self.client.list_objects(self.minio_bucket_name, prefix, recursive=True)
        object_names = []
        for obj in objects:
            object_name = obj.object_name
            index = object_name.rfind('/')
            if (index != -1):
                object_name = object_name[index+1:]
            object_names.append(object_name)
            print(object_name)
        return object_names
    
    def check_if_object_is_in_minio_bucket(self, object_name: str):
        object_exists = False
        minio_object_names = self.get_minio_object_names()
        if object_name in minio_object_names:
            object_exists = True
        return object_exists
    
    # Get presigned URL string to upload file in
    # bucket with response-content-type as application/json
    # and one day expiry.
    def get_minio_presigned_url(self, file_upload_path: str):
        url = self.client.get_presigned_url(
            "PUT",
            self.minio_bucket_name,
            file_upload_path,
            expires=timedelta(days=1),
            response_headers={"response-content-type": "application/json"},
        )
        return url
        
    def calculate_size_of_file(self, file_path: str):
        data = open(file_path, "rb").read()
        file_size = sys.getsizeof(data)
        print(file_size)
        return file_size
    
    def generate_md5_for_file(self, file_path: str):
        data = open(file_path, "rb").read()
        md5sum = hashlib.md5(data).hexdigest()
        print(md5sum)
        return md5sum
    
    def load_minio_manifest_file(self, manifest_file: str) -> dict:
        with open(manifest_file, "r") as f:
            reader = DictReader(f, delimiter="\t")
            return [row for row in reader]
        
    def create_minio_manifest_file(self, output_manifest_file: str):
        minio_objects = self.get_minio_objects()
        with open(output_manifest_file, "w") as f:
            writer = DictWriter(f, fieldnames=self.MANIFEST_FIELDS, delimiter="\t")
            writer.writeheader()
            for minio_object in minio_objects:
                writer.writerow(minio_object)
        print("Created manifest file and saved it in current working directory.")
        return "Created manifest file and saved it in current working directory."

    def update_minio_manifest_file(self, old_manifest_file: str):
        minio_objects = self.get_minio_objects()
        if len(minio_objects) == 0:
            print("There are no objects in the MinIO bucket.")
            return "There are no objects in the MinIO bucket."
        
        updated_minio_objects = []
        existing_minio_objects = self.load_minio_manifest_file(old_manifest_file)
        if len(existing_minio_objects) == 0:
            print("There are no entries in the manifest file. Creating a new manifest file...")
            return self.create_minio_manifest_file(old_manifest_file)
        
        existing_minio_objects_md5sum_values = [object["md5"] for object in existing_minio_objects]
        for obj in minio_objects:
            if str(obj["md5"]) in existing_minio_objects_md5sum_values:
                continue            
            updated_minio_objects.append({
                "guid": obj["guid"],
                "file_name": obj["file_name"],
                "md5": obj["md5"],
                "size": obj["size"],
                "acl": ["*"],
                "urls": obj["urls"],
            })
        with open(old_manifest_file, "a") as f:
            writer = DictWriter(f, fieldnames=self.MANIFEST_FIELDS, delimiter="\t")
            for minio_object in updated_minio_objects:
                writer.writerow(minio_object)
        print("Updated manifest file.")
        return "Updated manifest file."
        
    def create_indexd_manifest(self, manifest_file: str):
        auth = Gen3Auth(refresh_file=self.gen3_credentials)
        self.update_minio_manifest_file(manifest_file)
        indexd_manifest = index_object_manifest(
            commons_url=self.gen3_commons_url,
            manifest_file=manifest_file,
            thread_num=8,
            auth=auth,
            replace_urls=True,
            manifest_file_delimiter="\t", # put "," if the manifest is a CSV file
            submit_additional_metadata_columns=False, # set to True to submit additional metadata to the metadata service
        )

        print(indexd_manifest)
    
    def get_all_records(self):
        auth = Gen3Auth(refresh_file=self.gen3_credentials)
        gen3_index = Gen3Index(auth)
        return gen3_index.get_all_records()
           
    def json_dumps(self, data):
        return json.dumps({k: v for (k, v) in data.items() if v is not None})
        
    def create_blank_index(self, file_name):
        url = f"{self.gen3_commons_url}/index/index/blank"
        json = {"uploader": self.gen3_username, "file_name": file_name}
        data = self.json_dumps(json)
        access_token = self.get_gen3_commons_access_token()
        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.post(
            url,
            data=data,
            headers=headers,
            verify=False,
        )
        
        # The response.text has the following structure:
        # {
        #     "baseid": "79822e9d-ddd7-48dc-a0d1-d18f4fa9d77e",
        #     "did": "PREFIX/2e9514a1-a3aa-4520-8011-806b74da2e95",
        #     "rev": "c8056f0d"
        # }
        
        return response
        
    def update_blank_index(self, did, rev, minio_object):
        auth = Gen3Auth(refresh_file=self.gen3_credentials)
        url = f"{self.gen3_commons_url}/index/index/blank/{did}"
        
        access_token = self.get_gen3_commons_access_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        params = {"rev": rev}
        json = {
            "hashes": {
                "md5": minio_object["md5"]
            },
            "size": minio_object["size"]
        }
        # if minio_object["urls"]:
        #     json["urls"] = minio_object["urls"]
        # if minio_object["acl"]:
        #     json["authz"] = minio_object["acl"]
        # if minio_object["authz"]:
        #     json["authz"] = minio_object["authz"]
        data = self.json_dumps(json)

        response = requests.put(
            url,
            data=data,
            params=params,
            # auth=auth,
            headers=headers,
            verify=False,
        )
        
        print(response)
    
    def get_gen3_presigned_url(self, guid):
        auth = Gen3Auth(refresh_file=self.gen3_credentials)
        gen3_file = Gen3File(endpoint=self.gen3_commons_url, auth_provider=auth)
        gen3_presigned_url = gen3_file.get_presigned_url(guid)
        return gen3_presigned_url
        
    def delete_record_by_guid(self, guid, rev):
        auth = Gen3Auth(refresh_file=self.gen3_credentials)
        url = f"{self.gen3_commons_url}/index/index/{guid}"
        params = {"rev": rev}
        headers = {
            "Content-Type": "application/json",
        }
        try:
            print(f"Deleting file with GUID '{guid}' and rev '{rev}'...")
            response = requests.delete(
                url,
                params=params,
                auth=auth,
                headers=headers,
                verify=False,
            )
        except:
            print(f"Failed to delete file with GUID '{guid}'")
        
        print(response)
        
        
    def upload_file_and_update_record(self, file_path: str, old_manifest_file):
        print("Extracting file name from file path...")
        upload_path = Path(file_path)
        file_name = upload_path.name
        size_of_file = self.calculate_size_of_file(file_path)
        print(f"Name of file to be uploaded: '{file_name}'.")
        
        print("Checking if file already exists in MinIO bucket...")
        file_exists = self.check_if_object_is_in_minio_bucket(file_name)
        if file_exists:
            print(f"File '{file_name}' already exists in MinIO bucket. Process stopped.")
            return f"File '{file_name}' already exists in MinIO bucket. Process stopped."
        try:
            print(f"Creating blank record for '{file_name}'...")
            blank_index_response = self.create_blank_index(file_name)
            blank_index_json_response = blank_index_response.json()
            did = str(blank_index_json_response["did"])
            rev = str(blank_index_json_response["rev"])
            path_in_minio_bucket = os.path.join(did, file_name)
            
            try:
                print("Uploading file to MinIO bucket...")
                result = self.client.fput_object(
                    bucket_name=self.minio_bucket_name, 
                    object_name=path_in_minio_bucket, 
                    file_path=file_path,
                )
                
                minio_object = {
                    "guid": str(uuid4()),
                    "file_name": file_name,
                    "md5": str(result.etag,).strip('"'),
                    "size": size_of_file,
                    "acl": ["*"],
                    "urls": [f"https://{self.minio_api_endpoint}/{self.minio_bucket_name}/{path_in_minio_bucket}"],
                }
                print(minio_object)
                print(f"Object '{minio_object["file_name"]}' has been uploaded")
            except:
                print(f"Failed to upload file '{minio_object["file_name"]}'")
            
            print("Updating manifest with metadata about newly uploaded minio object...")
            self.update_minio_manifest_file(old_manifest_file)
            
            try:
                if did and rev:
                    print(f"Updating indexd database record for uploaded file with did '{did}' and rev '{rev}'...")
                    self.update_blank_index(did, rev, minio_object)
            except:
                print(f"Failed to update blank index with GUID of '{minio_object["file_name"]}'.")
        except:
            print(f"Failed to create blank index for file '{file_name}'.")
               
        return f"File '{file_name}' uploaded successfully and indexd database records updated."
    
    # download data of an object from MinIO bucket
    def download_file_from_minio_bucket(self, minio_object_name: str, prefix: str, guid: str, file_path: str):
        minio_download_path = f"/{prefix}/{guid}/{minio_object_name}"
        self.client.fget_object(
            bucket_name=self.minio_bucket_name, 
            object_name=minio_download_path, 
            file_path=file_path
        )
        return f"Downloaded MinIO object {minio_object_name} to {file_path} from bucket {self.minio_bucket_name}."
                        
if __name__ == '__main__':
    gen3_minio_client = Gen3MinioClient()
    gen3_minio_client.download_file_from_minio_bucket(
        minio_object_name="Albert-Camus-The-Stranger.pdf",
        prefix="PREFIX", 
        guid="d21d4089-b640-4c1c-ac6f-7968d934f9cc", 
        file_path="./minio_downloads/Albert-Camus-The-Stranger.pdf"
    )

    