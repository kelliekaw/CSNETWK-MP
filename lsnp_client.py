import secrets
import protocol
from network import NetworkHandler
from logger import Logger
import time
import argparse
import threading
from collections import defaultdict
import math
import base64
import socket
import os   
from shared import print_safe 

# --- Data Structures ---
online_peers = {}
message_history = defaultdict(list) # Stores posts and DMs
followers = set()
following = set()
incoming_files = {}
pending_file_offers = {}
sent_file_offers = {}
retry_counts = {}
pending_chunks = {}


shutdown_event = threading.Event() # For exiting




def send_file_offer_with_retry(network_handler, user_id, logger, target_user_id, filepath, filename, filesize, filetype, fileid, description):
    file_offer_message = protocol.create_file_offer_message(user_id, target_user_id, filename, filesize, filetype, fileid, description)
    message_id = file_offer_message['MESSAGE_ID']
    sent_file_offers[message_id] = {
        'filepath': filepath,
        'target_user_id': target_user_id,
        'fileid': fileid,
        'filesize': filesize
    }
    target_ip = target_user_id.split('@')[1]
    
    for i in range(3):
        network_handler.unicast(protocol.serialize_message(file_offer_message), target_ip)
        logger.log(file_offer_message, origin=f"Sent to {target_ip} (attempt {i+1})")
        time.sleep(10) # Wait for 10 seconds for an ACK
        if message_id not in sent_file_offers: # ACK received
            return
    
    if message_id in sent_file_offers:
        print_safe(f"\n> No response for file offer {message_id}. Giving up.")
        del sent_file_offers[message_id]

def send_chunk_with_retry(network_handler, user_id, logger, target_user_id, fileid, i, total_chunks, chunk_data):
    encoded_chunk = base64.b64encode(chunk_data).decode('utf-8')
    chunk_message = protocol.create_file_chunk_message(user_id, target_user_id, fileid, i, total_chunks, len(encoded_chunk), encoded_chunk)
    message_id = chunk_message['MESSAGE_ID']
    pending_chunks[message_id] = chunk_message
    target_ip = target_user_id.split('@')[1]

    for _ in range(3):
        network_handler.unicast(protocol.serialize_message(chunk_message), target_ip)
        logger.log(chunk_message, origin=f"Sent to {target_ip} (chunk {i+1}/{total_chunks})")
        time.sleep(1) # Wait for 1 second for an ACK
        if message_id not in pending_chunks: # ACK received
            return

    if message_id in pending_chunks:
        print_safe(f"\n> No response for chunk {i+1}. Giving up.")
        del pending_chunks[message_id]


def broadcast_profile(network_handler, profile_message, logger):
    """Periodically broadcasts the user's profile."""
    while not shutdown_event.is_set():
        serialized_message = protocol.serialize_message(profile_message)
        network_handler.broadcast(serialized_message)
        logger.log(profile_message, origin="Broadcast")
        time.sleep(300) # Broadcast every 5 minutes as per spec

# Broadcast ping every 5 minutes
def broadcast_ping(network_handler, user_id, logger):
    while not shutdown_event.is_set():
        ping_message = protocol.create_ping_message(user_id)
        network_handler.broadcast(protocol.serialize_message(ping_message))
        logger.log(ping_message, origin="Broadcast")
        time.sleep(300)


