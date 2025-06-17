# ClassCord Server – Projet Semaine Intensive SISR – BTS SIO 2025

## Auteur :

- Louka LAVENIR
- Classe : BTS SIO - Option SISR

## Dépôt GitHub :

- https://github.com/zedkabc/classcord-server

## Environnement de travail :

- **Machine physique :** Windows 11
- **VM :** Debian 12 sous VirtualBox
- **Réseau :** Mode Accès NAT
- **Python :** v3.13.5

# Jour 1

## Installation

### Créer la V.M. :

- V.M créée sur VirtualBox avec l'ISO Debian 12

### Cloner le dépôt :

- git clone https://github.com/zedkabc/classcord-server.git

### Aller dans serveur : 

- cd classcord-server

### Lancer le serveur :

- python3 server_classcord.py

## Connexion pour un étudiant SLAM

- Voici la procédure pour te connecter au serveur ClassCord hébergé sur ma machine :

### Prérequis :

- Avoir accès au réseau local (Wi-Fi ou Ethernet) sur lequel se trouve le serveur.
- Connaitre l’adresse IP et le port du serveur.

### Infos du serveur :

- Adresse IP : 10.0.108.144 (remplace si elle change)
- Port : 12345

### Étapes de connexion :

- Lancez votre client
- Quand le programme vous demande l'adresse IP :
- Tapez : 10.0.108.66
- Quand il vous demande le port :
- Tapez : 12345
- Cliquez sur “Connexion” ou validez.

### Assurez-vous que :

- Vous êtes bien connecté au même réseau que la machine serveur (ex : même Wi-Fi)
- Vous n’avez pas de pare-feu qui bloque la sortie (pare-feu personnel ou antivirus)
- Le firewall (ufw) autorise les connexions entrantes sur ce port : sudo ufw allow 12345
- Le serveur est sur écoute : sudo ss -tulpn | grep 12345

# Jour 2

## Création d'utilisateur système 

### Créer utilisateur :

- sudo useradd -m classcord
- MDP : sudo passwd classcord : class89

### Se connecter en tant que classcord :

- su - classcord

## Automatisation avec systemd

### Création du dossier classcord.service 

- sudo nano /etc/systemd/system/classcord.service
- Contenu :
[Unit]
Description=Serveur ClassCord
After=network.target

[Service]
User=classcord
WorkingDirectory=/home/classcord/classcord-server
ExecStart=/usr/bin/python3 /home/classcord/classcord-server/server_classcord.py
Restart=on-failure

[Install]
WantedBy=multi-user.target

### Activation du service

- sudo systemctl daemon-reexec
- sudo systemctl enable --now classcord.service

## Création d'un Dockerfile à la racine du projet

### Création du fichier : 

- sudo nano Dockerfile
- Programme : 
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt || true
EXPOSE 12345
CMD ["python", "server_classcord.py"]

### Construction de l'image Dockerfile :

- sudo docker build -t classcord-server .

### Test de l'image :

- docker run -it --rm -p 12345:12345 classcord-server


