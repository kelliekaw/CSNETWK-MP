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
post_history = defaultdict(list)
followers = set()
following = set()
incoming_files = {}
pending_file_offers = {}
sent_file_offers = {}
retry_counts = {}
pending_chunks = {}
groups = {}
liked_posts = {}
issued_tokens = set()
revoked_tokens = set()
show_only_group_messages = False
expected_scope_map = {
    protocol.MessageType.POST: "broadcast",
    protocol.MessageType.LIKE: "broadcast",
    protocol.MessageType.DM: "chat",
    protocol.MessageType.FOLLOW: "follow",
    protocol.MessageType.UNFOLLOW: "follow",
    protocol.MessageType.FILE_OFFER: "file",
    protocol.MessageType.FILE_CHUNK: "file",
    protocol.MessageType.REVOKE: "chat",
    protocol.MessageType.GROUP_CREATE: "group",
    protocol.MessageType.GROUP_UPDATE: "group",
    protocol.MessageType.GROUP_MESSAGE: "group",
    protocol.MessageType.TICTACTOE_INVITE: "game",
    protocol.MessageType.TICTACTOE_MOVE: "game",
    protocol.MessageType.TICTACTOE_RESULT: "game"
}

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

def send_revoke_messages(network_handler, user_id, tokens):
    for token in tokens:
        revoke_message = protocol.create_revoke_message(user_id, token)
        network_handler.broadcast(protocol.serialize_message(revoke_message))

def print_menu():
    print_safe("\n--- LSNP Client Menu ---")
    print_safe("[1] Posts") # view, create, like, unlike
    print_safe("[2] DMs") # view, send
    print_safe("[3] Peers") # view, follow, unfollow
    print_safe("[4] Files")
    print_safe("[5] Groups")
    print_safe("[6] Exit")

def posts_menu():
    print_safe("\n--- Posts Menu ---")
    print_safe("[1] View Posts")
    print_safe("[2] Create Post")
    print_safe("[3] Like Post")
    print_safe("[4] Unlike Post")
    print_safe("[5] Back")

def dms_menu():
    print_safe("\n--- DMs Menu ---")
    print_safe("[1] View DMs")
    print_safe("[2] Send DM")
    print_safe("[3] Back")

def peers_menu():
    print_safe("\n--- Peers Menu ---")
    print_safe("[1] Show Peers")
    print_safe("[2] View Profile")
    print_safe("[3] Follow")
    print_safe("[4] Unfollow")
    print_safe("[5] Back")
    
def files_menu():
    print_safe("\n--- Files Menu ---")
    print_safe("[1] Send File")
    print_safe("[2] Accept File Offer")
    print_safe("[3] Back")

def groups_menu():
    print_safe("\n--- Groups Menu ---")
    print_safe("[1] Create Group")
    print_safe("[2] View Groups")
    print_safe("[3] Update Group")
    print_safe("[4] Message Group")
    print_safe("[5] Toggle Group Messages Only")

    
def display_posts(user_id):
    if post_history[user_id]:
        print_safe(f"--- Posts by {user_id} ---")
        for post in post_history[user_id]:
            print_safe(f"{user_id} [{post.get('TIMESTAMP')}]: {post.get('CONTENT')}")
    else:
        print_safe(f"No posts found by {user_id}.")

def display_liked_posts():
    if not liked_posts:
        print_safe("No liked posts.")
        return
    print_safe("--- Liked Posts ---")
    for (user_id, timestamp) in liked_posts:
        user_posts = post_history.get(user_id, [])
        # Find the post with that timestamp
        for post in user_posts:
            if post.get("TIMESTAMP") == timestamp:
                content = post.get("CONTENT")
                print_safe(f"{user_id} [{timestamp}]: {content}")
                break

def display_groups():
    if not groups:
        print_safe("No groups yet.")
        return
    print_safe("--- Groups ---")
    for group_id, group_info in groups.items():
        name = group_info.get("GROUP_NAME", "Unnamed Group")
        members = group_info.get("MEMBERS", "")
        print_safe(f"Group ID: {group_id}")
        print_safe(f"Name: {name}")
        print_safe(f"Members: {members}")
        print_safe("-" * 14)

