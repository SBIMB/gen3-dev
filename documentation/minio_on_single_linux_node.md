## MinIO on Single Node (Linux)
We'll be installing a single-node-single-drive (SNSD) instance of [Minio](https://min.io/docs/minio/linux/index.html) on a bare-metal Ubuntu machine (hostname `cloud05`). To install on an Ubuntu machine, run the following:
```bash
wget https://dl.min.io/server/minio/release/linux-amd64/archive/minio_20240310025348.0.0_amd64.deb -O minio.deb
sudo dpkg -i minio.deb
```
A minio directory should be created with the following commands:
```bash
mkdir ~/minio
minio server ~/minio --console-address :9001
```
The latter command might cause some warnings to be generated, such as changing the username and password of the admin user.
![MinIO Default Credentials](public/assets/images/minio-default-credentials.png "MinIO Default Credentials") 

Instead of using `root` to work with MinIO, it is better to create a system group and user:
```bash
sudo groupadd -r minio-user
sudo useradd -M -r -g minio-user minio-user
```
A data directory needs to be created for where all the objects will be stored:
```bash
sudo mkdir /mnt/data
```
The ownership of this data directory needs to be given to the user and group:
```bash
sudo chown minio-user:minio-user /mnt/data
```
Environment variables need to be added for MinIO. Use `nano` or `vim` to open your preferred text editor and populate it with the following environment variables:
```bash
sudo vim /etc/default/minio
```
```txt
MINIO_VOLUMES="/mnt/data"

MINIO_OPTS="--certs-dir /home/regan/.minio/certs --console-address :9001"

MINIO_ROOT_USER=minioadmin

MINIO_ROOT_PASSWORD=minioadmin
```
We need to ensure that the firewall allows for ports 9000 and 9001 to be open. Since we are using `iptables`, we use:
```bash
sudo iptables -I INPUT -p tcp -s 0.0.0.0/0 --dport 9000 -j ACCEPT
sudo iptables -I INPUT -p tcp -s 0.0.0.0/0 --dport 9001 -j ACCEPT
```
Now we need to create a self-signed certificate for our MinIO server. First, we download the binary file from `certgen`:
```bash
wget https://github.com/minio/certgen/releases/download/v1.2.1/certgen_1.2.1_linux_amd64.deb
```
After the download is complete, install the package with:
```bash
sudo dpkg -i certgen_1.2.1_linux_amd64.deb
```
If the installation has been successful, then running `certgen -h` will output a list of commands.   

To generate a certificate for the host machine, run:
```bash
sudo certgen -host cloud05.core.wits.ac.za, 146.141.240.75	
```
A new certificate, `public.crt` and `private.key`, should have been created. These files need to be moved to the `/home/regan/.minio/certs` directory:
```bash
sudo mkdir -p /home/regan/.minio/certs
sudo mv private.key public.crt /home/regan/.minio/certs
```
Ownership of both files need to be given to the MinIO user and group:
```bash
sudo chown minio-user:minio-user /home/regan/.minio/certs/private.key
sudo chown minio-user:minio-user /home/regan/.minio/certs/public.crt
```
We can start the MinIO server using `systemd` with the following command:
```bash
sudo systemctl start minio
```
We can check the status with:
```bash
sudo systemctl status minio
```
![MinIO Start Up Status](public/assets/images/minio-start-up-status.png "MinIO Start Up Status") 

As can be seen in the screenshot above, the MinIO urls are using HTTP instead of HTTPS. This means that something has gone wrong with the certification creation process. We will need to investigate why this is the case. At least the MinIO UI appears and we can login:   

![MinIO Login Page](public/assets/images/minio-login-page.png "MinIO Login Page") 
