from csv import  DictReader, DictWriter
import sys
import logging
from uuid import uuid4
from minio import Minio
from dotenv import load_dotenv
import os

from boto3 import client, resource
from gen3.auth import Gen3Auth
from gen3.tools.indexing.index_manifest import index_object_manifest

logging.basicConfig(filename="output.log", level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

load_dotenv()
 
MANIFEST = "./manifest.tsv"
COMPLETED = "./completed.tsv"

MANIFEST_FIELDS = ['GUID', 'md5', 'size', 'acl', 'url']

minio_bucket_name = os.getenv("MINIO_BUCKET_NAME")
minio_api_endpoint = os.getenv("MINIO_ENDPOINT")
minio_access_key = os.getenv("MINIO_ACCESS_KEY")
minio_secret_key = os.getenv("MINIO_SECRET_KEY")
gen3_commons_url = os.getenv("GEN3_COMMONS_URL")
gen3_credentials = os.getenv("GEN3_CREDENTIALS_PATH")

client = Minio(
    minio_api_endpoint,
    access_key=minio_access_key,
    secret_key=minio_secret_key,
    cert_check=False,
)

# def get_minio_objects(bucket: str, prefix: str) -> dict:
#     s3 = resource("s3")
#     bucket = s3.Bucket(bucket)
#     return {obj.key: obj for obj in bucket.objects.filter(Prefix=prefix)}

objects = client.list_objects(minio_bucket_name)
for obj in objects:
    # print(obj.info())
    print(obj.object_name)

# # List objects information
# def list_minio_objects(bucket_name: str):
#     objects = client.list_objects(bucket_name)
#     for obj in objects:
#         print(obj)

# # List objects information whose names starts with "my/prefix/"
# def list_minio_objects_by_prefix(bucket_name: str, prefix: str):
#     objects = client.list_objects(bucket_name, prefix="PREFIX/")
#     for obj in objects:
#         print(obj)

# # List objects information recursively
# def list_minio_objects_recursively(bucket_name: str):
#     objects = client.list_objects(bucket_name, recursive=True)
#     for obj in objects:
#         print(obj)

# # List objects information recursively whose names starts with
# # "my/prefix/"
# def list_minio_objects_by_prefix_recursively(bucket_name: str, prefix: str):
#     objects = client.list_objects(
#         minio_bucket_name, prefix=prefix, recursive=True,
#     )
#     for obj in objects:
#         print(obj)


# def load_old_manifest(filename: str = COMPLETED) -> dict:
#     with open(filename, "r") as f:
#         reader = DictReader(f, delimiter="\t")
#         return {row["GUID"]: row for row in reader}


# def create_manifest(filename, minio_objects: dict) -> None:
#     with open(filename, "w") as f:
#         writer = DictWriter(f, fieldnames=MANIFEST_FIELDS, delimiter="\t")
#         writer.writeheader()
#         for key, minio_object in minio_objects.items():
#             writer.writerow(minio_object)


# def main():
#     auth = Gen3Auth(refresh_file=gen3_credentials)

#     already_uploaded = load_old_manifest()
#     print(already_uploaded)

#     minio_objects = get_minio_objects(bucket=minio_bucket_name, prefix="PREFIX")
#     new_manifest_dict = {}
#     for key, minio_object in minio_objects.items():
#         if key in already_uploaded:
#             continue
#         new_manifest_dict[key] = {
#             "GUID": str(uuid4()),
#             "md5": str(minio_object.e_tag).strip('"'),
#             "size": minio_object.size,
#             "acl": "[*]",
#             "url": f"https://{minio_api_endpoint}/{key}"
#         }
#     create_manifest(MANIFEST, new_manifest_dict)

#     # use basic auth for admin privileges in indexd
#     #auth = ("fence", "from fence secret")

#     indexd_manifest = index_object_manifest(
#         commons_url=gen3_commons_url,
#         manifest_file=MANIFEST,
#         thread_num=8,
#         auth=auth,
#         replace_urls=True,
#         manifest_file_delimiter="\t", # put "," if the manifest is csv file
#         submit_additional_metadata_columns=False, # set to True to submit additional metadata to the metadata service
#     )

#     print(indexd_manifest)