def view_profile(user_id):
    """Display a user's profile and download their avatar if available."""
    if user_id not in online_peers:
        print_safe(f"User '{user_id}' not found in online peers.")
        return
    
    peer_info = online_peers[user_id]
    display_name = peer_info.get('DISPLAY_NAME', 'N/A')
    status = peer_info.get('STATUS', 'N/A')
    
    print_safe(f"\n--- Profile for {user_id} ---")
    print_safe(f"Display Name: {display_name}")
    print_safe(f"Status: {status}")
    
    # Check if user has an avatar
    if 'AVATAR_DATA' in peer_info and peer_info['AVATAR_DATA']:
        print_safe("User has an avatar.")
        download_avatar = input("Download avatar? (y/n): ").strip().lower()
        if download_avatar == 'y':
            download_user_avatar(user_id)
    else:
        print_safe("User has no avatar.")

def download_user_avatar(user_id):
    """Download and save a user's avatar."""
    if user_id not in online_peers:
        print_safe(f"User '{user_id}' not found.")
        return
    
    peer_info = online_peers[user_id]
    
    # Check if user has avatar data
    if 'AVATAR_DATA' not in peer_info or not peer_info['AVATAR_DATA']:
        print_safe(f"User '{user_id}' has no avatar to download.")
        return
    
    avatar_data = peer_info['AVATAR_DATA']
    avatar_type = peer_info.get('AVATAR_TYPE', 'image/png')
    
    # Determine file extension based on MIME type
    if 'jpeg' in avatar_type or 'jpg' in avatar_type:
        ext = '.jpg'
    elif 'png' in avatar_type:
        ext = '.png'
    elif 'gif' in avatar_type:
        ext = '.gif'
    else:
        ext = '.png'  # Default fallback
    
    # Create filename
    filename = f"avatar_{user_id.split('@')[0]}{ext}"
    
    try:
        # Decode base64 data and save to file
        import base64
        image_data = base64.b64decode(avatar_data)
        with open(filename, 'wb') as f:
            f.write(image_data)
        print_safe(f"Avatar saved as '{filename}'")
    except Exception as e:
        print_safe(f"Error saving avatar: {e}")

