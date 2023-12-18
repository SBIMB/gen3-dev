# k3s Setup and Configuration on Ubuntu 22.04
## Introduction
We will be using a virtual machine with operating system _Ubuntu 22.04.2 LTS_, kernel _GNU/Linux 5.15.0-73-generic_, and architecture _x86-64_ to setup and configure a Kubernetes cluster using the [k3s distribution](https://docs.k3s.io/). We'll go with a K3s single-server setup (we might expand at a later date).        
![K3s Single Server Setup](/public/assets/images/k3s-architecture.png "K3s Single Server Setup")   

The ultimate goal for having this cluster up and running is to administer and orchestrate the [Gen3 stack](https://gen3.org/resources/operator/index.html), which consists of over a dozen containerised microservices.   

## Installation
### K3s 
The installation script for K3s, with default load balancer `servicelb` (also known as `klipper`) and default ingress controller `traefik` can be used as follows:
```bash
sudo curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644
```
However, if we wish to use a different load balancer or different ingress controller, then the default ones can be disabled when running the installation script. In our case, we'd like to use the [metallb load balancer](https://metallb.universe.tf/) and the [nginx ingress controller](https://docs.nginx.com/nginx-ingress-controller/installation/installing-nic/). The following command uses the installation script, but disables the default load balancer and ingress controller:
```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable servicelb --disable traefik" sh -s - --write-kubeconfig-mode 644
```   
The installation includes additional utilities such as `kubectl`, `crictl`, `ctr`, `k3s-killall.sh`, and `k3s-uninstall.sh`. `kubectl` will automatically use the `kubeconfig` file that gets written to `/etc/rancher/k3s/k3s.yaml` after the installation. By default, the container runtime that K3s uses is `containerd`.    

Docker is not needed, but can be installed if desired. To use Docker as the container runtime, the following command should be run:
```bash
curl https://releases.rancher.com/install-docker/20.10.sh | sh
```
This will let K3s use Docker instead of Containerd.     

We might encounter some permissions issues when trying to use the `kubectl` command line tool. This can be resolved by creating a `.kube` directory which contains the cluster config file. We can achieve this by running the following commands:
```bash
mkdir ~/.kube
sudo k3s kubectl config view --raw | tee ~/.kube/config
chmod 600 ~/.kube/config
export KUBECONFIG=~/.kube/config
```
For these updates to persist upon reboot, the `.profile` and `.bashrc` files should be updated with `export KUBECONFIG=~/.kube/config`.   

After about a minute or so, the following command can be run to see if the cluster is in good shape:
```bash
kubectl get all -n kube-system
```
![Resources in kube-system Namespace](/public/assets/images/kube-system-resources.png "Resources in kube-system Namespace")   

If something is not quite right and there is a desire to re-install K3s with some other features enabled/disabled, it can be fully uninstalled with:
```bash
/usr/local/bin/k3s-uninstall.sh
```
In such a case, remember to delete the `.kube` directory so that there aren't any certificate issues with a fresh re-install.   

To add another node to the cluster, two pieces of information are required:   
1. K3S_URL=https://ip-address-of-master-node:6443   
2. K3S_TOKEN="K10b63f77faa4043254ce5acd735f461514c9265b0c40e9fb32e84dc19cbdefdfa3::server:6f6edd5c568c0d8c6d18a19682d22d08" (this can be found in the `/var/lib/rancher/k3s/server` directory. Simply run `sudo cat /var/lib/rancher/k3s/server/node-token` to see the value).   
Once these values are retrieved, the new node can be added to the cluster by running:
```bash
curl -sfL https://get.k3s.io | K3S_URL=https://146.141.240.78:6443 K3S_TOKEN="K10b63f77faa4043254ce5acd735f461514c9265b0c40e9fb32e84dc19cbdefdfa3::server:6f6edd5c568c0d8c6d18a19682d22d08" INSTALL_K3S_EXEC="--disable servicelb --disable traefik" sh -s - --write-kubeconfig-mode 644
```
This newly added node needs to be started up as an agent:
```bash
sudo k3s agent --server ${K3S_URL} --token ${K3S_TOKEN}
```
On the master node, we can see all the nodes by running:
```bash
kubectl get nodes -o wide
```

### Helm
[Helm](https://helm.sh/) is a package manager for Kubernetes that allows for the installation or deployment of applications onto a Kubernetes cluster. We can install it as follows:
```bash
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh
```
To see if Helm has been installed, we can run a simple `helm` command like:
```bash
helm list
```
and we should get an empty table as our output,
| NAME          | NAMESPACE | REVISION  | UPDATED | STATUS  | CHART | APP VERSION |
| ------------- | --------- | --------- | ------- | ------- | ----- | ----------- |
|               |           |           |         |         |       |             |

### Installing MetalLB Load Balancer with Helm
Using Helm, we begin with:
```bash
helm repo add stable https://charts.helm.sh/stable
```
In the past, `metallb` used to be configured using config maps because that’s traditionally where configs were placed. However, now it uses custom resources (CRs). We'll create a namespace called `metallb-system` and then perform a Helm deployment for all the `metallb` resources:
```bash
kubectl create ns metallb-system
helm repo add metallb https://metallb.github.io/metallb
helm install metallb metallb/metallb --namespace metallb-system
```
Now we need to create two additional resources, an address pool and a layer two advertisement, which instructs `metallb` to use the address pool. Here are the manifests of the two resources (saved inside the `metallb` directory):
**IPAddressPool.yaml**   
```yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: k3s-cloud08-pool
  namespace: metallb
spec:
  addresses:
  - 146.141.240.78/32
```
**L2Advertisement.yaml**   
```yaml
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: k3s-cloud08-l2advertisment
  namespace: metallb
spec:
  ipAddressPools:
  - k3s-cloud08-pool
```
To create these resources, we need to run the `kubectl apply -f` command:
```bash
kubectl -n metallb-system apply -f metallb/IPAddressPool.yaml
kubectl -n metallb-system apply -f metallb/L2Advertisement.yaml
```
To see if the resources have been created, we can run:
```bash
kubectl get pods -n metallb-system
```
and should get an output that looks similar to:   

| NAME                                | READY | STATUS   | RESTARTS   | AGE |
| ----------------------------------- | ----- | -------- | ---------- | --- |
| metallb-speaker-dzcks               | 4/4   | Running  | 0          | 20m |
| metallb-controller-6cb58c6c9b-p9dqz | 1/1   | Running  | 1 (9m ago) | 20m |

### Installing NGINX Ingress with Helm
Using Helm, we can install the `ingress-nginx` controller as follows:
```bash
helm upgrade --install ingress-nginx ingress-nginx \
--repo https://kubernetes.github.io/ingress-nginx \
--namespace ingress-nginx --create-namespace
```
Instead of using Helm, the NGINX ingress controller can be created directly from a manifest:
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.7.1/deploy/static/provider/baremetal/deploy.yaml
```
(This manifest file has been copied and saved to this repository, `ingress-nginx-controller/ingress-nginx-controller-v1.7.1.yaml`).   

After a short while, we can run the following command to see if the pods are up and running:
```bash
kubectl get pods --namespace=ingress-nginx
```
For a simple test, let us create a sample deployment and a service to expose the deployment:
```bash
kubectl create deployment my-deployment --image=nginx --port=80
kubectl expose deployment my-deployment
```
An ingress resource can also be created as follows:
```bash
kubectl create ingress my-deployment-ingress --class=nginx --rule="my-deployment.localdev.me/*=my-deployment:80"
```
A local port can be forwarded to the ingress controller:
```bash
kubectl port-forward --namespace=ingress-nginx service/ingress-nginx-controller 8080:80
```
An NGINX welcome page should be seen if visiting the url http://my-deployment.localdev.me:8080/ (for local development), or using
```bash
curl http://my-deployment.localdev.me:8080/
```
which yields
```html
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
<style>
html { color-scheme: light dark; }
body { width: 35em; margin: 0 auto;
font-family: Tahoma, Verdana, Arial, sans-serif; }
</style>
</head>
<body>
<h1>Welcome to nginx!</h1>
<p>If you see this page, the nginx web server is successfully installed and
working. Further configuration is required.</p>

<p>For online documentation and support please refer to
<a href="http://nginx.org/">nginx.org</a>.<br/>
Commercial support is available at
<a href="http://nginx.com/">nginx.com</a>.</p>

<p><em>Thank you for using nginx.</em></p>
</body>
</html>
```
Here is an example Ingress that makes use of the controller: 
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example
  namespace: foo
spec:
  ingressClassName: nginx
  rules:
    - host: www.example.com
      http:
        paths:
          - pathType: Prefix
            backend:
              service:
                name: exampleService
                port:
                  number: 80
            path: /
  # This section is only required if TLS is to be enabled for the Ingress
  tls:
    - hosts:
      - www.example.com
      secretName: example-tls

# If TLS is enabled for the Ingress, a Secret containing the certificate and key must also be provided:
apiVersion: v1
kind: Secret
metadata:
  name: example-tls
  namespace: foo
data:
  tls.crt: <base64 encoded cert>
  tls.key: <base64 encoded key>
type: kubernetes.io/tls
```
When we install `gen3`, the `revproxy-service` will be the ingress of the Gen3 stack, and the `gen3-certs` will be the secret.   

**NOTE:** The test `my-deployment` resources can be deleted after confirming that the ingress controller is working as desired:
```bash
kubectl delete deployment my-deployment
kubectl delete service my-deployment
kubectl delete ingress my-deployment-ingress
```

### Installing Gen3 Microservices with Helm
The Helm charts for the Gen3 services can be found in the [uc-cdis/gen3-helm repository](https://github.com/uc-cdis/gen3-helm.git). We'd like to add the Gen3 Helm chart repository. To do this, we run:  

```bash
helm repo add gen3 http://helm.gen3.org
helm repo update
```
The Gen3 Helm chart repository contains the templates for all the microservices making up the Gen3 stack. For the `elastic-search-deployment` to run in a Linux host machine, we need to increase the max virtual memory areas by running:
```bash
sudo sysctl -w vm.max_map_count=262144
``` 
This setting will only last for the duration of the session. The host machine will be reset to the original value if it gets rebooted. For this change to be set permanently on the host machine, the `/etc/sysctl.conf` file needs to be edited with `vm.max_map_count=262144`. To see the current value, run `/sbin/sysctl vm.max_map_count`. More details can be found on the [official Elasticsearch website](https://www.elastic.co/guide/en/elasticsearch/reference/current/vm-max-map-count.html).   

Some of the microservices require the `uwsgi-plugin` for Python 3. To install it, run the following:
```bash
sudo apt update  
sudo apt install uwsgi-plugin-python3 
```

Before performing a `helm install`, we need to create a `values.yaml` file that can be used to override default values specified in the Gen3 Helm templates. The Helm installation can begin by running:
```bash
helm upgrade --install gen3-dev gen3/gen3 -f gen3/values.yaml 
```
In the above command, `gen3-dev` is the name of the release of the helm deployment. If the installation is successful, then a message similar to the following should be displayed in the terminal:
```bash
NAME: gen3-dev
LAST DEPLOYED: Tue Nov 14 13:27:49 2023
NAMESPACE: default
STATUS: deployed
REVISION: 1
```
If the default `traefik` ingress controller was used and all went well, we should see the `revproxy-dev` deployment up and running with the following command:
```bash
kubectl get ingress
```
The output should look similar to this:
| NAME          | CLASS   | HOSTS                   | ADDRESS        | PORTS   | AGE |
| ------------- | ------- | ----------------------- | -------------- | ------- | --- |
| revproxy-dev  | traefik | cloud08.core.wits.ac.za | 146.141.240.78 | 80, 443 | 34s |    

However, if the `nginx` ingress controller has been used instead, then the `revproxy-dev` ingress manifest needs to be edited. To edit the resource, run:
```bash
kubectl edit ingress revproxy-dev
```
This will open a `vim` editor. The following line, `ingressClassName: nginx`, should be added under the `spec` section of the YAML file and then the changes should be saved. Checking the ingress now should yield:
```bash
kubectl get ingress
```
The output should look similar to this:
| NAME          | CLASS   | HOSTS                   | ADDRESS        | PORTS   | AGE |
| ------------- | ------- | ----------------------- | -------------- | ------- | --- |
| revproxy-dev  | nginx   | cloud08.core.wits.ac.za | 146.141.240.78 | 80, 443 | 10m | 

The list of deployments can be seen by running:
```bash
kubectl get deployments
```    

![Gen3 services deployed with NGINX](/public/assets/images/gen3-deployments-nginx.png "Gen3 services deployed with NGINX")   

As can be seen in the screenshot above, not all of the deployments are ready. We need to investigate why this is the case.   

Several debugging attempts have already been made. The Firewall and DNS have been investigated, but it doesn't look like that is the main cause of the problem. See [this document](/documentation/debugging_networking_issues.md) for more information on some of the troubleshooting and debugging that was attempted.   

Looking at the logs of the `peregrine-deployment` pod,
```bash
kubectl logs pod/peregrine-deployment-694c89d4b4-x46qm
```
we see the following information (this is just an excerpt):
```bash
Traceback (most recent call last):
  File "/usr/local/lib/python3.6/site-packages/urllib3/connectionpool.py", line 710, in urlopen
    chunked=chunked,
  File "/usr/local/lib/python3.6/site-packages/urllib3/connectionpool.py", line 386, in _make_request
    self._validate_conn(conn)
  File "/usr/local/lib/python3.6/site-packages/urllib3/connectionpool.py", line 1040, in _validate_conn
    conn.connect()
  File "/usr/local/lib/python3.6/site-packages/urllib3/connection.py", line 426, in connect
    tls_in_tls=tls_in_tls,
  File "/usr/local/lib/python3.6/site-packages/urllib3/util/ssl_.py", line 450, in ssl_wrap_socket
    sock, context, tls_in_tls, server_hostname=server_hostname
  File "/usr/local/lib/python3.6/site-packages/urllib3/util/ssl_.py", line 493, in _ssl_wrap_socket_impl
    return ssl_context.wrap_socket(sock, server_hostname=server_hostname)
  File "/usr/local/lib/python3.6/ssl.py", line 407, in wrap_socket
    _context=self, _session=session)
  File "/usr/local/lib/python3.6/ssl.py", line 817, in __init__
    self.do_handshake()
  File "/usr/local/lib/python3.6/ssl.py", line 1077, in do_handshake
    self._sslobj.do_handshake()
  File "/usr/local/lib/python3.6/ssl.py", line 689, in do_handshake
    self._sslobj.do_handshake()
ssl.SSLError: [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:852)
```
There is an SSL or TLS issue with some of the deployments. We can try creating new certificates for the host (`cloud08`) using `openssl`:
```bash
mkdir -p cloud08_certs

openssl req \
-new \
-newkey rsa:2048 \
-x509 \
-sha256 \
-days 365 \
-nodes \
-subj "/O=cloud08/CN=cloud08.core.wits.ac.za" \
-keyout cloud08_certs/cloud08.key \
-out cloud08_certs/cloud08.crt
```
These certificates can be added to a Kubernetes secret as follows:
```bash
kubectl create secret tls cloud08-tls-secret --key cloud08_certs/cloud08.key --cert cloud08_certs/cloud08.crt
```
We can also create a secret that uses the pre-existing certificates on the node which reside in the `/etc/ssl/certs/` directory:
```bash
kubectl create secret tls cloud08-certs --key /etc/ssl/certs/ca-certificates.key --cert /etc/ssl/certs/ca-certificates.crt
```
Unfortunately, there doesn't seem to be a `.key` file for these old certificates. Without the `.key` file, we cannot use the certificate.   

We can also try creating new certificates for node `pc78`, since there appears to be some mix up regarding the DNS involving the ip addresses of the `cloud08` node and the `pc78` node. Perhaps they are the same nodes with two different names.    
![Hostname and IP Address of Node](/public/assets/images/nslookup-confusion.png "Hostname and IP Address of Node")   

We'll do the following:
```bash
mkdir -p pc78_certs

openssl req \
-new \
-newkey rsa:2048 \
-x509 \
-sha256 \
-days 365 \
-nodes \
-subj "/O=pc78/CN=pc78.core.wits.ac.za" \
-keyout pc78_certs/pc78.key \
-out pc78_certs/pc78.crt
```
We'll then create the corresponding secret which will have these newly created certificates:
```bash
kubectl create secret tls pc78-tls-secret --key pc78_certs/pc78.key --cert pc78_certs/pc78.crt
```
The NGINX ingress controller should be edited to include this secret by adding the following to the `revproxy-dev` manifest under the `spec` section:
```bash
  tls:
  - hosts:
    - cloud08.core.wits.ac.za
    secretName: gen3-certs
  - hosts:
    - cloud08.core.wits.ac.za
    secretName: cloud08-tls-secret
  - hosts:
    - pc78.core.wits.ac.za
    secretName: gen3-certs
  - hosts:
    - pc78.core.wits.ac.za
    secretName: pc78-tls-secret
```

Another reason for the problems we are facing could be due to not having an external load balancer configured for the K3s cluster. When using a cloud provider like AWS, the Amazon Load Balancer (ALB) is automatically configured to be used by the cluster. For on-prem solutions, an external load balancer needs to be manually configured. 
