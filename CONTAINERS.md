# Conteneurisation du projet `classcord-server`

## Pourquoi Docker ?

- Isolation : Chaque application tourne dans son propre conteneur, sans impacter le système hôte ni les autres services.
- Portabilité : Le conteneur fonctionne de la même façon sur tous les systèmes (Linux, Windows, macOS).
- Reproductibilité : L’environnement est identique à chaque lancement grâce au Dockerfile.
- Simplicité de déploiement : Plus besoin d’installer manuellement les dépendances, tout est packagé dans l’image.
- Rapidité : Les conteneurs démarrent rapidement et consomment moins de ressources qu’une machine virtuelle classique.

---

## Comment build et run le conteneur

### 1. Créer l’image Docker

```bash
sudo docker build -t classcord-server .
```

> Assurez-vous que le `Dockerfile` est dans le même dossier que `server_classcord.py`.

### 2. Lancer le conteneur

```bash
docker run -it --rm -p 12345:12345 -p 54321:54321 classcord-server```

- `-d` : Exécution en arrière-plan (détaché)
- `--name` : Nom du conteneur
- `-p` : Mappage des ports

---

## Ports à exposer

Le serveur utilise les ports '12345' et '54321', mappés depuis le conteneur vers l'hôte :

```
HOST:12345  →  CONTAINER:12345  (Port principal du serveur)
HOST:54321  →  CONTAINER:54321  (Port pour la table admin)

```

---

## Spécificités VM + NAT

- Lorsque le projet est lancé dans une machine virtuelle (VM) en mode NAT, un accès depuis l’ordinateur hôte nécessite la configuration d’une redirection de port.

Exemple de configuration dans VirtualBox :
-  Aller dans : Paramètres de la VM > Réseau > Avancé > Redirection de ports
- Ajouter une règle :
- Nom : classcord
- Protocole : TCP
- Port hôte : 12345
- Port invité : 12345

Cette configuration permet d’accéder au serveur lancé dans la VM via 127.0.0.1:12345 depuis l’hôte..

---

## Exemple de test

```bash
nc localhost 12345
{"type": "login", "username": "louka", "password": "azerty"}
```
