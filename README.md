# 📆 Projet Semaine Intensive SISR - BTS SIO 2024

### 🔖 Nom du projet : ClassCord Server - Mise en place et personnalisation d’un service de tchat multi-clients

### 🎓 Public concerné : Étudiants option SISR (Solutions d’Infrastructure, Systèmes et Réseaux)

---

## ✨ Contexte

Vous intégrez l’équipe d’administration systèmes et réseaux d’un établissement scolaire. Un projet collaboratif est mis en place entre les étudiants SISR et SLAM autour d’un outil de communication interne : **ClassCord**.

Votre mission :

* Déployer, configurer, sécuriser et faire évoluer un serveur de tchat à disposition des clients Java développés par les étudiants SLAM.
* Rendre ce serveur accessible sur le réseau local de façon sécurisée et fiable.
* Permettre à vos camarades de s’y connecter facilement, avec une documentation claire.

Le serveur vous est fourni au format Python (multi-clients avec sockets TCP). Il est volontairement simplifié pour pouvoir être personnalisé et amélioré. Votre formateur aura aussi un client opérationnel, prêt à se connecter sur votre propre serveur pour que vous puissiez tester votre travail.

---

## 🔧 Outils autorisés / recommandés

* OS : Linux (Debian, Ubuntu, etc.) ou Raspberry Pi OS
* Python 3.10+
* Git + GitHub (obligatoire)
* Docker / docker-compose (facultatif mais valorisé)
* Supervisord, systemd, cron
* Outils de journalisation/logging (rsyslog, journalctl, logrotate)
* Outils de sécurité (fail2ban, ufw, iptables, nginx, stunnel, etc.)
* Optionnel : Prometheus, Grafana, scripts bash, firewall matériel

---

## 🖥️ Préparation de l’environnement

Avant de commencer les tâches du projet, chaque étudiant doit disposer d’un environnement Linux prêt à l’emploi.

> 💡 **Si vous travaillez sur Windows ou macOS**, vous devez **créer une machine virtuelle Linux (Ubuntu, Debian, etc.)**. C’est cette VM qui hébergera le serveur Python et sur laquelle vous exécuterez toutes les commandes Linux.

Outils recommandés :

* VirtualBox ou VMware
* ISO Ubuntu Server 22.04 ou Debian 12

Une fois votre VM installée, assurez-vous que :

* Vous pouvez accéder à Internet depuis la VM
* Vous pouvez échanger des fichiers entre hôte et VM (via dossier partagé ou GitHub)
* Vous avez installé Python 3.10+, `git`, `ufw`, etc.

---

## 📅 Organisation de la semaine

Chaque journée cible une compétence du bloc infrastructure ou sécurité. Vous devez livrer à chaque étape un serveur fonctionnel et documenté, opérationnel sur le réseau local.

