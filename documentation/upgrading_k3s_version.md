## Upgrading K3s Version to v1.32.0
The version of our current K3s instance can be checked with the `k3s --version` command. We are going to upgrade our cluster version from `v1.29.4+k3s1` to `v1.32.0+k3s1`. Since our Kubernetes cluster is running on a single node, we will need to temporarily stop the K3s instance while performing the upgrade.   

The general form of the command for installing from the installation script is
```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=vX.Y.Z+k3s1 <EXISTING_K3S_ENV> sh -s - <EXISTING_K3S_ARGS>
```
The environment variables can be set as installation takes place. If we'd like for the environment variables to be saved for future purposes, then we can set them in a YAML file located at `/etc/rancher/k3s/config.yaml`.   

We would like to install the _latest_ stable version or release. We also do not want `servicelb` nor `traefik` installed by default, so we run:
```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable servicelb --disable traefik" sh -s - --write-kubeconfig-mode 644
```
The installation includes additional utilities such as `kubectl`, `crictl`, `ctr`, `k3s-killall.sh`, and `k3s-uninstall.sh`. `kubectl` will automatically use the `kubeconfig` file that gets written to `/etc/rancher/k3s/k3s.yaml` after the installation.   

Since we are performing an upgrade, there should exist a `.kube` directory which contains the cluster config file. This directory should be deleted and then recreated:   
```bash
rm -r ~/.kube
mkdir ~/.kube
sudo k3s kubectl config view --raw | tee ~/.kube/config
chmod 600 ~/.kube/config
export KUBECONFIG=~/.kube/config
```
For these updates to persist upon reboot, the `.profile` and `.bashrc` files should be updated with `export KUBECONFIG=~/.kube/config`.   

After about a minute or so, the following command can be run to see if the cluster is healthy:
```bash
kubectl get all -n kube-system
```
If all is well, then the `metallb` load balancer and the `nginx` ingress controller can be setup on the cluster. Instructions for this can be found in the [README](./../README.md).