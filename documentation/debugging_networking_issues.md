### Troubleshooting Networking Issues
Some of the Gen3 deployments are not in a READY state. After running the following command,
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
from inside the VM, a full JSON response is received. However, when running that same cURL command from inside the pod (with the `--image=nicolaka/netshoot` container running for debugging purposes), we get an ssl connection refused error (see image).   
![Netshoot Debugging](/public/assets/images/netshoot-debugging.png "Netshoot Debugging")   

The command for debugging the container is
```bash
kubectl debug <podname> -it --image=nicolaka/netshoot
```
and the command for entering into a running container is
```bash
kubectl exec --stdin --tty <podname> -- bash
```
There is reason to believe that certain certificates which are on the host machine are not present or accessible in the containers.   

We could also create a `netshoot-pod` in the `default` namespace by using the following manifest:   
**netshoot-pod.yaml**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: netshoot-pod
  namespace: default
spec:
  containers:
  - name: netshoot
    image: nicolaka/netshoot
    command: ["/bin/bash", "-c", "--"]
    args: ["while true; do sleep 30; done;"]
```
The pod can be created with:
```bash
kubectl apply -f netshoot-pod.yaml
```
and a shell to the `netshoot-pod` container can be opened with:
```bash
kubectl exec -it netshoot-pod -- /bin/bash
```
While inside the container, we can hit external endpoints like:
```bash
curl http://example.com -I
```
The goal of performing such exercises is to see if containers inside the cluster can make network requests to services outside of the cluster. The following two screenshots clearly indicate that there is a problem when trying to reach external services from within the cluster.   

![HTTP Request from inside Netshoot Container](/public/assets/images/netshoot-curl-http.png "HTTP Request from inside Netshoot Container")    

![HTTPS Request from inside Netshoot Container](/public/assets/images/netshoot-curl-https.png "HTTPS Request from inside Netshoot Container")   

These requests fail. However, when setting `hostNetwork: true` in the `.spec` of the pod definition, then there is a successful response.   

![Host Network True](/public/assets/images/netshoot-hostnetwork-true.png "Host Network True")    

Setting `hostNetwork: true` in the `.spec` of the pod templates of the Gen3 deployments does not work as desired. Errors of the type 
```bash
0/1 nodes are available: 1 node(s) didn't have free ports for the requested pod ports. preemption: 0/1 nodes are available: 1 No preemption victims found for incoming pod
``` 
are encountered. We need to determine if Flannel is responsible for this network behaviour, and perhaps a different CNI should be installed (like Calico or Cilium). Before resorting to such drastic measures (I know very little about CNIs), it might be safer to restart K3s with the following flag set: `--disable-network-policy`, since K3s includes an embedded network policy controller.    

openssl s_client -connect s3.amazonaws.com:443 -servername s3.amazonaws.com

Adding the following rules to the `iptables` script might help:
```bash
#K3s Cluster
$ipt -A INPUT -d 10.42.0.9 -j ACCEPT
$ipt -A OUTPUT -d 10.42.0.9 -j ACCEPT
$ipt -A INPUT -d 10.43.0.0/16 -j ACCEPT
$ipt -A OUTPUT -d 10.43.0.0/16 -j ACCEPT
$ipt -A INPUT -d 10.42.0.0/16 -j ACCEPT
$ipt -A OUTPUT -d 10.42.0.0/16 -j ACCEPT
$ipt -A INPUT -i eth0 -p tcp --dport 6443 -m state --state NEW,ESTABLISHED -j ACCEPT
$ipt -A INPUT -i eth0 -p tcp --dport 10250 -m state --state NEW,ESTABLISHED -j ACCEPT
$ipt -A INPUT -i eth0 -p tcp -m tcp --dport 0:65535 -j ACCEPT
$ipt -A INPUT -i eth0 -p tcp -m tcp --dport 2379:2380 -j ACCEPT
$ipt -A INPUT -p udp --dport 8472 -m multiport --sports 0:65535 -j ACCEPT
$ipt -A INPUT -p udp --dport 51820 -m multiport --sports 0:65535 -j ACCEPT
$ipt -A INPUT -p udp --dport 51821 -m multiport --sports 0:65535 -j ACCEPT
$ipt -A INPUT -i eth0 -p tcp --dport 80 -m comment --comment "# http #" -j ACCEPT
$ipt -A INPUT -i eth0 -p tcp --dport 443 -m comment --comment "# https #" -j ACCEPT
```
To temporarily disable the Firewall, run the following:
```bash
sudo iptables -P INPUT ACCEPT
sudo iptables -P FORWARD ACCEPT
sudo iptables -P OUTPUT ACCEPT
sudo iptables -t nat -F
sudo iptables -t mangle -F
sudo iptables -F
sudo iptables -X
```

While inside the `netshoot` pod, we can run 
```bash
cat /etc/resolv.conf
```
to see which nameserver address the pod is using. We get an output of the form,
```bash
search default.svc.cluster.local svc.cluster.local cluster.local DOMAINS
nameserver 10.43.0.10
options ndots:5
```   
which has the same ip address as the `service/kube-dns` in the `kube-system` namespace.   

When running
```bash
cat /etc/resolv.conf
```
on the node, we get the following response:
```bash
# Dynamic resolv.conf(5) file for glibc resolver(3) generated by resolvconf(8)
#     DO NOT EDIT THIS FILE BY HAND -- YOUR CHANGES WILL BE OVERWRITTEN
# 127.0.0.53 is the systemd-resolved stub resolver.
# run "systemd-resolve --status" to see details about the actual nameservers.