Un répertoire GitHub vous est attribué : [https://github.com/AstrowareConception/classcord-server](https://github.com/AstrowareConception/classcord-server)

Chaque soir, vous devez effectuer un `git push` avec README mis à jour (journal de bord, état du serveur, tests réalisés).

Les étudiants SLAM devront être capables de se connecter à votre instance en connaissant simplement :

* votre **adresse IP locale**
* votre **port d’écoute**
* la **marche à suivre** (documentée)

---

## 📕 Jour 1 - Lundi : Prise en main, exécution locale et débogage du serveur

### Objectifs de la journée :

* Cloner le dépôt GitHub fourni et comprendre le code Python du serveur minimal.
* Lancer le serveur en local sur votre machine ou VM Linux.
* Tester le serveur avec 2 clients (en local ou en LAN).
* Identifier et documenter les fonctionnalités existantes.
* Préparer la base pour la mise en réseau future (firewall, port, utilisateur).

### 🔄 Tâches à réaliser :

1. **Cloner le dépôt du projet serveur**

```bash
cd ~/BTS_SIO
git clone https://github.com/AstrowareConception/classcord-server.git
cd classcord-server
```

2. **Lire et comprendre le code Python (****`server_classcord.py`****)**

* Identifier les fonctions principales : `load_users`, `handle_client`, `broadcast`, etc.
* Noter les ports utilisés, les fichiers utilisés (`users.pkl`), les protocoles.

3. **Lancer le serveur**

```bash
python3 server_classcord.py
```

* Le serveur doit être en écoute sur le port 12345 par défaut.
* Sur une autre machine ou terminal, lancer un client compatible (ex: client SLAM) ou demander à votre formateur de se connecter avec son client.

4. **Faire un test de connexion**

* Depuis un client : se connecter en mode "invité"
* Envoyer un message : vérifier qu'il est reçu
* Ouvrir un deuxième client : tester les communications inter-clients (si supporté par les clients)

5. **Ajouter un journal de bord technique (dans le README)**

* Décrire : votre environnement, test effectué, résultat attendu et obtenu
* Captures d'écran si possible

6. **Vérifier l'ouverture du port sur votre machine**

```bash
ss -tulpn | grep 12345
```

* Commencer à configurer un firewall si nécessaire :

```bash
sudo ufw allow 12345/tcp
```

### 📄 Livrables en fin de journée :

* Serveur fonctionnel en local (ou sur réseau si possible)
* Tests de connexion entre 2 clients réussis
* README mis à jour avec journal de bord, capture écran, explications
* Premier commit Git : `git commit -am "Serveur fonctionnel en local"`

### 📉 En fin de journée vous devez être capables de :

* Démarrer le serveur Python et lire ses logs
* Accepter plusieurs connexions simultanées
* Recevoir et transmettre des messages JSON
* Voir les messages apparaître dans la console



## 📖 Jour 2 - Mardi : Déploiement sur le réseau, lancement en service et documentation d’accès

### 🎯 Objectifs pédagogiques

* Rendre le **serveur accessible depuis un poste SLAM**, malgré les contraintes réseau.
* Créer un **service système fiable** et documenté.
* Comprendre pourquoi **Docker est utile dans un contexte de virtualisation**.
* Commencer la **standardisation du déploiement via containerisation**.

---

## 🧠 Pourquoi Docker dans une VM ?

Votre serveur Python est pour l’instant lancé manuellement dans votre terminal. Ce n’est pas idéal :

* Il faut penser à le relancer à chaque démarrage
* Il dépend de l’environnement local de la VM
* D’autres étudiants ne peuvent pas le lancer facilement ailleurs

### ➕ Avec **Docker**, on peut :

✅ Emballer votre serveur dans une **image portable**

✅ Reproduire exactement le même environnement de déploiement

✅ Lancer le serveur avec une **simple commande** (`docker run ...`)

✅ Le redéployer plus tard dans un **autre contexte** (autre machine, cloud...)

> ⚠️ **On utilise Docker dans la VM**, car :
>
> * votre machine **hôte** (Windows/macOS) n’est pas homogène
> * tout le projet doit fonctionner **en local dans Linux**
> * **la VM est votre environnement cible officiel**

---

## 🖥️ Architecture réseau avec redirection NAT

Sur votre réseau pédagogique :

* Les VMs **ne sont pas directement accessibles** depuis l’extérieur
* Une redirection NAT permet de **recevoir des connexions sur le poste hôte**, qui sont redirigées vers la VM

Voici un schéma simplifié :

```
╭────────────╮          NAT (redir. port)         ╭────────────╮
│ Poste SLAM │ ─────────────────────────────────▶ │ Poste SISR │
│ 10.0.108.34│                                   │ 10.0.108.42│
╰────────────╯                                   │ (Hôte réel)│
                                                 │     ▲      │
                                                 │     │ NAT  │
                                                 │     ▼      │
                                                 │  VM Linux  │
                                                 │  192.168.X │
                                                 │ Port 12345 │
                                                 ╰────────────╯
```

> ✅ **Le SLAM se connecte à votre IP publique (10.0.108.42)**
> 🔁 **Une règle NAT redirige le port 12345 vers votre VM**

---

## 🔄 Tâches à réaliser

### 1. Vérifier que le serveur écoute sur l’adresse LAN

```bash
sudo ufw allow 12345/tcp
ss -tulpn | grep 12345
hostname -I  # pour obtenir l'IP interne (inutile pour SLAM, mais utile pour vous)
```

🟡 Demander à votre formateur si la **redirection NAT** est bien en place.
SLAM doit se connecter à l’**IP de votre hôte physique**, pas à celle de la VM.

---

### 2. Lancer un test de connexion depuis un client SLAM

* Sur un poste SLAM : saisir **votre IP publique** + port 12345
* Envoyer un message depuis le client invité
* Vérifier que le message apparaît dans la console du serveur

---

### 3. Créer un utilisateur système `classcord`

```bash
sudo useradd -m classcord
sudo passwd classcord
su - classcord
```

> Cela permet de **séparer les droits** : le serveur n’est pas lancé par un superadmin.

---

### 4. Automatiser avec `systemd`

Créer `/etc/systemd/system/classcord.service` :

```ini
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
```

Activer le service :

```bash
sudo systemctl daemon-reexec
sudo systemctl enable --now classcord.service
```

---

### 5. Rédiger une documentation de connexion (`doc_connexion.md`)

Inclure :

* IP d’accès : `10.0.108.xx` (celle de votre hôte, **pas de votre VM**)
* Port : `12345`
* Schéma réseau
* Extrait de log de connexion réussi
* Exemple d’utilisation du client Java

---

### 6. (Bonus) Script `start_server.sh` pour lancer manuellement

```bash
#!/bin/bash
python3 server_classcord.py
```

---

### 7. Créer un `Dockerfile` à la racine du projet

```Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt || true
EXPOSE 12345
CMD ["python", "server_classcord.py"]
```

---

### 8. Construire et tester l’image Docker

```bash
docker build -t classcord-server .
docker run -it --rm -p 12345:12345 classcord-server
```

✅ Cela prouve que le serveur est **portable et isolé**
✅ Cela prépare une éventuelle **migration vers le cloud ou un serveur réel**

---

### 9. (Bonus) Ajouter `docker-compose.yml`

```yaml
version: '3'
services:
  classcord:
    build: .
    ports:
      - "12345:12345"
    restart: unless-stopped
```

---

### 10. Créer un fichier `CONTAINERS.md`

Contenu :

* Pourquoi Docker ?
* Comment build, run
* Ports à exposer
* Spécificités VM + NAT

---

## 📄 Livrables attendus

* Serveur accessible depuis un client SLAM
* Démarrage automatisé avec `systemd`
* Image Docker fonctionnelle
* README à jour avec IP, port, captures et explication réseau

---

## ✅ En fin de journée, vous devez savoir

* Rendre un service accessible sur un réseau pédagogique restreint
* Lancer un service automatiquement au démarrage
* Créer une image Docker prête à être redéployée
* Rédiger une documentation technique claire


## 📗 Jour 3 - Mercredi : Sécurisation active, journalisation et sauvegardes

### Objectifs de la journée :

* Mettre en place une politique de journalisation efficace.
* Activer des mécanismes de défense contre les comportements anormaux (fail2ban, logs anormaux, ports scannés).
* Mettre en place une stratégie de sauvegarde régulière des fichiers critiques.
* Consolider la stabilité et la sécurité du service serveur.

### 🔄 Tâches à réaliser :

1. **Configurer la journalisation des événements du serveur**

* Utiliser `rsyslog`, `logrotate`, ou simplement des logs texte dans un dossier dédié (`/var/log/classcord.log`).
* Modifier le code Python si nécessaire pour écrire dans un fichier log toutes les connexions, erreurs et messages échangés.
* Exemple d’initialisation dans Python :

```python
import logging
logging.basicConfig(filename='classcord.log', level=logging.INFO, format='%(asctime)s - %(message)s')
```

2. **Mettre en place ** : **`fail2ban`**

* Créer un filtre pour bloquer les adresses IP qui se connectent trop souvent ou envoient des données invalides.
* Exemple : filtre sur tentatives de connexion erronées répétées (à adapter selon vos logs).

```bash
sudo apt install fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
```

3. **Limiter l'accès au serveur**

* Autoriser uniquement certaines IP (whitelist locale), ou bloquer toutes les adresses hors réseau local.
* Vérifier la configuration du pare-feu (`ufw`, `iptables`).

4. **Mettre en place une stratégie de sauvegarde**

* Sauvegarder le fichier `users.pkl` ou la base SQLite si utilisée.
* Automatiser via `cron` :

```bash
crontab -e
# Exemple : sauvegarde toutes les heures
0 * * * * cp /home/classcord/classcord-server/users.pkl /home/classcord/backups/users-$(date +\%F-\%H\%M).pkl
```

5. **Tester la résistance du serveur**

* Simuler des connexions massives (test multi-clients)
* Simuler une attaque brute force sur une IP, vérifier si fail2ban agit

6. **Documenter tout ce qui a été mis en place**

* Fichier `SECURITE.md` dans le dépôt avec :

  * Description des mécanismes en place
  * Exemple de log d’attaque bloquée
  * Extrait des scripts cron ou services fail2ban actifs

### 📄 Livrables attendus en fin de journée :

* Serveur avec logging actif et sécurisé
* fail2ban ou équivalent configuré
* Sauvegarde automatique en place (cron OK)
* Fichier `SECURITE.md` décrivant les mécanismes mis en œuvre
* Journal de bord technique mis à jour dans le README

### ✅ En fin de journée vous devez savoir :

* Lire et écrire des logs système ou applicatifs
* Automatiser des tâches d’administration avec cron
* Utiliser fail2ban pour bloquer des comportements suspects
* Expliquer les choix de sécurité appliqués au serveur

## 📘 Jour 4 - Jeudi : Améliorations fonctionnelles, personnalisation et préparation à la containerisation

### Objectifs de la journée :

* Ajouter des fonctionnalités serveur utiles aux clients (ex : canaux, historique, messages système).
* Rendre les données persistantes (comptes, logs, messages).
* Permettre une administration distante minimale (console, interface API, accès restreint).
* Enrichir l’expérience des utilisateurs SLAM côté serveur.

### 🔄 Tâches à réaliser :

1. **Ajouter un système de canaux de discussion**

* Adapter le traitement JSON côté serveur pour gérer plusieurs canaux (ex : `#général`, `#dev`, `#admin`).
* Exemple de message attendu :

```json
{
  "type": "message",
  "subtype": "global",
  "channel": "#dev",
  "from": "bob",
  "content": "Ping pour les devs !"
}
```

* Adapter la logique d’aiguillage pour ne diffuser un message qu’aux clients connectés au bon canal.

2. **Passer à un stockage persistant des utilisateurs/messages**

* Remplacer le fichier `users.pkl` par une base SQLite simple (`sqlite3`).
* Créer deux tables : `users` et `messages`, avec horodatage.
* Bonus : créer un script d’export des messages en CSV ou JSON.

3. **Personnaliser les messages système**

* Ajouter une fonction `send_system_message(to, content)`.
* Utiliser-la pour afficher : nouveaux arrivants, départs, alertes serveur, etc.

4. **Améliorer le logging technique du serveur**

* Enrichir les logs avec les types de messages, noms d’utilisateurs, IP, erreurs détectées.
* Générer un fichier `audit.log` ou `debug.log` selon le niveau.

5. **Bonus : créer une mini interface d’administration en ligne de commande**

* Interface texte côté serveur (ex : menu avec curses ou simple `input()`)
* Fonctions : afficher les clients actifs, stopper un canal, renvoyer une alerte globale, etc.

### 📄 Livrables attendus en fin de journée :

* Serveur enrichi avec gestion des canaux
* Base SQLite fonctionnelle avec utilisateurs et messages
* Personnalisation visible des messages système
* Log technique amélioré
* Documentation `FONCTIONNALITES.md` décrivant les ajouts faits au serveur
* README mis à jour avec captures ou exemples d'utilisation

### ✅ En fin de journée vous devez savoir :

* Modifier la logique interne du serveur pour introduire de nouvelles fonctionnalités
* Gérer un stockage persistant avec SQLite
* Fournir une API ou un menu technique rudimentaire pour les administrateurs
* Documenter proprement les fonctionnalités ajoutées

## 📙 Jour 5 - Vendredi : Finalisation, interopérabilité, démonstration, containerisation et clôture de la RP

### Objectifs de la journée :

* Valider le bon fonctionnement global du serveur avec plusieurs clients SLAM.
* Documenter de façon claire et professionnelle l’ensemble des choix techniques.
* Préparer une démonstration complète (serveur + 2 clients minimum).
* Organiser, nettoyer et finaliser votre dépôt GitHub.
* Identifier les apports réels au regard du référentiel BTS SIO.

### 🔄 Tâches à réaliser :

1. **Effectuer des tests croisés d’interopérabilité**

* Deux clients SLAM (minimum) doivent pouvoir se connecter à votre serveur.
* Tester toutes les fonctionnalités implémentées (MP, canaux, statuts, etc.).
* Vérifier la cohérence des logs, l’affichage côté client, et la stabilité réseau.

2. **Documenter proprement tout le projet**

* Finaliser votre `README.md` avec :

  * Description globale du projet
  * Architecture du serveur (technique + services)
  * Capture d’écran de logs, connexion, messages
  * Instructions d’installation/déploiement pour un autre étudiant
* Compléter les fichiers `SECURITE.md`, `FONCTIONNALITES.md`, `DOC_CONNEXION.md` si utilisés

3. **Nettoyer et organiser le dépôt Git**

* Supprimer les fichiers inutiles ou temporaires
* Organiser les scripts (répertoire `scripts/` ou `utils/` si besoin)
* Ajouter des commentaires aux parties importantes du code
* Créer des tags Git (`v1.0`, etc.) si applicable

4. **Préparer une démonstration technique claire**

* Lancer le serveur devant un formateur
* Connecter au moins 2 clients et démontrer :

  * authentification ou accès invité
  * envoi de message global et MP
  * affichage dynamique des statuts
  * journalisation active côté serveur
  * preuve de sécurité minimale (fail2ban, logs, etc.)

5. **Finaliser et tester la version Docker**

* Expliquer en quelques lignes comment lancer le serveur via Docker.
* Vérifier la compatibilité avec un ou plusieurs clients SLAM en environnement Docker.
* Bonus : tester le déploiement sur un autre poste, ou via réseau (bridge).

---

6. **Réfléchir à l’évaluation en tant que Réalisation Professionnelle**

* Remplir la fiche RP avec :

  * contexte, objectifs, livrables, contraintes
  * outils et méthodes utilisés
  * analyse critique du projet (apports, limites)

### 📄 Livrables attendus en fin de journée :

* Projet complet sur GitHub avec README finalisé
* Documentation claire, lisible, téléchargeable (PDF ou Markdown)
* Preuves de fonctionnement (captures, logs, exports SQL)
* Serveur prêt pour démonstration finale
* Fiche de réalisation professionnelle prête à l'impression ou intégrée au dépôt

### ✅ En fin de semaine vous devez être capables de :

* Déployer un service réseau sécurisé et documenté
* Gérer son cycle de vie et son interopérabilité
* Produire une documentation professionnelle
* Présenter un projet structuré et cohérent à un jury BTS SIO

* ## 🎓 Compétences mobilisées (Référentiel BTS SIO – SISR)

| Bloc de compétences | Référence | Intitulé                                                                                   |
|---------------------|-----------|---------------------------------------------------------------------------------------------|
| Concevoir une solution d’infrastructure réseau |
|                     | ✔         | Analyser un besoin exprimé et son contexte juridique                                       |
|                     | ✔         | Étudier l’impact d’une évolution d’un élément d’infrastructure sur le système informatique |
|                     | ✔         | Élaborer un dossier de choix d’une solution d’infrastructure et rédiger les spécifications techniques |
|                     | ✔         | Choisir les éléments nécessaires pour assurer la qualité et la disponibilité d’un service  |
|                     | ✔         | Maquetter et prototyper une solution d’infrastructure permettant d’atteindre la qualité de service |
|                     | ✔         | Déterminer et préparer les tests nécessaires à la validation de la solution                |
| Installer, tester et déployer une solution d’infrastructure réseau |
|                     | ✔         | Installer et configurer des éléments d’infrastructure                                      |
|                     | ✔         | Installer et configurer des éléments nécessaires pour assurer la continuité des services   |
|                     | ✔         | Rédiger ou mettre à jour la documentation technique et utilisateur                         |
|                     | ✔         | Tester l’intégration et l’acceptation d’une solution d’infrastructure                      |
|                     | ✔         | Déployer une solution d’infrastructure                                                     |
| Exploiter, dépanner et superviser une solution d’infrastructure réseau |
|                     | ✔         | Administrer sur site et à distance des éléments d’une infrastructure                       |
|                     | ✔         | Automatiser des tâches d’administration                                                    |
|                     | ✔         | Gérer des indicateurs et des fichiers d’activité des éléments d’une infrastructure         |
|                     | ✔         | Identifier, qualifier, évaluer et réagir face à un incident ou à un problème              |
|                     | ✔         | Évaluer, maintenir et améliorer la qualité d’un service                                    |



