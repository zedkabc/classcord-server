import socket
import json
import time
import os

ADMIN_PORT = 54321  # Port pour communiquer avec le serveur admin

def clear():
    os.system('clear' if os.name == 'posix' else 'cls')

def send_admin_command(command_type, data=None, expect_response=False):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("localhost", ADMIN_PORT))
            msg = {'type': command_type}
            if data:
                msg.update(data)
            s.sendall((json.dumps(msg) + '\n').encode())

            if expect_response:
                buffer = ''
                while True:
                    chunk = s.recv(1024).decode()
                    if not chunk:
                        break
                    buffer += chunk
                    if '\n' in buffer:
                        line, _ = buffer.split('\n', 1)
                        return json.loads(line)
    except Exception as e:
        print(f"❌ Erreur en envoyant la commande admin : {e}")
        return None

def menu():
    while True:
        clear()
        print("=== 🎮 CLASSCORD - CONSOLE ADMIN ===\n")
        
        response = send_admin_command('get_users', expect_response=True)
        if not response or 'users' not in response:
            print("Aucun utilisateur enregistré ou erreur de connexion.\n")
        else:
            users = response['users']
            if not users:
                print("Aucun utilisateur connecté.\n")
            else:
                print(f"{'Nom':<20} {'Statut':<10}")
                print("-" * 30)
                for username in users:
                    print(f"{username:<20} \033[92monline\033[0m")

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
