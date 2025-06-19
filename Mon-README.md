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
- Tapez : 10.0.108.56
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

# Jour 3

## Configuration de la journalisation des événements du serveur :

- Remplacement des "print" du code par des "logging"

## Mise en place de Fail2Ban :

- sudo apt install fail2ban
- sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

## Mise en place d'une stratégie de sauvegarde :

- Sauvegarde du fichier user.plk dans classcord-server
- Automatisation via "cron" :
   - crontab -e
   - Ajout de "0 * * * * cp /home/classcord/classcord-server/users.pkl /home/classcord/backups/users-$(date +\%F-\%H\%M).pkl" dedans

# Jour 4

## Ajout d'un système de canaux de discussions :

- Modification du code afin d'ajouter ce système

## Passage à un stockage persistant des utilisateurs/messages

### Remplacement du fichier users.pkl par une base SQLite simple (sqlite3) :

- Modification du code :
   Création d'une base SQLite pour les utilisateurs.
   Modification du code Python pour lire/écrire les utilisateurs dans cette base.
   Suppression des références à users.pkl.
- Suppression du fichier : rm users.pkl

### Création de deux tables : users et messages, avec horodatage :

- Modification du code :
   Connexion à classcord.db
   Remplacement de users.pkl par des requêtes SQL
   Insertion des messages dans la base

## Personnalisation des messages sytèmes 

### Ajout d'une fonction send_system_message(to, content) :

- Modification du code :
   Ajout d'une fonction send_system_message(to_username, content) qui envoie un message système    ciblé.

## Amélioration du logging technique du serveur

### Enrichissement des logs avec les types de messages, noms d’utilisateurs, IP, erreurs détectées : 

- Modification du code : Ajout dans chaque log les éléments utiles qui contextualisent l’événement (utilisateur, IP, type de message)

### Généreration d'un fichier audit.log ou debug.log selon le niveau

## Création d'une interface admin 

### Contenu du menu admin : 

- Affichage des clients actifs sur le serveur
- Envoi d'alerte globale
- Bannissement d'un client
- Eteindre le serveur





















