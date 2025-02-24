## Gen3-Minio Client
### Introduction
A running Gen3 instance is required in order for this application to be purposeful. The `gen3-minio-client` is a Python application that's main purpose is to allow for users to upload data to an on-prem MinIO bucket. The [gen3-client](https://github.com/uc-cdis/cdis-data-client) written in Go uploads data successfully when Gen3 is configured to use an Amazon S3 bucket. However, it fails to upload data to an on-prem MinIO bucket.    

The entire upload process is intended to be as follows:
- create a [blank record](https://uc-cdis.github.io/gen3sdk-python/_build/html/indexing.html#gen3.index.Gen3Index.create_blank) in the `indexd` database   
- generate a presigned URL for the data to be [uploaded](https://uc-cdis.github.io/gen3sdk-python/_build/html/file.html#gen3.file.Gen3File.upload_file)   
- update the blank record with a [GUID](https://uc-cdis.github.io/gen3sdk-python/_build/html/file.html#gen3.file.Gen3File.upload_file_to_guid) by making a PUT request to the `/index​/blank​/{GUID}` endpoint   
- [map](https://uc-cdis.github.io/gen3sdk-python/_build/html/submission.html#gen3.submission.Gen3Submission.submit_record) the uploaded data to the existing graph   

### Environment Variables
Environment variables can be stored inside a `.env` file that is to be stored in the root of this directory. The following variables need to be set:
```env
MINIO_BUCKET_NAME="my-minio-bucket"
MINIO_ENDPOINT="www.miniolocal.co.za"
MINIO_ACCESS_KEY="minioaccesskey"
MINIO_SECRET_KEY="miniosecretkey"
UPLOAD_PATH="/path/to/file"
GEN3_CREDENTIALS_PATH="/gen3-credentials.json"
GEN3_COMMONS_URL="https://www.gen3local.co.za"
```

### Running the Application
To run the application in a virtual environment, the following command can be used:
```bash
python3 -m venv venv
```
This path should be placed inside the `.gitignore` file so that it doesn't get committed to Github. We need to run individual Python scripts from inside the virtual environment:
```bash
source venv/bin/activate
```
The `get_minio_presigned_url.py` script can be run with:
```bash
python3 get_minio_presigned_url.py
```
NOTE: After installing all the dependencies, a `requirements.txt` file can be generated with the command:
```bash
pip freeze > requirements.txt
```

### Running as a CLI Tool   
NOTE: this is still a work in progress.   

In order to initialise the client, a JSON input needs to be provided. This JSON should contain the following fields:
```json
{
    "api_key": "gen3ApiKey", // optional
    "key_id": "gen3ApiKeyId", // optional
    "minio_bucket_name": "gen3-minio-bucket-name",
    "minio_endpoint": "gen3-minio-endpoint",
    "minio_access_key": "minioAccessKey",
    "minio_secret_key": "minioSecretKey",
    "gen3_credentials_path": "gen3-credentials.json",
    "gen3_commons_url": "https://gen3.com",
    "gen3_username": "name@example.com",
    "manifest_file_location": "data/manifest/output_manifest_file.tsv" // optional
}
```

### Attributes of MinIO Objects
The attributes of an object from a MinIO bucket looks as follows when calling the `.__dir__()` method:
```python
['_bucket_name', '_object_name', '_last_modified', '_etag', '_size', '_metadata', '_version_id', '_is_latest', '_storage_class', '_owner_id', '_owner_name', '_content_type', '_is_delete_marker', '_tags', '__module__', '__doc__', '__init__', 'bucket_name', 'object_name', 'is_dir', 'last_modified', 'etag', 'size', 'metadata', 'version_id', 'is_latest', 'storage_class', 'owner_id', 'owner_name', 'is_delete_marker', 'content_type', 'tags', 'fromxml', '__dict__', '__weakref__', '__new__', '__repr__', '__hash__', '__str__', '__getattribute__', '__setattr__', '__delattr__', '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__', '__reduce_ex__', '__reduce__', '__getstate__', '__subclasshook__', '__init_subclass__', '__format__', '__sizeof__', '__dir__', '__class__']
```
We can use these attributes for each object to generate a manifest file for the MinIO bucket. The manifest file needs to have the following five columns:   

| GUID | md5 | size | acl | url |
|------|-----|------|-----|-----|

The MD5 for an object can be determined by using the following Python code snippet:
```python
import requests
import sys
import hashlib

# either provide a url or a file name
data = requests.get(url).content
data = open("path/to/file", "rb").read()

file_size = sys.getsizeof(data)
md5sum = hashlib.md5(data).hexdigest()
print(file_size, md5sum)
```