nameserver 146.141.8.16
nameserver 146.141.15.210
nameserver 8.8.8.8
nameserver 8.8.4.4
nameserver 127.0.0.53
```

When running
```bash
cat /etc/resolv.conf
```
inside the `netshoot-pod` container, we get the following response:
```bash
search default.svc.cluster.local svc.cluster.local cluster.local DOMAINS
nameserver 10.43.0.10
options ndots:5
```

Create an NGINX load balancer that runs inside a Docker container:
```bash
sudo docker run -d --restart unless-stopped \
    -v ${PWD}/nginx.conf:/etc/nginx/nginx.conf \
    -p 6443:6443 \
    nginx:stable
```

**DNS Settings**
The command `cat /run/systemd/resolve/resolv.conf` displays the following: 
```bash
# This is /run/systemd/resolve/resolv.conf managed by man:systemd-resolved(8).
# Do not edit.
#
# This file might be symlinked as /etc/resolv.conf. If you're looking at
# /etc/resolv.conf and seeing this text, you have followed the symlink.
#
# This is a dynamic resolv.conf file for connecting local clients directly to
# all known uplink DNS servers. This file lists all configured search domains.
#
# Third party programs should typically not access this file directly, but only
# through the symlink at /etc/resolv.conf. To manage man:resolv.conf(5) in a
# different way, replace this symlink by a static file or a different symlink.
#
# See man:systemd-resolved.service(8) for details about the supported modes of
# operation for /etc/resolv.conf.

nameserver 146.141.8.16
nameserver 146.141.15.210
nameserver 8.8.8.8
# Too many DNS servers configured, the following entries may be ignored.
nameserver 8.8.4.4
search DOMAINS
```
The stubbed form of the `resolv.conf` file has the following contents, which can be seen after running `cat /run/systemd/resolve/stub-resolv.conf`:
```bash
# This is /run/systemd/resolve/stub-resolv.conf managed by man:systemd-resolved(8).
# Do not edit.
#
# This file might be symlinked as /etc/resolv.conf. If you're looking at
# /etc/resolv.conf and seeing this text, you have followed the symlink.
#
# This is a dynamic resolv.conf file for connecting local clients to the
# internal DNS stub resolver of systemd-resolved. This file lists all
# configured search domains.
#
# Run "resolvectl status" to see details about the uplink DNS servers
# currently in use.
#
# Third party programs should typically not access this file directly, but only
# through the symlink at /etc/resolv.conf. To manage man:resolv.conf(5) in a
# different way, replace this symlink by a static file or a different symlink.
#
# See man:systemd-resolved.service(8) for details about the supported modes of
# operation for /etc/resolv.conf.

