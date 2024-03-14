## Longhorn
[Longhorn](https://longhorn.io/docs/1.5.1/) is an open-source distributed block storage system for Kubernetes, and is supported by K3s. To install Longhorn, we apply the `longhorn.yaml`:

```bash
kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/v1.5.1/deploy/longhorn.yaml
```
(The manifest file for the `longhorn-system` can be found in this repo in the longhorn-system directory).   

We need to create a persistent volume claim and a pod to make use of it:   

**longhorn-gen3-pvc.yaml**
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: longhorn-gen3-pvc
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: longhorn
  resources:
    requests:
      storage: 2Gi
```

**gen3-volume-pod.yaml**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gen3-volume-pod
  namespace: default
spec:
  containers:
  - name: gen3-volume-pod
    image: nginx:stable-alpine
    imagePullPolicy: IfNotPresent
    volumeMounts:
    - name: gen3-volume
      mountPath: /data
    ports:
    - containerPort: 80
  volumes:
  - name: gen3-volume
    persistentVolumeClaim:
      claimName: longhorn-gen3-pvc
```
To create the `longhorn-gen3-pvc` and `gen3-volume-pod` defined above, we need to be apply the YAML:
```bash
kubectl create -f longhorn-gen3-pvc.yaml
kubectl create -f gen3-volume-pod.yaml
```
The creation of the persistent volume and persistent volume claim can be confirmed by running the following command:
```bash
kubectl get pv
kubectl get pvc
```    

### Setting up MinIO for Object Storage
[MinIO](https://min.io/docs/minio/kubernetes/upstream/index.html) is an open-source object storage solution which provides all the core Amazon S3 features and is compatible with the Amazon S3 API. It is built to be deployed anywhere - public cloud, private cloud, baremetal infrastructure, etc.   

We will be using MinIO to store uploaded files (like CSV, TSV, or JSON files) in a local volume. This volume will be a directory on the same host machine that the current Minikube cluster is provisioned on. The YAML files for the MinIO pod, service, and ingress are featured in this repository. To create the resources (we will be using the `minio-system` namespace), run:
```bash
kubectl apply -f minio/minio-system.yaml
```
The above commands created a `minio-service` of type **LoadBalancer**. To see the list of services, run:
```bash
kubectl get services
```
and there should be a row in the table that looks like this:
| NAME           | TYPE         | CLUSTER-IP     | EXTERNAL-IP   | PORT(S)           | AGE  |
| -------------- | ------------ | -------------- | ------------- | ----------------- | ---- |
| minio-service  | LoadBalancer | 10.109.116.135 |    <none>     | 9000/TCP,9090/TCP | 86s  |

The MinIO dashboard can be accessed as follows (or it can be opened up in the browser if you are developing locally, and not on an AWS EC2 instance): 
```bash
curl http://146.141.240.78:9001/minio
```
![HTML of MinIO Console](../public/assets/images/minio-console-in-terminal.png "HTML of MinIO Console")   

If using an EC2 instance or some other vm, a simple way to access the MinIO console is by port-forwarding the service, e.g.,
```bash
kubectl port-forward --address 0.0.0.0 svc/minio-service 8088:9090
```
This will allow for the browser to access the `minio-service` on port `<ip-address-of-node>:8088`:   

![MinIO in the Browser](../public/assets/images/minio-console-in-browser.png "MinIO in the Browser")  

Default login credentials are `minioadmin` and `minioadmin`.   

(Additional information about using persistent volumes, persistent volume claims, and storage classes will be added in the future).