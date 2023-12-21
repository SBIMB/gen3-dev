## Upgrading Traefik Ingress to v2.10
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