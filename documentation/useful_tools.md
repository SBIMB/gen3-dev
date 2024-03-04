## Installing the k9s Tool (Optional)
**k9s** is a useful tool that makes troubleshooting issues in a Kubernetes cluster easier. Installing it is highly recommended. It can be downloaded and installed as follows:
```bash
wget https://github.com/derailed/k9s/releases/download/v0.32.0/k9s_Linux_amd64.tar.gz
tar -xzvf k9s_Linux_amd64.tar.gz
chmod +x k9s
sudo mv k9s /usr/local/bin/
```
To open it, simply run:
```bash
k9s
```