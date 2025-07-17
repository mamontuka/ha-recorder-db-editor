# cli.py

import os
import traceback
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from fixer import RecorderFixer
import subprocess
import getpass

DEFAULT_DB_PATH = "/config/home-assistant_v2.db"

def build_completer(entity_ids):
    entity_completer = {e: None for e in entity_ids}

    sensor_completer = {
        "delete": entity_completer,
        "values": entity_completer,
        "raw": entity_completer,
        "find": entity_completer,
        "list_all": None,
    }

    completer = NestedCompleter.from_nested_dict({
        "sensor": sensor_completer,
        "clear": None,
        "help": None,
        "exit": None,
        "password": None,
    })
    return completer

def print_help():
    print("""
Available commands:

Sensor commands:

  sensor list_all                    - List all sensors with their metadata_id

  sensor find <entity_id>            - Show metadata_id + quick state preview
  sensor values <entity_id>          - Show all unique state values of a sensor
  sensor raw <entity_id>             - Show last 200 raw records for a sensor
  
  sensor delete <entity_id> <value>  - Delete entries with specific state value

Other commands:
  password                           - Change password for user 'debug'
  clear                              - Clear the screen
  help                               - Show this help message
  exit                               - Exit the shell
""")

def initialize_fixer(db_path):
    fixer = RecorderFixer(db_path)
    entity_rows = fixer.list_all_sensors()
    entity_ids = [row["entity_id"] for row in entity_rows]
    return fixer, entity_ids

def change_debug_password():
    print("Change password for user 'debug':")
    while True:
        pwd1 = getpass.getpass("Enter new password: ")
        pwd2 = getpass.getpass("Confirm new password: ")
        if pwd1 != pwd2:
            print("Passwords do not match. Please try again.")
        elif pwd1 == "":
            print("Password cannot be empty. Please try again.")
        else:
            break
    try:
        # Pass the password to chpasswd via stdin
        proc = subprocess.run(
            ["chpasswd"],
            input=f"debug:{pwd1}",
            encoding="utf-8",
            check=True,
            capture_output=True,
        )
        print("Password successfully changed for user 'debug'.")
    except subprocess.CalledProcessError as e:
        print("Failed to change password:")
        if e.stderr:
            print(e.stderr)
        else:
            print(str(e))

def main():
    warning = """
===  IMPORTANT NOTICE ===
BEFORE YOU USE THIS TOOL:
MAKE SURE TO BACKUP YOUR HOME ASSISTANT DATABASE USING STANDARD BACKUP METHODS!
THIS TOOL DOES NOT PROVIDE BACKUP OR RESTORE FUNCTIONALITY AND IS NOT RESPONSIBLE FOR DATA LOSS.

Type 'agree' and press Enter to continue, or 'exit' to quit.
"""

    while True:
        print(warning)
        consent = input("Your choice: ").strip().lower()
        if consent == "agree":
            break  # let's move on to CLI
        elif consent == "exit":
            print("Exit requested by user.")
            return  # end the program
        else:
            print("Invalid input. Please type 'agree' to continue or 'exit' to quit.\n")

    print("\nEntering CLI mode. Type 'help' to see commands.\n")

    db_path = input(f"Enter path to HA database or press ENTER key for confirm default [{DEFAULT_DB_PATH}]: ").strip()
    if not db_path:
        db_path = DEFAULT_DB_PATH

    if not os.path.isfile(db_path):
        print(f"Database file not found: {db_path}")
        return

    fixer, entity_ids = initialize_fixer(db_path)
    session = PromptSession(completer=build_completer(entity_ids))

    def print_help_forced():
        print_help()

    try:
        print_help_forced()
        while True:
            try:
                cmd_line = session.prompt("fixer> ").strip()
                if not cmd_line:
                    continue

                parts = cmd_line.split()
                cmd = parts[0]

                if cmd == "exit":
                    break

                elif cmd == "help":
                    print_help_forced()
                    continue

                elif cmd == "clear":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print_help_forced()
                    continue

                elif cmd == "password":  
                    change_debug_password()
                    print_help_forced()
                    continue

                elif cmd == "sensor":
                    if len(parts) < 2:
                        print("Sensor command requires subcommand. Type 'help' for usage.")
                        print_help_forced()
                        continue
                    subcmd = parts[1]

                    if subcmd == "list_all":
                        sensors = fixer.list_all_sensors()
                        if not sensors:
                            print("No sensors found.")
                        else:
                            for s in sensors:
                                print(f"  {s['entity_id']} → {s['metadata_id']}")
                        print_help_forced()
                        continue

                    elif len(parts) < 3:
                        print(f"Usage error: sensor {subcmd} requires <entity_id>")
                        print_help_forced()
                        continue

                    entity_id = parts[2]
                    if entity_id not in entity_ids:
                        print(f"Sensor '{entity_id}' not found.")
                        print_help_forced()
                        continue

                    elif subcmd == "delete":
                        if len(parts) != 4:
                            print("Usage: sensor delete <entity_id> <value>")
                            print_help_forced()
                            continue
                        value = parts[3]
                        
                        count = fixer.delete_state_everywhere(entity_id, value)
                        print(f"Deleted {count} record(s) for state = '{value}' in all tables (including mini graphs).")
                        print_help_forced()

                    elif subcmd == "values":
                        values = fixer.get_unique_values(entity_id)
                        if not values:
                            print(f"No values found for sensor '{entity_id}'.")
                        else:
                            for v in values:
                                print(f"  {v}")
                        print_help_forced()

                    elif subcmd == "raw":
                        rows = fixer.get_raw_states(entity_id)
                        if not rows:
                            print(f"No data for sensor '{entity_id}'.")
                        else:
                            for row in rows:
                                print(f"  {row['last_updated']} → {row['state']} (id: {row['state_id']})")
                        print_help_forced()

                    elif subcmd == "find":
                        metadata_id = fixer.get_metadata_id(entity_id)
                        if metadata_id is None:
                            print(f"Sensor '{entity_id}' not found.")
                        else:
                            print(f"metadata_id for '{entity_id}' is {metadata_id}")
                            states = fixer.list_states_by_id(metadata_id)
                            for s in states[:5]:
                                print(f"  {s['last_updated']} → {s['state']} (id: {s['state_id']})")
                        print_help_forced()

                    else:
                        print(f"Unknown sensor command: {subcmd}")
                        print_help_forced()

                else:
                    print(f"Unknown command: {cmd}. Type 'help' for commands.")
                    print_help_forced()

            except KeyboardInterrupt:
                print("\nType 'exit' to quit.")
            except EOFError:
                print("\nExit.")
                break
            except Exception as e:
                print("Error during command execution:")
                print(str(e))
                print(traceback.format_exc())
                print_help_forced()

    finally:
        fixer.close()


if __name__ == "__main__":
    main()
