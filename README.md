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

The above process installs and configures a single-node cluster. This single node acts as both a master and a worker node. To add additional worker nodes, please read [this document](documentation/adding_a_worker_node.md) for more details.   

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

Additional changes need to be made to the ingress manifest. Since an external service is going to be used for [external authentication](https://github.com/kubernetes/ingress-nginx/blob/main/docs/user-guide/nginx-configuration/annotations.md#external-authentication), the following annotation needs to be added to the ingress manifest:
```bash
nginx.ingress.kubernetes.io/auth-url: "URL to the authentication service"
```   

The list of deployments can be seen by running:
```bash
kubectl get deployments
```    
![Gen3 services deployed with NGINX](public/assets/images/gen3-deployments.png "Gen3 services deployed with NGINX")   

The `portal-deployment` is normally the last deployment to be ready. In particular, it is dependent on both the `peregrine-deployment` and the `sheepdog-deployment`. It may struggle (by constantly restarting) to run while waiting for the other deployments to be ready. If that happens, then the following command should be run once the `peregrine-deployment` and the `sheepdog-deployment` are up and running:
```bash
kubectl rollout restart deployment portal-deployment
```
This command restarts the deployment. Alternatively, the `portal-deployment` pod can simply be deleted. The replicaset will ensure that another pod is spun up immediately.   

Information about the Gen3 helm release can be found with the command:
```bash
helm list
```
and we should see a table that looks similar to this:
| NAME          | NAMESPACE | REVISION  | UPDATED                                  | STATUS   | CHART       | APP VERSION |
| ------------- | --------- | --------- | ---------------------------------------- | -------- | ----------- | ----------- |
| gen3-dev      | default   | 1         | 2024-01-16 13:35:01.712355152 +0200 SAST | deployed | gen3-0.1.21 | master      |

To verify that the correct custom values are being used, the following command can be run:
```bash
helm get values <name-of-release>
```
In our case, the name of the release is `gen3-dev`. The output will be a reproduction of the `values.yaml` file with the first line being **USER-SUPPLIED VALUES:**. There may exist the requirement to edit values in the `values.yaml` _without_ upgrading the version of the release. In that case, the following commands could be used if the values from the previous release need to be used again (this is because, by default, the `helm upgrade` command resets the values to those baked into the chart):
```bash
helm upgrade --reuse-values -f gen3/updated-values.yaml gen3-dev gen3/gen3
```
or 
```bash
helm upgrade --reuse-values --set key1=newValue1,key2=newValue2 gen3-dev gen3/gen3
```

#### Mocking Google Authentication
For testing purposes and for a quick setup of the Gen3 ecosystem, the authentication process can be mocked. The `fence` service is responsible for authenticating a user, so the `fence` config of the value file needs to be configured as follows:
```yaml
fence:
  enabled: true
  FENCE_CONFIG:
    MOCK_AUTH: true
```
This will automatically login a user with username "test". If all the Gen3 services are up and running, the portal can be accessed in the browser by making use of the machine's IP address and the node port of the `revproxy-service` (since the `revproxy-service` is a service of type **NodePort**), e.g.   

![User Endpoint for Mock Authentication](public/assets/images/user-endpoint-for-mock-login.png "User Endpoint for Mock Authentication")    

To upload a file to a custom AWS S3 bucket, the bucket name needs to be provided in the `fence` config of the `values.yaml` file:
```yaml
fence:
  enabled: true
  FENCE_CONFIG:
    AWS_CREDENTIALS:
      "gen3-user":
        aws_access_key_id: "accessKeyIdForGen3User"
        aws_secret_access_key: "secretAccessKeyForGen3User"
    S3_BUCKETS:
      # Name of the actual s3 bucket
      gen3-bucket:
        cred: "gen3-user"
        endpoint_url: "s3.us-east-1.amazonaws.com"
        region: us-east-1
    # This is important for data upload.
    DATA_UPLOAD_BUCKET: "gen3-bucket"
```
The other `fence` endpoints can be found over [here](https://petstore.swagger.io/?url=https://raw.githubusercontent.com/uc-cdis/fence/master/openapis/swagger.yaml). 

#### Google Authentication
The `fence-service` is mainly responsible for Gen3 authentication. There are a variety of authentication providers. If [Google is to be used for authentication](https://github.com/uc-cdis/fence/blob/master/docs/google_architecture.md), then a project needs to be created in the [Google Cloud Console](https://console.cloud.google.com/). This project will need to be part of an organisation. In our case, the organisation is **wits.ac.za**, and the project is called **gen3-dev**.    

The Google project needs to be setup correctly. The project needs to be a _web application_, it needs to be _external_, the authorised redirect uri needs to be configured as the `${hostname}/user/login/google/login/, and the following scopes are required:
- openid
- email
- profile

![Google OAuth App Setup](public/assets/images/google-oauth-app-setup.png "Google OAuth App Setup")   

If the correct values are provided, and the Google authentication and the ingress is setup correctly, then the `fence` authentication should work properly:   

![Gen3 Login](public/assets/images/gen3-login.png "Gen3 Login")   

#### Uploading of Files
A detailed description of how the upload process works in Gen3 can be found over [here](https://gen3.org/resources/user/gen3-client/). The data client SDK can be downloaded for Linux, MacOS, or Windows. It is in `.zip` format, and can be extracted into a folder and used accordingly. For convenience, all three `.zip` files have been included in this repository in the `/public/assets/sdk` directory (there is no guarantee that the `.zip` files in this directory are the most recent. Please check the website directly).   

#### Modifying the Fence Config File   
The `fence-config` is a Kubernetes secret and its contents can be viewed in YAML format with the following command:
```bash
kubectl get secret fence-config -o yaml
```
The output should look similar to this:
```yaml
apiVersion: v1
data:
  fence-config.yaml: QkFTRV9VUkw6IGh0dHBzOi...mdlX2FyZWE6CiAgICAtIC9kYmdhcC8K
kind: Secret
metadata:
  annotations:
    meta.helm.sh/release-name: gen3-dev
    meta.helm.sh/release-namespace: default
  creationTimestamp: "2024-01-30T08:03:14Z"
  labels:
    app.kubernetes.io/managed-by: Helm
  name: fence-config
  namespace: default
  resourceVersion: "2149406"
  uid: f48d526f-7d49-4510-978b-565e0a5b7f55
type: Opaque
```
The value in the data field is the base64 encoded form of the actual `fence-config.yaml` file. To decode it, the following command can be used:
```bash
echo 'base64 encoded value' | base64 --decode
```
This command will output the contents of the `fence-config.yaml` file in the correct YAML format. The values inside this YAML file can be checked to ensure that they match what was specified in the `values.yaml` file when the Helm deployment took place. 