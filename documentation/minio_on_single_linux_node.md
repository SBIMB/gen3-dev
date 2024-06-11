## MinIO on Single Node (Linux)
We'll be installing a single-node-single-drive (SNSD) instance of [Minio](https://min.io/docs/minio/linux/index.html) on a bare-metal Ubuntu machine (hostname `cloud05`). To install on an Ubuntu machine, run the following:
```bash
wget https://dl.min.io/server/minio/release/linux-amd64/minio
```
After the download is complete, we make the downloaded file executable with:
```bash
sudo chmod +x ./minio
```
Now we can move the executable file to the `/usr/local/bin` directory:
```bash
sudo mv ./minio /usr/local/bin
``` 
Instead of using `root` to work with MinIO, it is better to create a system group and user:
```bash
sudo useradd -r minio-user -s /sbin/nologin
```
We need to give this user permissions to the `minio` executable file:
```bash
sudo chown minio-user:minio-user /usr/local/bin/minio
```
A data directory needs to be created for where all the objects will be stored:
```bash
sudo mkdir /usr/local/share/minio
```
The ownership of this data directory needs to be given to the user and group:
```bash
sudo chown minio-user:minio-user /usr/local/share/minio
```
Environment variables need to be added for MinIO. We'll create another directory for this:
```bash
sudo mkdir /etc/minio
sudo chown minio-user:minio-user /etc/minio
```
Use `nano` or `vim` to open your preferred text editor and populate it with the following environment variables:
```bash
sudo vim /etc/default/minio
```
```txt
MINIO_ACCESS_KEY="some_access_key"
MINIO_SECRET_KEY="some_secret_key"

MINIO_VOLUMES="/usr/local/share/minio/"
MINIO_OPTS="-C /etc/minio --address 146.141.240.75:9000 --console-address 146.141.240.75:9001"
```
We need to ensure that the firewall allows for ports 9000 and 9001 to be open. Since we are using `iptables`, we use:
```bash
sudo iptables -I INPUT -p tcp -s 0.0.0.0/0 --dport 9000 -j ACCEPT
sudo iptables -I INPUT -p tcp -s 0.0.0.0/0 --dport 9001 -j ACCEPT
```
For MinIO to be started whenever the system boots up, we need to install the following script:
```bash
curl -O https://raw.githubusercontent.com/minio/minio-service/master/linux-systemd/minio.service
```
This downloaded script needs to be moved to the `systemd` directory:
```bash
sudo mv minio.service /etc/systemd/system
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
sudo certgen -host "146.141.240.75,cloud05.core.wits.ac.za"
```
A new certificate, `public.crt` and `private.key`, should have been created. These files need to be moved to the `/etc/minio/` directory:
```bash
sudo mv private.key public.crt /etc/minio/
```
Ownership of both files need to be given to the MinIO user and group:
```bash
sudo chown minio-user:minio-user /etc/minio/private.key
sudo chown minio-user:minio-user /etc/minio/public.crt
```
To apply the changes, we need to reload the `systemd` service files:
```bash
sudo systemctl daemon-reload
sudo systemctl enable minio
```
We can now start MinIO with:
```bash
sudo systemctl start minio
```
We can check the status with:
```bash
sudo systemctl status minio
```
![MinIO Status](../public/assets/images/minio-status.png "MinIO Status")    

We should also see that MinIO can be accessed on HTTPS. This is good news, since it means that the generation of SSL certificates was a success.   

![MinIO HTTPS Login](../public/assets/images/minio-https-login.png "MinIO HTTPS Login") 

Once logged in, we can create a bucket called `gen3-minio-bucket` that will be used for all the Gen3 file uploads.   

![Gen3 MinIO Bucket](../public/assets/images/gen3-minio-bucket.png "Gen3 MinIO Bucket")    

We can also check the health status of the MinIO API with 
```bash
curl -I https://cloud05.core.wits.ac.za/minio/health/live -k
```
If the response has status code _200_, then all is well.

### Installing the MinIO Client
To download and install the MinIO client, run the following:
```bash
curl https://dl.min.io/client/mc/release/linux-amd64/mc \
  --create-dirs \
  -o $HOME/minio-binaries/mc

chmod +x $HOME/minio-binaries/mc
export PATH=$PATH:$HOME/minio-binaries/

mc --help
```
Then set an alias, provide the hostname, and give both the access keys and secret keys, respectively:
```bash
bash +o history
mc alias set ALIAS HOSTNAME ACCESS_KEY SECRET_KEY
bash -o history
```
The following is an example:
```bash
mc alias set minio-user https://cloud05.core.wits.ac.za:9000 my_access_key my_secret_key
```
The connection to the MinIO server can be tested with:
```bash
mc admin info minio-user
```

### Installing the AWS CLI
The AWS CLI can be quickly downloaded and installed with
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```
Once installed, credentials need to be configure with:
```bash
aws configure
```
We can list the MinIO buckets (which are S3 buckets) with the following command:
```bash
aws --endpoint-url https://ip-address:9000 s3 ls --no-verify-ssl
```
To see contents within a specific bucket, we run
```bash
aws --endpoint-url https://ip-address:9000 s3 ls s3://my-minio-bucket --no-verify-ssl
```
To add an **S3** alias for MinIO, we need to run
```bash
mc alias set s3 https://s3.region.amazonaws.com MINIO_ACCESS_KEY MINIO_SECRET_KEY
```
Now third party applications should be able to interact with the MinIO buckets as if it's an AWS S3 bucket.   

### Publishing Upload Events to RabbitMQ
Update the environment variables by opening `/etc/default/minio` and adding the following:
```txt
MINIO_NOTIFY_AMQP_ENABLE="on"
MINIO_NOTIFY_AMQP_URL="amqp://<username>:<password>@<ip-address>:<port>/<vhost>"
```
The `AMQP` url comes from the RabbitMQ instance that needs to be setup.  The details for setting up RabbitMQ can be found over [here](./setting_up_rabbitmq.md).
