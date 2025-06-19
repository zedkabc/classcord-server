import sqlite3
import time
import os

DB_FILE = 'classcord.db'

def clear():
    os.system('clear' if os.name == 'posix' else 'cls')

def fetch_users():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, state, last_seen FROM users ORDER BY state DESC, last_seen DESC")
        return cursor.fetchall()

def main():
    while True:
        clear()
        print("=== CLASSCORD ADMIN CONSOLE ===\n")
        users = fetch_users()
        if not users:
            print("Aucun utilisateur enregistré.")
        else:
            print(f"{'Nom':<20} {'Statut':<10} Dernière activité")
            print("-" * 50)
            for username, state, last_seen in users:
                status_color = "\033[92m" if state == 'online' else "\033[91m"
                print(f"{username:<20} {status_color}{state:<10}\033[0m {last_seen}")
        print("\nAppuie sur Ctrl+C pour quitter.")
        time.sleep(3)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nFermeture de la console admin.")
