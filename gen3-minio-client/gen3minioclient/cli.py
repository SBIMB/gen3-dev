"""
The command-line interface for the gen3minioclient
"""
import argparse
from gen3minioclient import create_minio_manifest_file
from gen3minioclient import update_minio_manifest_file
from gen3minioclient import upload_file_and_update_record
from gen3minioclient import delete_record_by_guid
from gen3minioclient import configure_gen3_minio_client

def main():
    parser = argparse.ArgumentParser(
        description="An application for interacting with a Gen3 instance and an on-prem MinIO bucket."
    )
    
    parser.add_argument(
        "--createManifestFile",
        help=(
            "The './output_manifest_file.tsv' will be saved to the current working directory."
        )
    )
    
    parser.add_argument(
        "--updateManifestFile",
        help=(
            "The './output_manifest_file.tsv' will be updated, or recreated if it does not exist."
        )
    )
    
    parser.add_argument(
        "--filePath",
        "--manifestFile",
        help=(
            "Specify the file path for the file to be uploaded to a MinIO bucket. The './output_manifest_file.tsv' will be updated, or recreated if it does not exist."
        )
    )
    
    parser.add_argument(
        "--guid",
        "--rev",
        help=(
            "DELETE a record from the Sheepdog database by providing the GUID and revision number."
        )
    )
    
    parser.add_argument(
        "--pathToGen3MinioCreds",
        help=(
            "Provide path to 'gen3-minio-credentials.json' so that the CLI tool can communicate with Gen3 and MinIO."
        )
    )
    
    args = parser.parse_args()
    
    create_minio_manifest_file(output_manifest_file=args.createManifestFile)
    update_minio_manifest_file(old_manifest_file=args.updateManifestFile)
    upload_file_and_update_record(file_path=args.filePath, old_manifest_file=args.manifestFile)
    delete_record_by_guid(guid=args.guid, rev=args.rev)
    configure_gen3_minio_client(gen3_minio_json_file=args)

if __name__ == "__main__":
    main()