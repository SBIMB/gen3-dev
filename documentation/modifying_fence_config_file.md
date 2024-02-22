## Modifying the Fence Config File   
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