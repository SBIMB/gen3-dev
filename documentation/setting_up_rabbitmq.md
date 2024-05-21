## RabbitMQ
To setup **RabbitMQ** on `cloud05`, use the [rabbitmq_installation.sh script](../rabbitmq/rabbitmq_installation.sh) found inside this repository (it comes directly from the [rabbitmq documentation website](https://www.rabbitmq.com/docs/install-debian#apt-quick-start-cloudsmith)):
```bash
sudo bash rabbitmq_installation.sh
```   

If the script runs successfully to completion, the status of `rabbitmq` can be checked with:
```bash
systemctl status rabbitmq-server.service
```
and the ouput should contain _active_.    

![RabbitMQ Status](../public/assets/images/rabbitmq-status.png "RabbitMQ Status")   

To see if `rabbitmq` is enabled, simply run:
```bash
systemctl is-enabled rabbitmq-server.service
```
and the output should be `enabled`. If it is _not_ enabled, it can be enabled with:
```bash
sudo systemctl enable rabbitmq-server
```
For ease of use and convenience, the UI management dashboard can be enabled with
```bash
sudo rabbitmq-plugins enable rabbitmq_management
```
The UI management dashboard should be accessible on port `15672`, so the web address would be `http://<server-ip>:15672`.   

![RabbitMQ Login Page](../public/assets/images/rabbitmq-login-page.png "RabbitMQ Login Page") 

Create an admin user and set a good password for the admin user:
```bash
sudo rabbitmqctl add_user admin <some_password>
```
Set tags for the admin user:
```bash
sudo rabbitmqctl set_user_tags admin administrator
```
It is now possible to login with user `admin` and the password that was set above:   

![RabbitMQ Landing Page](../public/assets/images/rabbitmq-landing-page.png "RabbitMQ Landing Page")   

As root, a user can be added with:
```bash
sudo rabbitmqctl add_user 'new-user' 'NewPassword'
```
A list of users can be retrieved with:
```bash
sudo rabbitmqctl list_users
```
A user can be deleted with:
```bash
sudo rabbitmqctl delete_user 'new-user'
```
A list of RabbitMQ vhosts can be retrieved with:
```bash
sudo rabbitmqctl -q --formatter=pretty_table list_vhosts name description tags default_queue_type
```
We can create a new virtual host using the admin user credentials as follows:
```bash
curl -u admin-user:admin-password -X PUT http://146.141.240.75:15672/api/vhosts/minio-vhost \
                           -H "content-type: application/json" \
                           --data-raw '{"description": "Virtual host for MinIO bucket events", "tags": "minio,gen3-minio-bucket", "default_queue_type": "quorum"}'
```
A user can be granted permissions on a virtual host with the following command:
```bash
sudo rabbitmqctl set_permissions -p "minio-vhost" "new-user" ".*" ".*" ".*"
```
A vhost can be deleted with the CLI tools as follows:
```bash
sudo rabbitmqctl delete_vhost qa1
```
or with the API:
```bash
curl -u admin-user:admin-password -X DELETE http://rabbitmq.local:15672/api/vhosts/minio-vhost
```
To see the permissions associated with a virtual host, the following command can be run:
```bash
sudo rabbitmqctl list_permissions --vhost minio-vhost
```
To form a connection to a virtual host with an `amqp` endpoint, the following URI should be used:
```bash
"amqp://new-user:NewPassword@146.141.240.75:5672/minio-vhost"
```
It takes the form
```bash
amqp://<username>:<password>@<ip-address>:<port>/<vhost>
```