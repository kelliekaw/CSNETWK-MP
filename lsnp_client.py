import protocol
from network import NetworkHandler
from logger import Logger
import time
import argparse
import threading
from collections import defaultdict
import socket   
from shared import print_safe 
from tictactoe import TicTacToe

# --- Data Structures ---
online_peers = {}
message_history = defaultdict(list) # Stores posts and DMs
post_history = defaultdict(list)
followers = set()
following = set()
liked_posts = {}
issued_tokens = set()
revoked_tokens = set()
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
active_games = {}
active_game_ids = set()
pending_acks = {}
ACK_TIMEOUT = 2  # seconds
MAX_RETRIES = 3

shutdown_event = threading.Event() # For exiting
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

def check_pending_acks(network_handler, logger):
    now = time.time()
    for msg_id, info in list(pending_acks.items()):
        if now - info["timestamp"] > ACK_TIMEOUT:
            if info["retries"] < MAX_RETRIES:
                print_safe(f"Retrying invite for msg_id={msg_id}...")
                network_handler.unicast(protocol.serialize_message(info["data"]), info["target_ip"])
                logger.log(info["data"], origin=f"Retry sent to {info['target_ip']}")
                info["timestamp"] = now
                info["retries"] += 1
            else:
                print_safe(f"Failed to get ACK for {msg_id} after {MAX_RETRIES} retries.")
                del pending_acks[msg_id]

def handle_ack(message):
    msg_id = message.get("MESSAGE_ID")
    if msg_id in pending_acks:
        print_safe(f"ACK received for message_id={msg_id}.")
        ack_info = pending_acks.pop(msg_id) 
        msg = ack_info["data"]
        msg_type = msg.get("TYPE")
        game_id = msg.get("GAMEID")
        
        if not game_id:
            return
        if game_id not in active_games:
            print_safe(f"ACK {msg_id} received, but game {game_id} is not active.")
            return
        game = active_games[game_id]
        print_safe(f"ACK received for game {game_id}")
        handle_move(game_id)
    else:
        print_safe(f"Unexpected or duplicate ACK for {msg_id}")

def generate_game_id():
    for i in range(256):
        if i not in active_game_ids:
            active_game_ids.add(i)
            return i
    raise RuntimeError("No available game IDs!")

def handle_invite(message, network_handler, logger):
    from_user = message["FROM"]
    to_user = message["TO"]
    game_id = message["GAMEID"]
    symbol = message["SYMBOL"]
    message_id = message["MESSAGE_ID"]
    choice = input("Accept? (y/n): ").strip().lower()
    if choice != "y":
        print_safe("Invite declined.")
        return

    send_ack(message_id, from_user, network_handler, logger)
    # Create game and assign symbols
    game = TicTacToe()
    game.assign_symbols(symbol, "O")
    game.player_symbol = "O"
    game.opponent_symbol = "X"
    game.player_id = to_user
    game.opponent_id = from_user
    active_games[game_id] = game

    print_safe("Game started!")
    handle_move(game_id, network_handler, logger)

def send_ack(message_id, to_user, network_handler, logger):
    ack = protocol.create_ack_message(message_id)
    target_ip = to_user.split('@')[1]
    network_handler.unicast(protocol.serialize_message(ack), target_ip)
    logger.log(ack, origin=f"Sent to {target_ip}")

def invite_player(user_id, to_user_id, network_handler, logger):
    game_id = generate_game_id()

    game = TicTacToe()
    game.assign_symbols("X")
    game.player_symbol = "X"
    game.opponent_symbol = "O"
    game.player_id = user_id
    game.opponent_id = to_user_id
    active_games[game_id] = game

    msg = protocol.create_ttt_invite_message(
        from_user_id=user_id,
        to_user_id=to_user_id,
        game_id=game_id,
        symbol="X"
    )
    message_id = msg.get("MESSAGE_ID")
    target_ip = to_user_id.split('@')[1]
    network_handler.unicast(protocol.serialize_message(msg), target_ip)
    logger.log(msg, origin=f"Sent to {target_ip}")

    pending_acks[message_id] = {
        "timestamp": time.time(),
        "retries": 0,
        "data": msg,
        "target_ip": target_ip
    }