def handle_user_input(network_handler, user_id, logger):
    """Handles commands typed by the user."""
    # print_safe("\nType 'post <message>', 'dm <user_id> <message>', 'peers', 'view <user_id>', or 'exit'.")
    while True:
        try:
            print_menu()
            select = input("> ").strip()
            if not select:
                continue

            match select:
                case "1":
                    posts_menu()
                    choice = input("> ").strip()
                    if not choice:
                        continue
                    match choice:
                        case "1": # view posts
                            target_user_id = input("View posts from (user_id): ").strip()
                            display_posts(target_user_id)
                        case "2": # create post
                            content = input("Enter your post: ")
                            post_message = protocol.create_post_message(user_id, content)
                            issued_tokens.add(post_message["TOKEN"])
                            network_handler.broadcast(protocol.serialize_message(post_message))
                            logger.log(post_message, origin="Sent")
                        case "3": # like
                            target_user_id = input("Like post by (user_id): ")
                            if target_user_id not in online_peers:
                                print_safe(f"Error: Peer '{target_user_id}' not found.")
                                continue
                            display_posts(target_user_id)
                            post_timestamp = input("Enter timestamp of post: ")
                            like_message = protocol.create_like_message(user_id, target_user_id, post_timestamp)
                            target_ip = target_user_id.split('@')[1]
                            network_handler.unicast(protocol.serialize_message(like_message), target_ip)
                            logger.log(like_message, origin=f"Sent to {target_ip}")
                            liked_posts[(target_user_id, post_timestamp)] = like_message

                        case "4": # unlike
                            if not liked_posts:
                                print_safe("No liked posts.")
                                continue
                            display_liked_posts()
                            target_user_id = input("Unlike post by (user_id): ").strip()
                            post_timestamp = input("Enter timestamp of post:").strip()
                            key = (target_user_id, post_timestamp)
                            if key not in liked_posts:
                                print_safe(f"Error: Post by {target_user_id} at '{target_user_id}' not found.")
                                continue
                        
                            like_message = protocol.create_like_message(user_id, target_user_id, post_timestamp, action="UNLIKE")
                            target_ip = target_user_id.split('@')[1]
                            network_handler.unicast(protocol.serialize_message(like_message), target_ip)
                            logger.log(like_message, origin=f"Sent to {target_ip}")
                            del liked_posts[key]

                        case "5": # back
                            break

                        case _:
                            print_safe("Invalid choice")
                            continue

                case "2":
                    dms_menu()
                    choice = input("> ").strip()
                    match choice:
                        case "1": # view dms
                            target_user_id = input("View messages from (user_id): ").strip()
                            print_safe(f"--- Message History with {target_user_id} ---")
                            if message_history[target_user_id]:
                                for msg in message_history[target_user_id]:
                                    direction = "To" if msg.get('FROM') == user_id else "From"
                                    print_safe(f"[DM {direction} {target_user_id}] {msg.get('CONTENT')}")
                            else:
                                print_safe(f"No messages found for {target_user_id}.")
                        case "2": # send dm
                            target_user_id = input("Send to (user_id): ").strip()
                            if target_user_id not in online_peers:
                                print_safe(f"Error: Peer '{target_user_id}' not found.")
                                continue
                            content = input("Message: ").strip()
                            dm_message = protocol.create_dm_message(user_id, target_user_id, content)
                            issued_tokens.add(dm_message["TOKEN"])
                            target_ip = target_user_id.split('@')[1]
                            network_handler.unicast(protocol.serialize_message(dm_message), target_ip)
                            logger.log(dm_message, origin=f"Sent to {target_ip}")
                            message_history[target_user_id].append(dm_message)
                        case "3": # back
                            break
                        case _:
                            print_safe("Invalid choice")
                            continue
                case "3":
                    peers_menu()
                    choice = input("> ").strip()
                    match choice:
                        case "1":
                            print_safe("--- Online Peers ---")
                            if online_peers:
                                for peer_id, peer_info in online_peers.items():
                                    has_avatar = "(has avatar)" if peer_info.get('AVATAR_DATA') else ""
                                    print_safe(f"- {peer_info.get('DISPLAY_NAME', 'Unknown')} ({peer_id}) {has_avatar}")
                            else:
                                print_safe("No other peers detected.")

                        case "2":
                            target_user_id = input("View profile of user (user_id): ").strip()
                            view_profile(target_user_id)

                        case "3":
                            target_user_id = input("Follow user (user_id): ").strip()
                            if target_user_id not in online_peers:
                                print_safe(f"Error: Peer '{target_user_id}' not found.")
                                continue
                            follow_message = protocol.create_follow_message(user_id, target_user_id)
                            issued_tokens.add(follow_message["TOKEN"])
                            target_ip = target_user_id.split('@')[1]
                            network_handler.unicast(protocol.serialize_message(follow_message), target_ip)
                            logger.log(follow_message, origin=f"Sent to {target_ip}")
                            following.add(target_user_id)

                        case "4":
                            target_user_id = input("Unfollow user (user_id): ").strip()
                            if target_user_id not in following:
                                print_safe(f"Error: You are not following '{target_user_id}'.")
                                continue
                            unfollow_message = protocol.create_unfollow_message(user_id, target_user_id)
                            issued_tokens.add(unfollow_message["TOKEN"])
                            target_ip = target_user_id.split('@')[1]
                            network_handler.unicast(protocol.serialize_message(unfollow_message), target_ip)
                            logger.log(unfollow_message, origin=f"Sent to {target_ip}")
                            following.remove(target_user_id)

                            if target_user_id in post_history:
                                del post_history[target_user_id]
                        
                        case "5":
                            break

                        case _:
                            print_safe("Invalid choice")
                            continue
                case "4":
                    files_menu()
                    choice = input("> ").strip()
                    match choice:
                        case "1":
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
                        case "2":
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
                        case "3":
                            break
                
                case "5":
                    groups_menu()
                    choice = input("> ").strip()
                    match choice:
                        case "1":
                            group_name = input("Enter group name: ").strip()
                            members = set()
                            print_safe("Enter members' user IDs one by one. Type 'done' when finished.")
                            while True:
                                member = input("Member user_id: ").strip()
                                if member.lower() == 'done':
                                    break
                                if member == user_id:
                                    print_safe("You are automatically included as a member.")
                                    continue
                                if member in online_peers:
                                    members.add(member)
                                else:
                                    print_safe(f"User '{member}' not found in online peers. Please try again.")
                            # Make sure creator is included
                            members.add(user_id)

                            group_create_msg = protocol.create_group_create(user_id, group_name, members=list(members))
                            target_ips = [m.split('@')[1] for m in members]
                            for ip in target_ips:
                                network_handler.unicast(protocol.serialize_message(group_create_msg), ip)
                            
                            logger.log(group_create_msg)
                            groups[group_create_msg["GROUP_ID"]] = group_create_msg


                        case "2":
                            display_groups()

                        case "3":
                            group_id = input("Enter group id to update: ").strip()
                            if group_id not in groups:
                                print_safe("Group not found.")
                                continue
                            group_info = groups[group_id]
                            if user_id != group_info.get('FROM'):
                                print_safe("You do not have permission to update this group.")
                                continue
                            members_str = group_info.get('MEMBERS', '')
                            print_safe(f"Current members: {members_str}")

                            add_members = input("Enter members to add (comma-separated), or leave blank: ").strip()
                            remove_members = input("Enter members to remove (comma-separated), or leave blank: ").strip()

                            to_add = set()
                            to_remove = set()

                            current_members = set(m.strip() for m in members_str.split(",") if m.strip())

                            if add_members:
                                to_add = set(m.strip() for m in add_members.split(",") if m.strip())
                                current_members.update(to_add)

                            if remove_members:
                                to_remove = set(m.strip() for m in remove_members.split(",") if m.strip())
                                current_members.difference_update(to_remove)

                            # Save updated members list back
                            group_info["MEMBERS"] = ",".join(sorted(current_members))

                            group_update_msg = protocol.create_group_update(user_id, group_id, to_add, to_remove)
                            notify = current_members.union(to_remove)
                            target_ips = [m.split('@')[1] for m in notify]
                            for ip in target_ips:
                                network_handler.unicast(protocol.serialize_message(group_update_msg), ip)
                            
                            logger.log(group_update_msg)

                        case "4":
                            group_id = input("Enter group id to message: ").strip()
                            if group_id not in groups:
                                print_safe("Group not found.")
                                continue
                            group_info = groups[group_id]
                            content = input("Enter message: ").strip()
                            members_str = group_info.get("MEMBERS", "")
                            members = [m.strip() for m in members_str.split(",") if m.strip()]

                            msg = protocol.create_group_message(user_id, group_id, content)
                            target_ips = [m.split('@')[1] for m in members]
                            for ip in target_ips:
                                network_handler.unicast(protocol.serialize_message(msg), ip)

                            logger.log(msg)

                        case "5":
                            logger.show_only_group_messages = not logger.show_only_group_messages
                            status = "ON" if logger.show_only_group_messages else "OFF"
                            print_safe(f"Group Messages Only mode is now {status}")
                            continue

                case "6":
                    print_safe("Exiting...")
                    send_revoke_messages(network_handler, user_id, issued_tokens)
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
    avatar_path = input("Avatar path (optional, press Enter to skip): ").strip()
    ip = get_own_ip()
    user_id = f"{username}@{ip}"

    avatar_type = None
    avatar_encoding = None
    avatar_data = None
    if avatar_path and os.path.exists(avatar_path):
        try:
            with open(avatar_path, "rb") as f:
                avatar_data_raw = f.read()
            if len(avatar_data_raw) < 20000:
                avatar_data = base64.b64encode(avatar_data_raw).decode('utf-8')
                avatar_type = f"image/{avatar_path.split('.')[-1]}"
                avatar_encoding = "base64"
            else:
                print_safe("Avatar image is too large (must be under 20KB). Skipping.")
        except Exception as e:
            print_safe(f"Error reading avatar file: {e}. Skipping.")

    logger = Logger(verbose=args.verbose, user_id=user_id, online_peers=online_peers, groups=groups)
    logger.following = following  
    network_handler = NetworkHandler()

    # Create profile message
    profile_message = protocol.create_profile_message(user_id, display_name, status, avatar_type, avatar_encoding, avatar_data)
    
    # Start broadcasting in a separate thread
    broadcast_thread = threading.Thread(target=broadcast_profile, args=(network_handler, profile_message, logger), daemon=True)
    broadcast_thread.start()

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

            if msg_type == protocol.MessageType.REVOKE:
                revoked_token = message.get('TOKEN')
                if revoked_token:
                    revoked_tokens.add(revoked_token)
                continue

            token = message.get('TOKEN')
            sender_id = message.get('USER_ID') or message.get('FROM')
            expected_scope = expected_scope_map.get(msg_type)

            if expected_scope:
                if not protocol.validate_token(token, expected_scope, sender_id, revoked_tokens):
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
                else: # Update existing peer
                    online_peers[from_user_id].update(message)
            
            elif msg_type == protocol.MessageType.POST:
                from_user_id = message.get('USER_ID')
                if from_user_id in following:
                    post_history[from_user_id].append(message)
                # Send ACK for POST message
                message_id = message.get('MESSAGE_ID')
                if message_id:
                    ack_message = protocol.create_ack_message(message_id, "RECEIVED")
                    target_ip = from_user_id.split('@')[1]
                    network_handler.unicast(protocol.serialize_message(ack_message), target_ip)
                    logger.log(ack_message, origin=f"Sent to {target_ip}")

            elif msg_type == protocol.MessageType.DM:
                from_user_id = message.get('FROM')
                to_user_id = message.get('TO')
                if to_user_id == user_id:
                    message_history[from_user_id].append(message)
                # Send ACK for DM message
                message_id = message.get('MESSAGE_ID')
                if message_id:
                    ack_message = protocol.create_ack_message(message_id, "RECEIVED")
                    target_ip = from_user_id.split('@')[1]
                    network_handler.unicast(protocol.serialize_message(ack_message), target_ip)
                    logger.log(ack_message, origin=f"Sent to {target_ip}")
            
            elif msg_type == protocol.MessageType.FOLLOW:
                from_user_id = message.get('FROM')
                followers.add(from_user_id)
                # print_safe(f"\n> {from_user_id} has followed you.")
                # Send ACK for FOLLOW message
                message_id = message.get('MESSAGE_ID')
                if message_id:
                    ack_message = protocol.create_ack_message(message_id, "RECEIVED")
                    target_ip = from_user_id.split('@')[1]
                    network_handler.unicast(protocol.serialize_message(ack_message), target_ip)
                    logger.log(ack_message, origin=f"Sent to {target_ip}")

            elif msg_type == protocol.MessageType.UNFOLLOW:
                from_user_id = message.get('FROM')
                if from_user_id in followers:
                    followers.remove(from_user_id)
                    # print_safe(f"\n> {from_user_id} has unfollowed you.")
                # Send ACK for UNFOLLOW message
                message_id = message.get('MESSAGE_ID')
                if message_id:
                    ack_message = protocol.create_ack_message(message_id, "RECEIVED")
                    target_ip = from_user_id.split('@')[1]
                    network_handler.unicast(protocol.serialize_message(ack_message), target_ip)
                    logger.log(ack_message, origin=f"Sent to {target_ip}")

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

            elif msg_type == protocol.MessageType.GROUP_CREATE:
                group_id = message.get("GROUP_ID")
                if group_id:
                    groups[group_id] = message
                else:
                    print_safe("Received GROUP_CREATE message with no GROUP_ID")
            
            elif msg_type == protocol.MessageType.GROUP_UPDATE:
                group_id = message.get("GROUP_ID")
                if group_id:
                    group_name = groups.get(group_id, {}).get("GROUP_NAME", "Unknown Group")
                    remove_list = message.get("REMOVE", "")
                    remove_members = set(m.strip() for m in remove_list.split(",") if m.strip())
                    if user_id in remove_members:
                        if group_id in groups:
                            del groups[group_id]
                            print_safe(f"You were removed from group \"{group_name}\"")
                    groups[group_id] = message
                else:
                    print_safe("Received GROUP_UPDATE message with no GROUP_ID")

            elif msg_type == protocol.MessageType.TICTACTOE_INVITE:
                from_user_id = message.get('FROM')
                # Send ACK for TICTACTOE_INVITE message
                message_id = message.get('MESSAGE_ID')
                if message_id:
                    ack_message = protocol.create_ack_message(message_id, "RECEIVED")
                    target_ip = from_user_id.split('@')[1]
                    network_handler.unicast(protocol.serialize_message(ack_message), target_ip)
                    logger.log(ack_message, origin=f"Sent to {target_ip}")

            elif msg_type == protocol.MessageType.TICTACTOE_MOVE:
                from_user_id = message.get('FROM')
                # Send ACK for TICTACTOE_MOVE message
                message_id = message.get('MESSAGE_ID')
                if message_id:
                    ack_message = protocol.create_ack_message(message_id, "RECEIVED")
                    target_ip = from_user_id.split('@')[1]
                    network_handler.unicast(protocol.serialize_message(ack_message), target_ip)
                    logger.log(ack_message, origin=f"Sent to {target_ip}")

            elif msg_type == protocol.MessageType.TICTACTOE_RESULT:
                from_user_id = message.get('FROM')
                # Send ACK for TICTACTOE_RESULT message
                message_id = message.get('MESSAGE_ID')
                if message_id:
                    ack_message = protocol.create_ack_message(message_id, "RECEIVED")
                    target_ip = from_user_id.split('@')[1]
                    network_handler.unicast(protocol.serialize_message(ack_message), target_ip)
                    logger.log(ack_message, origin=f"Sent to {target_ip}")



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