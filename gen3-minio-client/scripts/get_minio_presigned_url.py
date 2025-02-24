from datetime import timedelta
from minio import Minio
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()
 
# Access environment variables
minio_bucket_name = os.getenv("MINIO_BUCKET_NAME")
minio_api_endpoint = os.getenv("MINIO_ENDPOINT")
minio_access_key = os.getenv("MINIO_ACCESS_KEY")
minio_secret_key = os.getenv("MINIO_SECRET_KEY")
upload_path = os.getenv("UPLOAD_PATH")

client = Minio(
    minio_api_endpoint,
    access_key=minio_access_key,
    secret_key=minio_secret_key,
    cert_check=False,
)

# Get presigned URL string to upload file in
# bucket with response-content-type as application/json
# and one day expiry.
url = client.get_presigned_url(
    "PUT",
    minio_bucket_name,
    upload_path,
    expires=timedelta(days=1),
    response_headers={"response-content-type": "application/json"},
)

print(url)
