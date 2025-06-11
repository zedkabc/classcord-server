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

Le serveur vous est fourni au format Python (multi-clients avec sockets TCP). Il est volontairement simplifié pour pouvoir être personnalisé et amélioré.

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
Tu as parfaitement raison : pour assurer la **cohérence avec le projet SLAM** et respecter les bonnes pratiques GitHub, les SISR doivent aussi **forker** le dépôt avant de le cloner.

Voici le bloc mis à jour, **au bon format Markdown**, à remplacer dans ton document (README ou énoncé) :

---

## 📅 Organisation de la semaine

Chaque journée cible une compétence du bloc infrastructure ou sécurité. Vous devez livrer à chaque étape un serveur fonctionnel et documenté, opérationnel sur le réseau local.

Un repository GitHub contient les consignes et le code de base du serveur : [https://github.com/AstrowareConception/classcord-server](https://github.com/AstrowareConception/classcord-server)

> 🎯 **Chaque étudiant doit travailler dans un dépôt GitHub personnel issu d’un fork de ce projet.**

### Étapes à suivre :

1. **Forkez** le dépôt [classcord-server](https://github.com/AstrowareConception/classcord-server) sur votre compte GitHub.
2. Sur votre fork, cliquez sur **Code > HTTPS** et copiez l’URL.
3. Ouvrez un terminal Linux (ou VSCode en SSH) et tapez :

```bash
cd ~/BTS_SIO
git clone https://github.com/votre-identifiant/classcord-server.git
cd classcord-server
```

4. Enregistrez votre travail régulièrement :

```bash
git add .
git commit -m "ex: configuration du pare-feu + test local"
git push origin main
```

---

### 📌 Contraintes GitHub pour la validation

* Travail **exclusivement sur votre fork GitHub**
* Projet avec **au moins 1 commit par jour, clair et structuré**
* Un `README.md` personnel contenant :

  * vos **nom et prénom**
  * les **services mis en place**
  * la **documentation d’accès au serveur**

---

Chaque soir, vous devez effectuer un `git push` avec README mis à jour (journal de bord, état du serveur, tests réalisés).

Les étudiants SLAM devront être capables de se connecter à votre instance en connaissant simplement :

* votre **adresse IP locale**
* votre **port d’écoute**
* la **marche à suivre** (documentée)

---

## 📕 Jour 1 - Lundi : Prise en main, exécution locale et débogage du serveur

### Objectifs de la journée :

* Forker et cloner le dépôt GitHub contenant le serveur minimal
* Comprendre le code Python fourni et son fonctionnement général
* Lancer le serveur en local sur votre machine ou VM Linux.
* Tester le serveur avec 2 clients (en local ou en LAN).
* Identifier et documenter les fonctionnalités existantes.
* Préparer la base pour la mise en réseau future (firewall, port, utilisateur).

### 🔄 Tâches à réaliser :

1. **Forker puis cloner le dépôt du projet serveur**

- Forkez le dépôt sur votre propre compte GitHub (voir section précédente)
- Clonez ensuite votre fork depuis votre terminal :

```bash
cd ~/BTS_SIO
git clone https://github.com/votre-identifiant/classcord-server.git
cd classcord-server
```

2. **Lire et comprendre le code Python (`server_classcord.py`)**

* Identifier les fonctions principales : `load_users`, `handle_client`, `broadcast`, etc.
* Noter les ports utilisés, les fichiers utilisés (`users.pkl`), les protocoles.

3. **Lancer le serveur**

```bash
python3 server_classcord.py
```

* Le serveur doit être en écoute sur le port 12345 par défaut.
* Sur une autre machine ou terminal, lancer un client compatible (ex: client SLAM).

4. **Faire un test de connexion**

* Depuis un client : se connecter en mode "invité"
* Envoyer un message : vérifier qu'il est reçu
* Ouvrir un deuxième client : tester les communications inter-clients

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

### Objectifs de la journée :

* Rendre le serveur accessible sur le réseau local (LAN) de la salle.
* Créer un utilisateur système spécifique pour exécuter le serveur.
* Mettre en place un lancement automatique avec `systemd` ou `supervisord`.
* Documenter clairement la procédure de connexion pour les étudiants SLAM.
* Commencer à protéger l'accès au serveur (port, journalisation, détection de comportements anormaux).

### 🔄 Tâches à réaliser :

1. **Configurer le serveur sur votre machine Linux**

* S'assurer que le port 12345 est bien à l'écoute sur l'adresse LAN (ex: `192.168.X.X`).
* Autoriser le port dans `ufw` ou `iptables`.

```bash
sudo ufw allow 12345/tcp
hostname -I  # pour obtenir votre IP locale
```

2. **Tester une connexion distante depuis un client SLAM**

* Sur une autre machine : entrer IP + port dans l'application client.
* Vérifier la réception des messages dans la console serveur.

3. **Créer un utilisateur dédié au serveur Python**

```bash
sudo useradd -m classcord
sudo passwd classcord
```

* Lancer le serveur depuis ce compte (via `su - classcord`).

4. **Mettre en place un service systemd** (`/etc/systemd/system/classcord.service`)

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

```bash
sudo systemctl daemon-reexec
sudo systemctl enable --now classcord.service
```

5. **Rédiger une documentation de connexion à destination des SLAM**

* Format `README.md` ou `doc_connexion.md`
* Contient : IP, port, conditions d’accès, exemple de client, schéma réseau
* Inclure des captures d’écran du test de connexion

6. **Bonus : écriture d'un petit script `start_server.sh`**

* Pour permettre un redémarrage manuel rapide du serveur par un non-admin

### 📄 Livrables attendus en fin de journée :

* Serveur joignable depuis une autre machine du réseau
* Lancement automatisé du serveur à l’allumage
* Documentation de connexion fonctionnelle pour les SLAM
* Journal de bord mis à jour dans le README (avec tests + IP)

### 📊 En fin de journée vous devez savoir :

* Configurer un service réseau en écoute sur votre machine
* Le rendre accessible et maintenu automatiquement
* Fournir une documentation claire à un tiers technique

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

2. **Mettre en place `fail2ban`**

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

## 📘 Jour 4 - Jeudi : Améliorations fonctionnelles et personnalisation du serveur

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

## 📙 Jour 5 - Vendredi : Finalisation, interopérabilité, démonstration et clôture de la RP

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

5. **Réfléchir à l’évaluation en tant que Réalisation Professionnelle**

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

* ---

## 🎓 Compétences mobilisées (Référentiel BTS SIO – SISR)

| Bloc de compétences | Référence | Intitulé                                                      |
|---------------------|-----------|----------------------------------------------------------------|
| Bloc 1              | A1.1.1    | Analyse du cahier des charges d’un service à produire         |
| Bloc 1              | A1.2.1    | Élaboration d’une solution d’infrastructure                    |
| Bloc 2              | A2.3.1    | Installation et configuration d’éléments d’infrastructure      |
| Bloc 2              | A2.3.2    | Déploiement d’un service                                       |
| Bloc 2              | A2.3.3    | Administration d’un service réseau                            |
| Bloc 2              | A2.3.4    | Sécurisation d’un service réseau                              |
| Bloc 3              | A3.1      | Supervision et maintenance d’une infrastructure                |
| Bloc 3              | A3.2      | Sauvegarde, restauration et audit                             |
| Bloc 4              | A4.1      | Gestion des accès et des authentifications                    |
| Bloc 4              | A4.3      | Mise en place de la traçabilité et de l’alerte                |
| Bloc 5              | A5.1.1    | Mise en place de la documentation technique                   |
| Bloc 5              | A5.2.3    | Présentation d’un service à un utilisateur                    |

> Ce projet peut être valorisé en E4 (U41 - Projets SISR) ou en E5 (U51 - Parcours SISR)

