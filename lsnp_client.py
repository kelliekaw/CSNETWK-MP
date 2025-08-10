import protocol
from network import NetworkHandler
from logger import Logger
import time
import argparse
import threading
from collections import defaultdict
import socket   
from shared import print_safe 

# --- Data Structures ---
online_peers = {}
message_history = defaultdict(list) # Stores posts and DMs


shutdown_event = threading.Event() # For exiting
def broadcast_profile(network_handler, profile_message, logger):
    """Periodically broadcasts the user's profile."""
    while not shutdown_event.is_set():
        serialized_message = protocol.serialize_message(profile_message)
        network_handler.broadcast(serialized_message)
        logger.log(profile_message, origin="Broadcast")
        time.sleep(300) # Broadcast every 5 minutes as per spec

def print_menu():
    print_safe("\n--- LSNP Client Menu ---")
    print_safe("[1] Post")
    print_safe("[2] DM")
    print_safe("[3] Show Peers")
    print_safe("[4] View Messages by Peer")
    print_safe("[5] Exit")

def handle_user_input(network_handler, user_id, logger):
    """Handles commands typed by the user."""
    # print_safe("\nType 'post <message>', 'dm <user_id> <message>', 'peers', 'view <user_id>', or 'exit'.")
    while True:
        try:
            print_menu()
            choice = input("> ").strip()
            if not choice:
                continue

            # command = parts[0].lower()
            match choice:
                case "1":
                    content = input("Enter your post: ")
                    post_message = protocol.create_post_message(user_id, content)
                    network_handler.broadcast(protocol.serialize_message(post_message))
                    logger.log(post_message, origin="Sent")

                case "2":
                    target_user_id = input("Send to (user_id): ").strip()
                    if target_user_id not in online_peers:
                        print_safe(f"Error: Peer '{target_user_id}' not found.")
                        continue
                    content = input("Message: ").strip()
                    dm_message = protocol.create_dm_message(user_id, target_user_id, content)
                    target_ip = target_user_id.split('@')[1]
                    network_handler.unicast(protocol.serialize_message(dm_message), target_ip)
                    logger.log(dm_message, origin=f"Sent to {target_ip}")
                    message_history[target_user_id].append(dm_message)

                case "3":
                    print_safe("--- Online Peers ---")
                    if online_peers:
                        for peer_id, peer_info in online_peers.items():
                            print_safe(f"- {peer_info.get('DISPLAY_NAME', 'Unknown')} ({peer_id})")
                    else:
                        print_safe("No other peers detected.")

                case "4":
                    target_user_id = input("View messages from (user_id): ").strip()
                    print_safe(f"--- Message History with {target_user_id} ---")
                    if message_history[target_user_id]:
                        for msg in message_history[target_user_id]:
                            if msg.get('TYPE') == protocol.MessageType.POST:
                                print_safe(f"[POST] {msg.get('CONTENT')}")
                            elif msg.get('TYPE') == protocol.MessageType.DM:
                                direction = "To" if msg.get('FROM') == user_id else "From"
                                print_safe(f"[DM {direction} {target_user_id}] {msg.get('CONTENT')}")
                    else:
                        print_safe(f"No messages found for {target_user_id}.")

                case "5":
                    print_safe("Exiting...")
                    shutdown_event.set()
                    break
                case _:
                    print_safe("Invalid choice")
                    continue
                    
        except (EOFError, KeyboardInterrupt):
            shutdown_event.set()
            break

def get_own_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1)) # non-routable IP in a private range (i.e. it doesn’t matter if the address exists)
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP

def main():
    parser = argparse.ArgumentParser(description='LSNP Client')
    # parser.add_argument('user_id', type=str, help='User ID for the client (e.g., alice@192.168.1.11)')
    # parser.add_argument('display_name', type=str, help='Display name for the client')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()

    
    
    # print_safe(f"LSNP Client Starting for {args.display_name} ({args.user_id})...")
    # Get inputs
    print_safe(f"LSNP Client Starting...")
    username = input("Username: ").strip()
    display_name = input("Display Name (optional): ").strip() or None
    status = input("Status: ").strip()
    ip = get_own_ip()
    user_id = f"{username}@{ip}"

    logger = Logger(verbose=args.verbose, user_id=user_id)

    network_handler = NetworkHandler()

    # Create profile message
    profile_message = protocol.create_profile_message(user_id, display_name, status)
    
    # Start broadcasting in a separate thread
    broadcast_thread = threading.Thread(target=broadcast_profile, args=(network_handler, profile_message, logger), daemon=True)
    broadcast_thread.start()

    # Send a PING to discover other clients
    ping_message = protocol.create_ping_message(user_id)
    network_handler.broadcast(protocol.serialize_message(ping_message))
    logger.log(ping_message, origin="Sent")

    time.sleep(0.5)

    # Start input handling in a separate thread
    input_thread = threading.Thread(target=handle_user_input, args=(network_handler, user_id, logger), daemon=True)
    input_thread.start()

    # print_safe("\nListening for messages...")
    try:
        while not shutdown_event.is_set():
            data, addr = network_handler.receive()
            if data is None:
                continue

            message = protocol.parse_message(data)
            
            msg_type = message.get('TYPE')
            if not msg_type:
                continue

            # Ignore own messages
            if message.get('USER_ID') == user_id or message.get('FROM') == user_id:
                continue

            logger.log(message, origin=f"Received from {addr}")

            if msg_type == protocol.MessageType.PING:
                network_handler.broadcast(protocol.serialize_message(profile_message))
            
            elif msg_type == protocol.MessageType.PROFILE:
                from_user_id = message.get('USER_ID')
                if from_user_id and from_user_id not in online_peers:
                    online_peers[from_user_id] = message
            
            elif msg_type == protocol.MessageType.POST:
                from_user_id = message.get('USER_ID')
                message_history[from_user_id].append(message)

            elif msg_type == protocol.MessageType.DM:
                from_user_id = message.get('FROM')
                to_user_id = message.get('TO')
                if to_user_id == user_id:
                    message_history[from_user_id].append(message)

    except KeyboardInterrupt:
        print_safe("\nShutting down client.")
        shutdown_event.set()
    finally:
        print_safe("\nShutting down client.")
        network_handler.close()
        broadcast_thread.join(timeout=1)
        input_thread.join(timeout=1)

if __name__ == "__main__":
    main()