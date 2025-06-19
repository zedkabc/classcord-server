import socket
import json
import os
import time

ADMIN_PORT = 54321  # Port pour communiquer avec le serveur (admin)


def clear():
    os.system('clear' if os.name == 'posix' else 'cls')


def send_admin_command(command_type, data=None):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("localhost", ADMIN_PORT))
            msg = {'type': command_type}
            if data:
                msg.update(data)
            s.sendall((json.dumps(msg) + '\n').encode())

            buffer = ''
            while True:
                chunk = s.recv(1024).decode()
                if not chunk:
                    break
                buffer += chunk
                if '\n' in buffer:
                    break

            line, _ = buffer.split('\n', 1)
            return json.loads(line)
    except Exception as e:
        print(f"\n❌ Erreur de communication avec le serveur admin : {e}\n")
        return None


def fetch_users():
    response = send_admin_command('list_users')
    if response and 'users' in response:
        return response['users']
    return []


def menu():
    while True:
        clear()
        print("=== 🎮 CLASSCORD - CONSOLE ADMIN ===\n")
        users = fetch_users()
        if not users:
            print("Aucun utilisateur enregistré.\n")
        else:
            print(f"{'Nom':<20} {'Statut':<10} Dernière activité")
            print("-" * 50)
            for user in users:
                username = user.get('username')
                state = user.get('state')
                last_seen = user.get('last_seen')
                color = "\033[92m" if state == 'online' else "\033[91m"
                print(f"{username:<20} {color}{state:<10}\033[0m {last_seen}")

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
            send_admin_command('kick', {'target': username})
        elif choice == '3':
            content = input("Message global : ").strip()
            send_admin_command('global_message', {'content': content})
        elif choice == '4':
            confirm = input("⚠️ Es-tu sûr de vouloir éteindre le serveur ? (oui/non): ").strip().lower()
            if confirm == 'oui':
                send_admin_command('shutdown')
                print("🔻 Arrêt demandé.")
                break
        elif choice == '0':
            break
        else:
            print("⛔ Choix invalide.")

        input("\nAppuie sur Entrée pour continuer...")


if __name__ == '__main__':
    menu()
