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

