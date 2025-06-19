import socket
import json

def afficher_menu(users):
    print("\n= 🎮 CLASSCORD - CONSOLE ADMIN ===\n")
    if not users:
        print("Aucun utilisateur connecté.\n")
    else:
        print("Utilisateurs connectés :")
        for u in users:
            print(f"- {u}")
        print()
    print("Options :")
    print("1. Rafraîchir la liste")
    print("2. Kicker un utilisateur")
    print("3. Envoyer un message global")
    print("4. Éteindre le serveur")
    print("0. Quitter\n")

def envoyer_message(sock, data):
    sock.sendall(json.dumps(data).encode() + b'\n')

def recevoir_reponse(sock):
    data = b''
    while b'\n' not in data:
        more = sock.recv(1024)
        if not more:
            break
        data += more
    if not data:
        return None
    try:
        return json.loads(data.decode().strip())
    except:
        return None

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', 12345))

    while True:
        envoyer_message(s, {'type': 'list_users'})
        response = recevoir_reponse(s)

        users = []
        if response and response.get('type') == 'list_users':
            users = response.get('users', [])

        afficher_menu(users)

        choix = input("Choix : ").strip()
        if choix == '0':
            print("Fermeture du client admin.")
            break

        elif choix == '1':
            continue  # Rafraîchir (boucle relance)

        elif choix == '2':
            if not users:
                print("Aucun utilisateur à kicker.")
                continue
            to_kick = input("Nom de l'utilisateur à kicker: ").strip()
            if to_kick not in users:
                print("Utilisateur non connecté.")
                continue
            envoyer_message(s, {'type': 'kick_user', 'username': to_kick})
            reponse_kick = recevoir_reponse(s)
            if reponse_kick and reponse_kick.get('type') == 'error':
                print("Erreur:", reponse_kick.get('message'))

        elif choix == '3':
            msg = input("Message global à envoyer: ").strip()
            if msg:
                envoyer_message(s, {'type': 'global_message', 'content': msg})

        elif choix == '4':
            confirm = input("⚠️ Es-tu sûr de vouloir éteindre le serveur ? (oui/non): ").strip().lower()
            if confirm == 'oui':
                envoyer_message(s, {'type': 'shutdown'})
                print("Commande arrêt envoyée.")
                break
            else:
                print("Annulé.")

        else:
            print("Option inconnue.")

    s.close()

if __name__ == '__main__':
    main()
