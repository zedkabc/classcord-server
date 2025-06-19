import socket
import json
import os

ADMIN_PORT = 54321
ADMIN_HOST = "localhost"

def clear():
    os.system('clear' if os.name == 'posix' else 'cls')

def send_admin_command_and_receive(command, data=None):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ADMIN_HOST, ADMIN_PORT))
            msg = {'type': command}
            if data:
                msg.update(data)
            s.sendall((json.dumps(msg) + '\n').encode())

            # Lire la réponse complète (en supposant une petite réponse)
            response = ''
            while True:
                chunk = s.recv(4096).decode()
                if not chunk:
                    break
                response += chunk
                # On s’arrête si on trouve la fin (ici pas de marqueur, on lit tout)
                # Pour simplifier on suppose que le serveur ferme la connexion après la réponse
            return response
    except Exception as e:
        return f"❌ Erreur lors de la communication avec le serveur admin : {e}"

def parse_and_print_users(response):
    try:
        data = json.loads(response)
        users = data.get('users', [])
        if not users:
            print("Aucun utilisateur connecté.\n")
            return
        print(f"{'Nom':<20} {'Statut':<10} Dernière activité")
        print("-" * 50)
        for user in users:
            username = user.get('username', '???')
            state = user.get('state', 'unknown')
            last_seen = user.get('last_seen', '')
            color = "\033[92m" if state == 'online' else "\033[91m"
            print(f"{username:<20} {color}{state:<10}\033[0m {last_seen}")
    except Exception:
        # Si ce n’est pas JSON on affiche en brut
        print(response)

def menu():
    while True:
        clear()
        print("=== 🎮 CLASSCORD - CONSOLE ADMIN ===\n")

        # Demande liste utilisateurs connectes
        response = send_admin_command_and_receive('list_users')
        parse_and_print_users(response)

        print("\nOptions :")
        print("1. Rafraîchir")
        print("2. Kicker un utilisateur")
        print("3. Envoyer un message global")
        print("4. Éteindre le serveur")
        print("0. Quitter\n")

        choice = input("Choix : ").strip()

        if choice == '1':
            continue

        elif choice == '2':
            username = input("Nom d'utilisateur à kicker : ").strip()
            resp = send_admin_command_and_receive('kick', {'target': username})
            print(resp)

        elif choice == '3':
            content = input("Message global : ").strip()
            resp = send_admin_command_and_receive('broadcast', {'content': content})
            print(resp)

        elif choice == '4':
            confirm = input("⚠️ Es-tu sûr de vouloir éteindre le serveur ? (oui/non): ").strip().lower()
            if confirm == 'oui':
                resp = send_admin_command_and_receive('shutdown')
                print(resp)
                print("🔻 Arrêt demandé.")
                break

        elif choice == '0':
            print("Au revoir.")
            break

        else:
            print("⛔ Choix invalide.")

        input("\nAppuie sur Entrée pour continuer...")

if __name__ == '__main__':
    menu()
