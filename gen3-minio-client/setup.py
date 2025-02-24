import setuptools

with open("README.md", "r", encoding="utf-8") as fhand:
    long_description = fhand.read()

setuptools.setup(
    name="gen3-minio-client",
    version="0.0.1",
    author="RWCannell",
    author_email="regancannell@gmail.com",
    description=("An application for interacting with a Gen3 "
                "instance and an on-prem MinIO bucket."),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/RWCannell/gen3-minio-client",
    project_urls={
        "Issues": "https://github.com/RWCannell/gen3-minio-client/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "requests",
        "logging",
        "os",
        "sys",
        "hashlib",
        "json",
        "re",
        "pathlib",
        "csv",
        "datetime",
        "uuid",
        "minio"
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "gen3minioclient = gen3minioclient.cli:main",
        ]
    }
)
