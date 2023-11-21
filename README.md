# k3s Setup and Configuration on Ubuntu 22.04
## Introduction
We will be using a virtual machine with operating system _Ubuntu 22.04.2 LTS_, kernel _GNU/Linux 5.15.0-73-generic_, and architecture _x86-64_ to setup and configure a Kubernetes cluster using the [k3s distribution](https://docs.k3s.io/). We'll go with a K3s single-server setup (we might expand at a later date).        
![K3s Single Server Setup](/public/assets/images/k3s-architecture.png "K3s Single Server Setup")   

The ultimate goal for having this cluster up and running is to administer and orchestrate the [Gen3 stack](https://gen3.org/resources/operator/index.html), which consists of over a dozen containerised microservices.   

## Installation
### K3s
The installation script for K3s can be used as follows:
```bash
curl -sfL https://get.k3s.io | sh -
```
The installation includes additional utilities such as `kubectl`, `crictl`, `ctr`, `k3s-killall.sh`, and `k3s-uninstall.sh`. `kubectl` will automatically use the `kubeconfig` file that gets written to `/etc/rancher/k3s/k3s.yaml` after the installation. By default, the container runtime that K3s uses is `containerd`. Docker is not needed, but can be installed if desired.   

We might encounter some permissions issues when trying to use the `kubectl` command line tool. This can be resolved by running the following commands:
```bash
mkdir ~/.kube
sudo k3s kubectl config view --raw | tee ~/.kube/config
chmod 600 ~/.kube/config
export KUBECONFIG=~/.kube/config
```
For these updates to persist upon reboot, the `.profile` and `.bashrc` files should be updated with `export KUBECONFIG=~/.kube/config`.   

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

### Longhorn
[Longhorn](https://longhorn.io/docs/1.5.1/) is an open-source distributed block storage system for Kubernetes, and is supported by K3s. To install Longhorn, we apply the `longhorn.yaml`:

```bash
kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/v1.5.1/deploy/longhorn.yaml
```

We need to create a persistent volume claim and a pod to make use of it:   

**longhorn-volv-pvc.yaml**
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: longhorn-volv-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: longhorn
  resources:
    requests:
      storage: 2Gi
```

**volume-test-pod.yaml**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: volume-test
  namespace: default
spec:
  containers:
  - name: volume-test
    image: nginx:stable-alpine
    imagePullPolicy: IfNotPresent
    volumeMounts:
    - name: volv
      mountPath: /data
    ports:
    - containerPort: 80
  volumes:
  - name: volv
    persistentVolumeClaim:
      claimName: longhorn-volv-pvc
```
To create the `longhorn-volv-pvc` and `volume-test-pod` defined above, we need to be apply the YAML:
```bash
kubectl create -f longhorn-volv-pvc.yaml
kubectl create -f volume-test-pod.yaml
```
The creation of the persistent volume and persistent volume claim can be confirmed by running the following command:
```bash
kubectl get pv
kubectl get pvc
```

### Grafana OSS in Kubernetes (Optional)   
Grafana open source software (OSS) allows for the querying, visualising, alerting on, and exploring of metrics, logs, and traces wherever they are stored. Graphs and visualisations can be created from time-series database (TSDB) data with the tools that are provided by Grafana OSS. We'll be using the [Grafana documentation](https://grafana.com/docs/grafana/latest/setup-grafana/installation/kubernetes/) to guide us in installing Grafana in our k8s cluster.   

To create a namespace for Grafana, run the following command:
```bash
kubectl create namespace gen3-grafana
```
We'll create a `grafana.yaml` file which will contain the blueprint for a persistent volume claim (pvc), a service of type loadbalancer, and a deployment. This file can be found in the `gen3` directory of this repo. To create these resources, we need to apply the manifest as follows:
```bash
kubectl apply -f gen3/grafana.yaml --namespace=gen3-grafana
```
To get all information about the Grafana deplyment, run:
```bash
kubectl get all --namespace=gen3-grafana
```
![Grafana k8s Objects](/public/assets/images/grafana-k8s-objects.png "Grafana k8s Objects")  

The `grafana` service should have an **EXTERNAL-IP**. This IP can be used to access the Grafana sign-in page in the browser. If there is no **EXTERNAL_IP**, then port-forwarding can be performed like this:
```bash
kubectl port-forward service/grafana 3000:3000 --namespace=gen3-grafana
```
Then the Grafana sign-in page can be accessed on `http://<ip-address>:3000`. Use `admin` for both the username and the password.   
![Grafana Login Page](/public/assets/images/grafana-login-page.png "Grafana Login Page")   

### Docker (Optional)
To use Docker as the container runtime, the following command should be run:
```bash
curl https://releases.rancher.com/install-docker/20.10.sh | sh
```
This will let K3s use Docker instead of Containerd.   

#### More Detailed Process for Docker Installation (not necessary if the above script works)
Let us go through the steps to install [Docker](https://docs.docker.com/get-started/overview/). We'll begin by doing a general software dependency update:
```bash
apt-get update
```
Add the official Docker GPG key:
```bash
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
```
Add the Docker repository:
```bash
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
$(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list &gt; /dev/null
```
Install the necessary Docker dependencies:
```bash
sudo apt-get install apt-transport-https ca-certificates curl gnupg lsb-release -y
```
The following two commands will install the latest version of the Docker engine:
```bash
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io -y
```
Add the user to the Docker group  with the following command:
```bash
sudo usermod -aG docker $USER
```
End the terminal session and then restart it. Docker should be installed.    

### Running a PostgreSQL Database inside a Docker Container (Optional)
A postgreSQL database can be created to run inside a Docker container. This should not be in the Kubernetes cluster. This is not necessary for testing, but would be required if a persistent database is required. The following commands can be copied into a script called `init-db.sh` for convenience, or they could be run independently, but sequentially, as follows:
```bash
echo "Start postgres docker container"
docker run --rm --name gen3-dev-db -e POSTGRES_PASSWORD=gen3-password -d -p 5432:5432 -v postgres_gen3_dev:/var/lib/postgresql/data postgres:14
echo "Database starting..."
sleep 10
echo "Create gen3 Database"
docker exec -it gen3-dev-db bash -c 'PGPASSWORD=gen3-password psql -U postgres -c "create database gen3_db"'
echo "Create gen3_schema Schema"
docker exec -it gen3-dev-db bash -c 'PGPASSWORD=gen3-password psql -U postgres -d gen3_db -c "create schema gen3_schema"'
```
If the script runs successfully, the output should look like:
![Gen3 PostgreSQL Database](/public/assets/images/gen3-db.png "Gen3 PostgreSQL Database")   
By default, the hostname of the database is the container id.   

### Installing the k9s Tool (Optional)
**k9s** is a useful tool that makes troubleshooting issues in a Kubernetes cluster easier. Installing it is highly recommended. It can be downloaded and installed as follows:
```bash
wget https://github.com/derailed/k9s/releases/download/v0.25.18/k9s_Linux_x86_64.tar.gz
tar -xzvf k9s_Linux_x86_64.tar.gz
chmod +x k9s
sudo mv k9s /usr/local/bin/
```
To open it, simply run:
```bash
k9s
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
If all went well, we should see the `revproxy-dev` deployment up and running with the following command:
```bash
kubectl get ingress
```
The output should look similar to this:
| NAME          | CLASS   | HOSTS           | ADDRESS        | PORTS   | AGE |
| ------------- | ------- | --------------- | -------------- | ------- | --- |
| revproxy-dev  | traefik | gen3local.co.za | 146.141.240.78 | 80, 443 | 34s |

The list of deployments can be seen by running:
```bash
kubectl get deployments
```    

![Gen3 services deployed](/public/assets/images/gen3-deployments-incomplete.png "Gen3 services deployed")   

As can be seen in the screenshot above, not all of the deployments are ready. We need to investigate why this is the case.   

### Troubleshooting Networking Issues
Some of the deployments are not in a READY state. After running the following command,
```bash
sudo iptables -S
```
the following information was found:
```bash
-A KUBE-SERVICES -d 10.43.248.157/32 -p tcp -m comment --comment "default/peregrine-service:http has no endpoints" -m tcp --dport 80 -j REJECT --reject-with icmp-port-unreachable
-A KUBE-SERVICES -d 10.43.45.52/32 -p tcp -m comment --comment "default/pidgin-service:https has no endpoints" -m tcp --dport 443 -j REJECT --reject-with icmp-port-unreachable
-A KUBE-SERVICES -d 10.43.45.52/32 -p tcp -m comment --comment "default/pidgin-service:http has no endpoints" -m tcp --dport 80 -j REJECT --reject-with icmp-port-unreachable
-A KUBE-SERVICES -d 10.43.214.116/32 -p tcp -m comment --comment "default/workspace-token-service:http has no endpoints" -m tcp --dport 80 -j REJECT --reject-with icmp-port-unreachable
-A KUBE-SERVICES -d 10.43.252.154/32 -p tcp -m comment --comment "default/portal-service:http has no endpoints" -m tcp --dport 80 -j REJECT --reject-with icmp-port-unreachable
-A KUBE-SERVICES -d 10.43.168.94/32 -p tcp -m comment --comment "default/sheepdog-service:http has no endpoints" -m tcp --dport 80 -j REJECT --reject-with icmp-port-unreachable
-A KUBE-SERVICES -d 10.43.214.116/32 -p tcp -m comment --comment "default/workspace-token-service:https has no endpoints" -m tcp --dport 443 -j REJECT --reject-with icmp-port-unreachable
-A KUBE-SERVICES -d 10.43.120.234/32 -p tcp -m comment --comment "default/gen3-dev-manifestservice:http has no endpoints" -m tcp --dport 80 -j REJECT --reject-with icmp-port-unreachable
-A KUBE-SERVICES -d 10.43.145.199/32 -p tcp -m comment --comment "default/elasticsearch has no endpoints" -m tcp --dport 9200 -j REJECT --reject-with icmp-port-unreachable
```
When running
```bash
kubectl get endpoints
```
the following output is received:   
| NAME                       | ENDPOINTS                       | AGE |
| -------------------------- | ------------------------------- | --- |
kubernetes                   | 146.141.240.78:6443             | 17d |
gen3-dev-manifestservice     | <none>                          | 58m |
peregrine-service            |                                 | 58m |
sheepdog-service             |                                 | 58m |
elasticsearch                |                                 | 58m |
gen3-dev-postgresql-hl       | 10.42.0.227:5432                | 58m |
hatchery-service             | 10.42.0.218:8000                | 58m |
sower-service                | 10.42.0.224:8000                | 58m |
gen3-dev-postgresql          | 10.42.0.227:5432                | 58m |
pidgin-service               |                                 | 58m |
argo-wrapper-service         | 10.42.0.240:8000                | 58m |
portal-service               |                                 | 58m |
revproxy-service             | 10.42.0.242:80                  | 58m |
ambassador-service           | 10.42.0.247:8080                | 58m |
ambassador-admin             | 10.42.0.247:8877                | 58m |
arborist-service             | 10.42.0.243:80                  | 58m |
metadata-service             | 10.42.0.226:80                  | 58m |
presigned-url-fence-service  | 10.42.0.235:80                  | 58m |
audit-service                | 10.42.0.220:80                  | 58m |
requestor-service            | 10.42.0.245:80                  | 58m |
indexd-service               | 10.42.0.222:80                  | 58m |
fence-service                | 10.42.0.225:80                  | 58m |
workspace-token-service      | 10.42.0.238:443,10.42.0.238:80  | 58m |

Perhaps the solution entails explicitly allowing traffic to those IP addresses listed above with the `--reject-with icmp-port-unreachable` flag, or maybe the ingress controller and/or network policy needs to be configured differently. There’s a `KUBE-SERVICES` chain in the target that’s created by `kube-proxy`. We can list the rules in that chain as follows:
```bash
sudo iptables -t nat -L KUBE-SERVICES -n  | column -t
```   
A long list of services will be displayed, however, the `peregrine`, `pidgin`, `elasticsearch`, `sheepdog`, and the `portal` services are not listed. Somehow the Firewall or the `kube-proxy` is blocking traffic to those services.   

The `peregrine` deployment pod refuses to reach a READY state due to some SSL error of the form
```bash
ssl.SSLError: [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:852)
```
When running the cURL command,
```bash
curl https://s3.amazonaws.com/dictionary-artifacts/datadictionary/develop/schema.json
```
from inside the VM, a full JSON response is received. However, when running that same cURL command from inside the pod (with the `--image=nicolaka/netshoot` container running), we get that same ssl connection refused error (see image).   
![Netshoot Troubleshooting](/public/assets/images/netshoot-troubleshooting.png "Netshoot Troubleshooting")   

### Upgrading Traefik Ingress to v2.10
From the root, we can navigate to `/var/lib/rancher/k3s/server/manifests` and see the contents of the `traefik.yaml` file, which should **never** be edited manually:
```bash
cat traefik.yaml
```
```yaml
---
apiVersion: helm.cattle.io/v1
kind: HelmChart
metadata:
  name: traefik-crd
  namespace: kube-system
spec:
  chart: https://%{KUBERNETES_API}%/static/charts/traefik-crd-21.2.1+up21.2.0.tgz
---
apiVersion: helm.cattle.io/v1
kind: HelmChart
metadata:
  name: traefik
  namespace: kube-system
spec:
  chart: https://%{KUBERNETES_API}%/static/charts/traefik-21.2.1+up21.2.0.tgz
  set:
    global.systemDefaultRegistry: ""
  valuesContent: |-
    podAnnotations:
      prometheus.io/port: "8082"
      prometheus.io/scrape: "true"
    providers:
      kubernetesIngress:
        publishedService:
          enabled: true
    priorityClassName: "system-cluster-critical"
    image:
      repository: "rancher/mirrored-library-traefik"
      tag: "2.10.5"
    tolerations:
    - key: "CriticalAddonsOnly"
      operator: "Exists"
    - key: "node-role.kubernetes.io/control-plane"
      operator: "Exists"
      effect: "NoSchedule"
    - key: "node-role.kubernetes.io/master"
      operator: "Exists"
      effect: "NoSchedule"
    service:
      ipFamilyPolicy: "PreferDualStack"
```
**NOTE:** Permissions for entering this directory might be denied, so the following command should be run by a root user:
```bash
sudo chmod -R 777 var/lib
```
We can then customise our Traefik configuration by creating a file called `traefik-config.yaml` with the following content:
```yaml
apiVersion: helm.cattle.io/v1
kind: HelmChartConfig
metadata:
  name: traefik
  namespace: kube-system
spec:
  valuesContent: |-
    image:
      name: traefik
      tag: 2.10.5
    forwardedHeaders:
      enabled: true
      trustedIPs:
        - 10.0.0.0/8
    ssl:
      enabled: true
      permanentRedirect: false
```
When using version 2.10 of `traefik`, we need to manually add the missing CRDS:
```bash
kubectl apply -f https://raw.githubusercontent.com/traefik/traefik/v2.10/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml
```
We then need to update the api groups in the `traefik-kube-system` cluster role with `traefik.io`:
```bash
kubectl edit clusterrole traefik-kube-system
```
![traefik-kube-system Cluster Role](/public/assets/images/traefik-kube-system-cluster-role.png "traefik-kube-system Cluster Role")   

All api groups in Traefik resources need to be changed from `traefik.containo.us/v1alpha1` to `traefik.io/v1alpha1`.
