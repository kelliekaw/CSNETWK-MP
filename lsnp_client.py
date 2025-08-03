import protocol
from network import NetworkHandler
from logger import Logger
import time
import argparse
import threading
from collections import defaultdict

# --- Data Structures ---
online_peers = {}
message_history = defaultdict(list) # Stores posts and DMs

def broadcast_profile(network_handler, profile_message, logger):
    """Periodically broadcasts the user's profile."""
    while True:
        serialized_message = protocol.serialize_message(profile_message)
        network_handler.broadcast(serialized_message)
        logger.log(profile_message, origin="Broadcast")
        time.sleep(300) # Broadcast every 5 minutes as per spec

def handle_user_input(network_handler, user_id, logger):
    """Handles commands typed by the user."""
    print("\nType 'post <message>', 'dm <user_id> <message>', 'peers', 'view <user_id>', or 'exit'.")
    while True:
        try:
            command_str = input("> ")
            parts = command_str.strip().split()
            if not parts:
                continue

            command = parts[0].lower()

            if command == "exit":
                break
            elif command == "peers":
                print("--- Online Peers ---")
                if online_peers:
                    for peer_id, peer_info in online_peers.items():
                        print(f"- {peer_info.get('DISPLAY_NAME', 'Unknown')} ({peer_id})")
                else:
                    print("No other peers detected.")
            
            elif command == "post" and len(parts) > 1:
                content = " ".join(parts[1:])
                post_message = protocol.create_post_message(user_id, content)
                network_handler.broadcast(protocol.serialize_message(post_message))
                logger.log(post_message, origin="Sent")

            elif command == "dm" and len(parts) > 2:
                target_user_id = parts[1]
                content = " ".join(parts[2:])
                if target_user_id not in online_peers:
                    print(f"Error: Peer '{target_user_id}' not found.")
                    continue
                
                dm_message = protocol.create_dm_message(user_id, target_user_id, content)
                target_ip = target_user_id.split('@')[1]
                network_handler.unicast(protocol.serialize_message(dm_message), target_ip)
                logger.log(dm_message, origin=f"Sent to {target_ip}")

            elif command == "view" and len(parts) > 1:
                target_user_id = parts[1]
                print(f"--- Message History with {target_user_id} ---")
                if message_history[target_user_id]:
                    for msg in message_history[target_user_id]:
                        if msg.get('TYPE') == protocol.MessageType.POST:
                            print(f"[POST] {msg.get('CONTENT')}")
                        elif msg.get('TYPE') == protocol.MessageType.DM:
                            direction = "To" if msg.get('FROM') == user_id else "From"
                            print(f"[DM {direction} {target_user_id}] {msg.get('CONTENT')}")
                else:
                    print(f"No messages found for {target_user_id}.")

            else:
                print(f"Unknown command: '{command_str}'")

        except (EOFError, KeyboardInterrupt):
            break

def main():
    parser = argparse.ArgumentParser(description='LSNP Client')
    parser.add_argument('user_id', type=str, help='User ID for the client (e.g., alice@192.168.1.11)')
    parser.add_argument('display_name', type=str, help='Display name for the client')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()

    logger = Logger(verbose=args.verbose)

    print(f"LSNP Client Starting for {args.display_name} ({args.user_id})...")
    network_handler = NetworkHandler()

    # Create profile message
    status = "Exploring LSNP!"
    profile_message = protocol.create_profile_message(args.user_id, args.display_name, status)

    # Start broadcasting in a separate thread
    broadcast_thread = threading.Thread(target=broadcast_profile, args=(network_handler, profile_message, logger), daemon=True)
    broadcast_thread.start()
    
    # Start input handling in a separate thread
    input_thread = threading.Thread(target=handle_user_input, args=(network_handler, args.user_id, logger), daemon=True)
    input_thread.start()

    # Send a PING to discover other clients
    ping_message = protocol.create_ping_message(args.user_id)
    network_handler.broadcast(protocol.serialize_message(ping_message))
    logger.log(ping_message, origin="Sent")

    print("\nListening for messages...")
    try:
        while True:
            data, addr = network_handler.receive()
            message = protocol.parse_message(data)
            
            msg_type = message.get('TYPE')
            if not msg_type:
                continue

            # Ignore own messages
            if message.get('USER_ID') == args.user_id or message.get('FROM') == args.user_id:
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
                if to_user_id == args.user_id:
                    message_history[from_user_id].append(message)

    except KeyboardInterrupt:
        print("\nShutting down client.")
    finally:
        network_handler.close()

if __name__ == "__main__":
    main()