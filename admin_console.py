import socket
import json
import time
import os

ADMIN_PORT = 54321  # Port utilisé pour se connecter au serveur admin

# Fonction pour nettoyer l'écran (compatible Windows / Linux / macOS)
def clear():
    os.system('clear' if os.name == 'posix' else 'cls')

# Fonction utilitaire pour envoyer une commande au serveur admin
def send_admin_command(command_type, data=None, expect_response=False):
    try:
        # Création de la connexion TCP avec le serveur admin
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("localhost", ADMIN_PORT))  # Connexion à localhost sur le port admin
            msg = {'type': command_type}         # Préparation de la commande JSON
            if data:
                msg.update(data)                 # Ajout des données optionnelles (ex: nom à kicker)
            s.sendall((json.dumps(msg) + '\n').encode())  # Envoi du message

            # Si une réponse est attendue (ex: pour get_users)
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

# Menu principal de la console admin
def menu():
    while True:
        clear()
        print("=== 🎮 CLASSCORD - CONSOLE ADMIN ===\n")
        
        # Demande au serveur la liste des utilisateurs connectés
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
                    print(f"{username:<20} \033[92monline\033[0m")  # Affiche "online" en vert

        # Affichage du menu des options
        print("\nOptions :")
        print("1. Rafraîchir")
        print("2. Kicker un utilisateur")
        print("3. Envoyer un message global")
        print("4. Éteindre le serveur")
        print("0. Quitter\n")

        choice = input("Choix : ").strip()

        if choice == '1':
            continue  # Rafraîchit juste l'affichage
        elif choice == '2':
            username = input("Nom d'utilisateur à kicker : ").strip()
            send_admin_command('kick', {'target': username})  # Envoie la commande 'kick'
        elif choice == '3':
            content = input("Message global : ").strip()
            send_admin_command('global_message', {'content': content})  # Envoie le message à tous
        elif choice == '4':
            confirm = input("⚠️ Es-tu sûr de vouloir éteindre le serveur ? (oui/non): ").strip().lower()
            if confirm == 'oui':
                send_admin_command('shutdown')  # Arrête le serveur
                print("🔻 Arrêt demandé.")
                break
        elif choice == '0':
            break  # Quitte la console admin
        else:
            print("⛔ Choix invalide.")

        input("\nAppuie sur Entrée pour continuer...")  # Pause avant de réafficher le menu

# Point d’entrée du script
if __name__ == '__main__':
    menu()
