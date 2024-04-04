## Adding a Worker Node to the K3s Cluster

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
To see what labels each node has, run the following command:
```bash
kubectl get nodes --show-labels
```
To see the labels for a specific node, specify the name of the node in the command:
```bash
kubectl label --list nodes <node_name>
```
which should produce an output similar to this:
```bash
kubernetes.io/os=linux
node.kubernetes.io/instance-type=k3s
beta.kubernetes.io/arch=amd64
beta.kubernetes.io/instance-type=k3s
beta.kubernetes.io/os=linux
kubernetes.io/arch=amd64
kubernetes.io/hostname=<node_name>
```
Labeling nodes is particularly useful, especially when there is a need to have certain workloads running on specific nodes. For example, if there are important production workloads, we may label a particular node with a key-value pair like `workload=prod`. Any pod that contains a label or annotation that includes `workload=prod` will be scheduled to run on the node with that label. As a start, we can begin by giving the newly added worker node a label of `role=worker` as follows:
```bash
kubectl label node cloud05 node-role.kubernetes.io/worker=worker
```
We can see that the labelling has worked by running:
```bash
kubectl get nodes
```
Where the output is:   

| NAME    | STATUS | ROLES                | AGE |  VERSION     |
| ------- | ------ | -------------------- | --- | ------------ |
| cloud08 | Ready  | control-plane,master | 14d | v1.27.7+k3s2 |
| cloud05 | Ready  | worker               | 40m | v1.28.4+k3s2 |

## Removing a Worker Node to the K3s Cluster
To remove a worker node from the K3s cluster, a few commands need to be run. The first step is to drain the worker node without interfering with any daemonsets (since daemonsets run on all nodes in the cluster). In our case, if we wish to remove the node `cloud05`, we run the following commands on the master node:
```bash
kubectl drain cloud05 --ignore-daemonsets  --delete-emptydir-data
kubectl delete node cloud05
```
If we wish to remove K3s completely from the worker node, we run the `uninstall` script:
```bash
sh /usr/local/bin/k3s-agent-uninstall.sh
```
If the node has been successfully removed, we should not see it listed in the table of nodes, e.g.
```bash
kubectl get nodes
```   

| NAME    | STATUS | ROLES                | AGE |  VERSION     |
| ------- | ------ | -------------------- | --- | ------------ |
| cloud08 | Ready  | control-plane,master | 14d | v1.27.7+k3s2 |