nameserver 127.0.0.53
options edns0 trust-ad
search DOMAINS
```
The `/etc/resolv.conf` file contains the following:
```bash
# Dynamic resolv.conf(5) file for glibc resolver(3) generated by resolvconf(8)
#     DO NOT EDIT THIS FILE BY HAND -- YOUR CHANGES WILL BE OVERWRITTEN
# 127.0.0.53 is the systemd-resolved stub resolver.
# run "systemd-resolve --status" to see details about the actual nameservers.

nameserver 146.141.8.16
nameserver 146.141.15.210
nameserver 8.8.8.8
nameserver 8.8.4.4
nameserver 127.0.0.53
```
The `/etc/resolv.conf` file needs to be symlinked to the `/run/systemd/resolve/resolv.conf` file, not the stubbed version.   

The command `nslookup 146.141.8.16` gives the following result:
```bash
16.8.141.146.in-addr.arpa	name = thebe.ds.wits.ac.za.
```
The command `nslookup 146.141.15.210` gives the following result:
```bash
210.15.141.146.in-addr.arpa	name = mail1.wits.ac.za.
```
We need to modify the `resolv.conf` file by removing the top two nameserver ip addresses, since they are not allowing us to access the public internet. We should use `8.8.8.8`, which is the primary DNS server for Google DNS.   

To change the DNS server, we need to configure the `/etc/network/interfaces` file. The command `cat /etc/network/interfaces` displays the following:
```bash
# This file describes the network interfaces available on your system
# and how to activate them. For more information, see interfaces(5).

source /etc/network/interfaces.d/*

# The loopback network interface
auto lo
iface lo inet loopback

# The primary network interface
auto eno0
iface eno0 inet manual






auto br0
iface br0 inet static
      address 146.141.240.78
      netmask 255.255.255.0
      network 146.141.240.0
      broadcast 146.141.240.255
      gateway 146.141.240.10
      bridge_ports eno0
      bridge_stp off
      bridge_fd 0
      bridge_maxwait 0
      dns-nameservers 146.141.8.16 146.141.15.210 8.8.8.8
```
We can see that the `dns-nameservers` contains those two ip addresses that are giving us trouble. We should remove those and end up with 
```bash
dns-nameservers 8.8.8.8 8.8.4.4
```
First, we should ensure that the `resolvconf` service is enabled and running with:
```bash
sudo systemctl status resolvconf.service
```
If there is no response, then the service can be started and enabled with
```bash
sudo systemctl start resolvconf.service
sudo systemctl enable resolvconf.service
```
Now the `/etc/resolvconf/resolv.conf.d/head` file can be edited with
```bash
sudo vim /etc/resolvconf/resolv.conf.d/head
```
by removing the two unwanted ip addresses and replacing them with `8.8.8.8` and `8.8.4.4`. These updated scripts can be forced to run with
```bash
sudo resolvconf --enable-updates
sudo resolvconf -u
```
This should change the DNS settings of the host machine. The following commands can also be run if necessary:
```bash
sudo systemctl restart resolvconf.service
sudo systemctl restart systemd-resolved.service
```

**Disabling IPv6 via sysctl settings**
If either of the following commands return a result,
```bash
ip -6 addr
```
or
```bash
ip a | grep inet6 
```
then IPv6 is enabled on your system. To temporarily disable IPv6 settings using `sysctl`, run the following commands:
```bash
sysctl -w net.ipv6.conf.all.disable_ipv6=1
sysctl -w net.ipv6.conf.default.disable_ipv6=1
sysctl -w net.ipv6.conf.lo.disable_ipv6=1
```
To make these changes permanent, the `/etc/sysctl.conf` configuration file needs to be modified as follows:
```bash
net.ipv6.conf.all.disable_ipv6=1
net.ipv6.conf.default.disable_ipv6=1
net.ipv6.conf.lo.disable_ipv6 = 1
```
The following command will apply these changes:
```bash
sysctl -p
```
If IPv6 has been successfully disabled, then the following command,
```bash
cat /proc/sys/net/ipv6/conf/all/disable_ipv6
```
should yield an output of `1`.   

To re-enable IPv6, remove from the `/etc/sysctl.conf` file those three lines that were added above, and then apply the changes. A reboot of the system might also be required, i.e. `sudo reboot`.