def handle_move(game_id, network_handler, logger):
    game = active_games[game_id]
    symbol = game.player_symbol
    turn = game.turn_number
    print_safe(game.display_board())
    
    while True:
        try:
            move = int(input("Enter position (0-8)"))
            if move < 0 or move >= 9:
                print_safe("Invalid position. Choose 0-8.")
                continue
            if not game.make_move(move, game.player_symbol):
                print_safe("Position already taken. Try again.")
            break
        except ValueError:
            print_safe("Please enter a valid number")
        
    print_safe(game.display_board())

    msg = protocol.create_ttt_move_message(
        from_user_id=game.player_id,
        to_user_id=game.opponent_id,
        game_id=game_id,
        position=move,
        symbol=symbol,
        turn=turn
    )    
    target_ip = game.opponent_id.split("@")[1]
    network_handler.unicast(protocol.serialize_message(msg), target_ip)
    logger.log(msg, origin=f"Sent to {target_ip}")
    pending_acks[msg["MESSAGE_ID"]] = {
        "timestamp": time.time(),
        "retries": 0,
        "data": msg,
        "target_ip": target_ip
    }
    print_safe(f"Move sent to {game.opponent_id}")



def play_game(game_id, is_my_turn=False):
    game = active_games[game_id]

    while True:
        if is_my_turn:
            move = int(input("Enter position (0-8): "))
            if game.make_move(move, game.player_symbol):
                print_safe(game.display_board())
                is_my_turn = False
            else:
                print_safe("Invalid move. Try again.")
        else:
            print_safe("Waiting for opponent's move...")
            # Here you’d wait for a MOVE message from opponent
            is_my_turn = True

        winner = game.check_winner()
        if winner:
            print_safe(f"Game Over! Winner: {winner}")
            break


def print_menu():
    print_safe("\n--- LSNP Client Menu ---")
    print_safe("[1] Posts") # view, create, like, unlike
    print_safe("[2] DMs") # view, send
    print_safe("[3] Peers") # view, follow, unfollow
    print_safe("[4] Play TicTacToe")
    print_safe("[4] Exit")

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
    print_safe("[2] Follow")
    print_safe("[3] Unfollow")
    print_safe("[4] Back")
    
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
                                    print_safe(f"- {peer_info.get('DISPLAY_NAME', 'Unknown')} ({peer_id})")
                            else:
                                print_safe("No other peers detected.")

                        case "2":
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

                        case "3":
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
                        
                        case "4":
                            break

                        case _:
                            print_safe("Invalid choice")
                            continue
                case "4":
                    target_user_id = input("Invite (user_id) to play tic-tac-toe: ").strip()
                    if target_user_id not in online_peers:
                        print_safe(f"Error: Peer '{target_user_id}' not found.")
                        continue

                    invite_player(user_id, target_user_id, network_handler, logger)
                case "5":
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
            
            elif msg_type == protocol.MessageType.POST:
                from_user_id = message.get('USER_ID')
                if from_user_id in following:
                    post_history[from_user_id].append(message)

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

            elif msg_type == protocol.MessageType.TICTACTOE_INVITE:
                handle_invite(message, network_handler, logger)
            elif msg_type == protocol.MessageType.TICTACTOE_MOVE:
                handle_move(message, network_handler, logger)
            elif msg_type == protocol.MessageType.TICTACTOE_RESULT:
                print_safe(f"Game over. Result: {message['RESULT']}")
                if message["GAMEID"] in active_games:
                    del active_games[message["GAMEID"]]
            elif msg_type == protocol.MessageType.ACK:
                handle_ack(message, network_handler, logger)



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