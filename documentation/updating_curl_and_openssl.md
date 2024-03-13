## Updating cURL and OpenSSL
To update `curl` to version 8.4.0, download the `.zip` file using the following command:
```bash
wget https://curl.se/download/curl-8.4.0.zip
```
This binary file needs to be unzipped:
```bash
unzip curl-8.4.0.zip
```
A directory called `curl-8-4-0` will be created as a part of the unzipping process. Inside this directory, the installation process needs to take place:
```bash
cd curl-8.4.0
./configure --prefix=$HOME/curl --with-ssl
make
make install
```
If trying to install `curl` with a specific version of `openssl` by using the flag `--with-openssl` and an error occurs, then a manual installation of a newer version of `openssl` is required. To complete this process, begin by navigating to the `/usr/local/src/` directory:
```bash
cd /usr/local/src/
```
When inside this directory, fetch the desired binary of `openssl`:
```bash
sudo wget https://www.openssl.org/source/openssl-3.2.0.tar.gz
```
The `tar` package needs to be unpacked:
```bash
sudo tar -xf openssl-3.2.0.tar.gz
```
Enter the directory of the package:
```bash
cd openssl-3.2.0
```
Run the following command to install the configuration of `openssl`:
```bash
sudo ./config --prefix=/usr/local/ssl --openssldir=/usr/local/ssl shared zlib
```
Lastly, compile and install `openssl` with:
```bash
sudo make && sudo make install
```
If the installation is successful, the installed version of `openssl` can be seen with:
```bash
openssl version -a
```