import logging
import os
import requests
import sys
import json
from pathlib import Path

from uuid import uuid4
from gen3.auth import Gen3Auth
from gen3.tools.indexing.index_manifest import index_object_manifest
from gen3.index import Gen3Index
from gen3.file import Gen3File

from gen3minioclient.minioclient import minio_client

logging.basicConfig(filename="output.log", level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

class Gen3Client: 
    def __init__(self, gen3_minio_json_file):
        # opening JSON file containing credentials
        f = open(gen3_minio_json_file)

        # returns JSON object as 
        # a dictionary
        json_values = json.load(f)
        
        if not json_values["gen3_commons_url"] or json_values["gen3_commons_url"] == "":
            return f"'gen3_commons_url' attribute has not been specified"
        
        if not json_values["gen3_username"] or json_values["gen3_username"] == "":
            return f"'gen3_username' attribute has not been specified"
        
        if not (json_values["gen3_api_key"]) or json_values["gen3_api_key"] == "":
            return f"'gen3_api_key' attribute has not been specified"
        if not (json_values["gen3_key_id"]) or json_values["gen3_key_id"] == "":
            return f"'gen3_key_id' attribute has not been specified"
        
        self.gen3_commons_url = json_values["gen3_commons_url"]
        self.gen3_username = json_values["gen3_username"]
        self.gen3_api_key = json_values["gen3_api_key"]
        self.gen3_key_id = json_values["gen3_key_id"]
    
        return f"Credentials for the 'Gen3Client' has been successfully initialised."
        
        
    def get_gen3_commons_access_token(self):
        url = f"{self.gen3_commons_url}/user/credentials/cdis/access_token"

        data = {
            "api_key": self.gen3_api_key,
            "key_id": self.gen3_key_id
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
        
    def create_indexd_manifest(self, manifest_file: str):
        auth = Gen3Auth(refresh_file={
            "api_key": self.gen3_api_key,
            "key_id": self.gen3_key_id
        })
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
        auth = Gen3Auth(refresh_file={
            "api_key": self.gen3_api_key,
            "key_id": self.gen3_key_id
        })
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
        auth = Gen3Auth(refresh_file={
            "api_key": self.gen3_api_key,
            "key_id": self.gen3_key_id
        })
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
        auth = Gen3Auth(refresh_file={
            "api_key": self.gen3_api_key,
            "key_id": self.gen3_key_id
        })
        gen3_file = Gen3File(endpoint=self.gen3_commons_url, auth_provider=auth)
        gen3_presigned_url = gen3_file.get_presigned_url(guid)
        return gen3_presigned_url
        
    def delete_record_by_guid(self, guid, rev):
        auth = Gen3Auth(refresh_file={
            "api_key": self.gen3_api_key,
            "key_id": self.gen3_key_id
        })
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
        size_of_file = minio_client.calculate_size_of_file(file_path)
        print(f"Name of file to be uploaded: '{file_name}'.")
        
        print("Checking if file already exists in MinIO bucket...")
        file_exists = minio_client.check_if_object_is_in_minio_bucket(file_name)
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
                result = minio_client.client.fput_object(
                    bucket_name=minio_client.minio_bucket_name, 
                    object_name=path_in_minio_bucket, 
                    file_path=file_path,
                )
                
                minio_object = {
                    "guid": str(uuid4()),
                    "file_name": file_name,
                    "md5": str(result.etag,).strip('"'),
                    "size": size_of_file,
                    "acl": ["*"],
                    "urls": [f"https://{minio_client.minio_api_endpoint}/{minio_client.minio_bucket_name}/{path_in_minio_bucket}"],
                }
                print(minio_object)
                print(f"Object '{minio_object["file_name"]}' has been uploaded")
            except:
                print(f"Failed to upload file '{minio_object["file_name"]}'")
            
            print("Updating manifest with metadata about newly uploaded minio object...")
            minio_client.update_minio_manifest_file(old_manifest_file)
            
            try:
                if did and rev:
                    print(f"Updating indexd database record for uploaded file with did '{did}' and rev '{rev}'...")
                    self.update_blank_index(did, rev, minio_object)
            except:
                print(f"Failed to update blank index with GUID of '{minio_object["file_name"]}'.")
        except:
            print(f"Failed to create blank index for file '{file_name}'.")
                
        return f"File '{file_name}' uploaded successfully and indexd database records updated."
    