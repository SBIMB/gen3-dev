from gen3minioclient.gen3minioclient import Gen3MinioClient

if __name__ == '__main__':
    Gen3MinioClient.upload_file_and_update_record(
        file_path="./../data/uploads/20-Industrial-Rev.pdf",
        old_manifest_file="./../data/manifest/output_manifest_file.tsv"
)
    