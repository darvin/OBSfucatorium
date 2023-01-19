# OBSfucatorium
A webservice that provides OBS studio scene switching and monitoring of remote server over the stream


# Install

```
git clone git@github.com:darvin/OBSfucatorium.git
cd OBSfucatorium

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt


```

# Install default monitoring suite

```
sudo apt-add-repository ppa:obsproject/obs-studio
sudo apt-get update
sudo apt-get install obs-studio
sudo apt install glances
sudo npm install -g gtop
```