def print_menu():
    print_safe("\n--- LSNP Client Menu ---")
    print_safe("[1] Post")
    print_safe("[2] DM")
    print_safe("[3] Show Peers")
    print_safe("[4] View Messages by Peer")
    print_safe("[5] Follow")
    print_safe("[6] Unfollow")
    print_safe("[7] Send File")
    print_safe("[8] Accept File Offer")
    print_safe("[9] Exit")

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
                    target_user_id = input("Follow user (user_id): ").strip()
                    if target_user_id not in online_peers:
                        print_safe(f"Error: Peer '{target_user_id}' not found.")
                        continue
                    follow_message = protocol.create_follow_message(user_id, target_user_id)
                    target_ip = target_user_id.split('@')[1]
                    network_handler.unicast(protocol.serialize_message(follow_message), target_ip)
                    logger.log(follow_message, origin=f"Sent to {target_ip}")
                    following.add(target_user_id)

                case "6":
                    target_user_id = input("Unfollow user (user_id): ").strip()
                    if target_user_id not in following:
                        print_safe(f"Error: You are not following '{target_user_id}'.")
                        continue
                    unfollow_message = protocol.create_unfollow_message(user_id, target_user_id)
                    target_ip = target_user_id.split('@')[1]
                    network_handler.unicast(protocol.serialize_message(unfollow_message), target_ip)
                    logger.log(unfollow_message, origin=f"Sent to {target_ip}")
                    following.remove(target_user_id)

                case "7":
                    target_user_id = input("Send to (user_id): ").strip()
                    if target_user_id not in online_peers:
                        print_safe(f"Error: Peer '{target_user_id}' not found.")
                        continue
                    filepath = input("Filepath: ").strip()
                    if not os.path.exists(filepath):
                        print_safe(f"Error: File '{filepath}' not found.")
                        continue
                    filename = os.path.basename(filepath)
                    filesize = os.path.getsize(filepath)
                    filetype = filename.split('.')[-1]
                    fileid = secrets.token_hex(8)
                    description = input("Description: ").strip()
                    # Send file offer in a new thread to handle retries
                    offer_thread = threading.Thread(target=send_file_offer_with_retry, args=(network_handler, user_id, logger, target_user_id, filepath, filename, filesize, filetype, fileid, description), daemon=True)
                    offer_thread.start()

                case "8":
                    fileid = input("Enter the File ID of the offer you want to accept: ").strip()
                    if fileid in pending_file_offers:
                        offer = pending_file_offers[fileid]
                        ack_message = protocol.create_ack_message(offer['message_id'], "ACCEPTED")
                        target_ip = offer['from'].split('@')[1]
                        network_handler.unicast(protocol.serialize_message(ack_message), target_ip)
                        logger.log(ack_message, origin=f"Sent to {target_ip}")
                        incoming_files[fileid] = {
                            'filename': offer['filename'],
                            'filesize': offer['filesize'],
                            'received_chunks': {},
                            'from': offer['from']
                        }
                        del pending_file_offers[fileid]
                    else:
                        print_safe("Invalid File ID.")

                case "9":
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
    display_name = input("Display Name (optional): ").strip() or ""
    status = input("Status: ").strip()
    ip = get_own_ip()
    user_id = f"{username}@{ip}"

    logger = Logger(verbose=args.verbose, user_id=user_id)
    logger.following = following  
    network_handler = NetworkHandler()

    # Create profile message
    profile_message = protocol.create_profile_message(user_id, display_name, status)
    
    # Start broadcasting in a separate thread
    broadcast_thread = threading.Thread(target=broadcast_profile, args=(network_handler, profile_message, logger), daemon=True)
    broadcast_thread.start()

    # Send initial PING to discover other clients
    ping_message = protocol.create_ping_message(user_id)
    network_handler.broadcast(protocol.serialize_message(ping_message))
    logger.log(ping_message, origin="Sent")

    # Start broadcasting ping
    discovery_thread = threading.Thread(target=broadcast_ping, args=(network_handler, user_id, logger), daemon=True)
    discovery_thread.start()

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
                from_user_id = message.get('USER_ID')
                if from_user_id and from_user_id not in online_peers:
                    online_peers[from_user_id] = message
                    network_handler.broadcast(protocol.serialize_message(profile_message))

            
            elif msg_type == protocol.MessageType.PROFILE:
                from_user_id = message.get('USER_ID')
                if from_user_id and from_user_id not in online_peers:
                    online_peers[from_user_id] = message
                    network_handler.broadcast(protocol.serialize_message(profile_message))
            
            elif msg_type == protocol.MessageType.POST:
                from_user_id = message.get('USER_ID')
                if from_user_id in following:
                    message_history[from_user_id].append(message)

            elif msg_type == protocol.MessageType.DM:
                from_user_id = message.get('FROM')
                to_user_id = message.get('TO')
                if to_user_id == user_id:
                    message_history[from_user_id].append(message)
            
            elif msg_type == protocol.MessageType.FOLLOW:
                from_user_id = message.get('FROM')
                followers.add(from_user_id)
                # print_safe(f"\n> {from_user_id} has followed you.")

            elif msg_type == protocol.MessageType.UNFOLLOW:
                from_user_id = message.get('FROM')
                if from_user_id in followers:
                    followers.remove(from_user_id)
                    # print_safe(f"\n> {from_user_id} has unfollowed you.")

            elif msg_type == protocol.MessageType.ACK:
                message_id = message.get('MESSAGE_ID')
                status = message.get('STATUS')
                if message_id in sent_file_offers:
                    if status == 'ACCEPTED':
                        offer = sent_file_offers[message_id]
                        filepath = offer['filepath']
                        target_user_id = offer['target_user_id']
                        fileid = offer['fileid']
                        filesize = offer['filesize']
                        
                        # Read file and send chunks
                        chunk_size = 1024 # 1KB chunks
                        total_chunks = math.ceil(filesize / chunk_size)
                        with open(filepath, 'rb') as f:
                            for i in range(total_chunks):
                                chunk_data = f.read(chunk_size)
                                send_chunk_with_retry(network_handler, user_id, logger, target_user_id, fileid, i, total_chunks, chunk_data)
                        del sent_file_offers[message_id]
                    elif status == 'REJECTED':
                        print_safe(f"\n> File offer {message_id} was rejected.")
                        del sent_file_offers[message_id]
                elif message_id in pending_chunks:
                    del pending_chunks[message_id]

            elif msg_type == protocol.MessageType.FILE_OFFER:
                from_user_id = message.get('FROM')
                fileid = message.get('FILEID')
                filename = message.get('FILENAME')
                filesize = int(message.get('FILESIZE'))
                message_id = message.get('MESSAGE_ID')
                print_safe(f"\n> User {from_user_id} wants to send you a file: {filename} ({filesize} bytes). File ID: {fileid}")
                pending_file_offers[fileid] = {
                    'filename': filename,
                    'filesize': filesize,
                    'from': from_user_id,
                    'message_id': message_id
                }

            elif msg_type == protocol.MessageType.FILE_CHUNK:
                fileid = message.get('FILEID')
                if fileid in incoming_files:
                    chunk_index = int(message.get('CHUNK_INDEX'))
                    total_chunks = int(message.get('TOTAL_CHUNKS'))
                    data = base64.b64decode(message.get('DATA'))
                    message_id = message.get('MESSAGE_ID')
                    incoming_files[fileid]['received_chunks'][chunk_index] = data

                    # Send ACK for the chunk
                    ack_message = protocol.create_ack_message(message_id, "RECEIVED")
                    target_ip = incoming_files[fileid]['from'].split('@')[1]
                    network_handler.unicast(protocol.serialize_message(ack_message), target_ip)
                    logger.log(ack_message, origin=f"Sent to {target_ip}")

                    if len(incoming_files[fileid]['received_chunks']) == total_chunks:
                        # Reassemble file
                        filename = incoming_files[fileid]['filename']
                        with open(filename, 'wb') as f:
                            for i in range(total_chunks):
                                f.write(incoming_files[fileid]['received_chunks'][i])
                        print_safe(f"\n> File '{filename}' received successfully.")
                        
                        # Send FILE_RECEIVED message
                        file_received_message = protocol.create_file_received_message(user_id, incoming_files[fileid]['from'], fileid, "COMPLETE")
                        target_ip = incoming_files[fileid]['from'].split('@')[1]
                        network_handler.unicast(protocol.serialize_message(file_received_message), target_ip)
                        logger.log(file_received_message, origin=f"Sent to {target_ip}")

                        del incoming_files[fileid]

            elif msg_type == protocol.MessageType.FILE_RECEIVED:
                fileid = message.get('FILEID')
                status = message.get('STATUS')
                if status == "COMPLETE":
                    print_safe(f"\n> File with ID '{fileid}' was successfully received.")


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