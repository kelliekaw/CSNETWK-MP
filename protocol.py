# Defines the LSNP message formats and provides functions for creating and parsing messages.
import time
import secrets

SCOPES = {"chat", "file", "broadcast", "follow", "game", "group"}

class MessageType:
    # Milestone 2 Required Types
    PROFILE = "PROFILE"
    POST = "POST"
    DM = "DM"
    PING = "PING"
    ACK = "ACK"
    FOLLOW = "FOLLOW"
    UNFOLLOW = "UNFOLLOW"
    
    # Milestone 3 Required Types
    FILE_OFFER = "FILE_OFFER"
    FILE_CHUNK = "FILE_CHUNK"
    FILE_RECEIVED = "FILE_RECEIVED"
    REVOKE = "REVOKE"
    
    TICTACTOE_INVITE = "TICTACTOE_INVITE"
    TICTACTOE_MOVE = "TICTACTOE_MOVE"
    TICTACTOE_RESULT = "TICTACTOE_RESULT"
    LIKE = "LIKE"

    GROUP_CREATE = "GROUP_CREATE"
    GROUP_UPDATE = "GROUP_UPDATE"
    GROUP_MESSAGE = "GROUP_MESSAGE"


def create_profile_message(user_id, display_name, status, avatar_type=None, avatar_encoding=None, avatar_data=None):
    """Creates a PROFILE message dictionary."""
    message = {
        "TYPE": MessageType.PROFILE,
        "USER_ID": user_id,
        "DISPLAY_NAME": display_name if display_name else "",
        "STATUS": status
    }
    if avatar_type and avatar_encoding and avatar_data:
        message["AVATAR_TYPE"] = avatar_type
        message["AVATAR_ENCODING"] = avatar_encoding
        message["AVATAR_DATA"] = avatar_data
    return message

def create_ping_message(user_id):
    """Creates a PING message dictionary."""
    return {
        "TYPE": MessageType.PING,
        "USER_ID": user_id
    }

def create_token(user_id, scope, ttl=3600):
    """Creates a token for a given scope."""
    expiration = int(time.time()) + ttl
    return f"{user_id}|{expiration}|{scope}"

def validate_token(token, expected_scope, sender_user_id=None, revoked_tokens=None):
    if not token:
        return False
    
    if revoked_tokens and token in revoked_tokens:
        return False
    
    parts = token.split('|')
    if len(parts) != 3:
        return False
    
    user_id, expiration, scope = parts

    # if user id and sender are same
    if sender_user_id and user_id != sender_user_id:
        return False
    
    # validate expiration timestamp
    try:
        exp = int(expiration)
    except ValueError:
        return False
    
    current_time = int(time.time())
    if exp < current_time:
        return False
    
    # validate scope
    if scope != expected_scope or scope not in SCOPES:
        return False
    
    return True

def create_revoke_message(user_id, token):
    return {
        "TYPE": MessageType.REVOKE,
        "TOKEN": token
    }

def create_post_message(user_id, content, ttl=3600):
    """Creates a POST message dictionary."""
    return {
        "TYPE": MessageType.POST,
        "USER_ID": user_id,
        "CONTENT": content,
        "TTL": ttl,
        "MESSAGE_ID": secrets.token_hex(8),
        "TOKEN": create_token(user_id, "broadcast", ttl),
        "TIMESTAMP": int(time.time())
    }

def create_dm_message(from_user_id, to_user_id, content):
    """Creates a DM message dictionary."""
    return {
        "TYPE": MessageType.DM,
        "FROM": from_user_id,
        "TO": to_user_id,
        "CONTENT": content,
        "TIMESTAMP": int(time.time()),
        "MESSAGE_ID": secrets.token_hex(8),
        "TOKEN": create_token(from_user_id, "chat")
    }

def create_follow_message(from_user_id, to_user_id):
    """Creates a FOLLOW message dictionary."""
    return {
        "TYPE": MessageType.FOLLOW,
        "FROM": from_user_id,
        "TO": to_user_id,
        "TIMESTAMP": int(time.time()),
        "MESSAGE_ID": secrets.token_hex(8),
        "TOKEN": create_token(from_user_id, "follow")
    }

def create_unfollow_message(from_user_id, to_user_id):
    """Creates an UNFOLLOW message dictionary."""
    return {
        "TYPE": MessageType.UNFOLLOW,
        "FROM": from_user_id,
        "TO": to_user_id,
        "TIMESTAMP": int(time.time()),
        "MESSAGE_ID": secrets.token_hex(8),
        "TOKEN": create_token(from_user_id, "follow")
    }

def create_ack_message(message_id, status):
    """Creates an ACK message dictionary."""
    return {
        "TYPE": MessageType.ACK,
        "MESSAGE_ID": message_id,
        "STATUS": status
    }

def create_file_offer_message(from_user_id, to_user_id, filename, filesize, filetype, fileid, description):
    """Creates a FILE_OFFER message dictionary."""
    return {
        "TYPE": MessageType.FILE_OFFER,
        "FROM": from_user_id,
        "TO": to_user_id,
        "FILENAME": filename,
        "FILESIZE": filesize,
        "FILETYPE": filetype,
        "FILEID": fileid,
        "DESCRIPTION": description,
        "TIMESTAMP": int(time.time()),
        "MESSAGE_ID": secrets.token_hex(8),
        "TOKEN": create_token(from_user_id, "file")
    }

def create_file_chunk_message(from_user_id, to_user_id, fileid, chunk_index, total_chunks, chunk_size, data):
    """Creates a FILE_CHUNK message dictionary."""
    return {
        "TYPE": MessageType.FILE_CHUNK,
        "FROM": from_user_id,
        "TO": to_user_id,
        "FILEID": fileid,
        "CHUNK_INDEX": chunk_index,
        "TOTAL_CHUNKS": total_chunks,
        "CHUNK_SIZE": chunk_size,
        "DATA": data,
        "MESSAGE_ID": secrets.token_hex(8),
        "TOKEN": create_token(from_user_id, "file")
    }

def create_file_received_message(from_user_id, to_user_id, fileid, status):
    """Creates a FILE_RECEIVED message dictionary."""
    return {
        "TYPE": MessageType.FILE_RECEIVED,
        "FROM": from_user_id,
        "TO": to_user_id,
        "FILEID": fileid,
        "STATUS": status,
        "TIMESTAMP": int(time.time())
    }

def create_like_message(from_user_id, to_user_id, post_timestamp, action="LIKE"):
    return {
        "TYPE": MessageType.LIKE,
        "FROM": from_user_id,
        "TO": to_user_id,
        "POST_TIMESTAMP": post_timestamp,
        "ACTION": action,
        "TIMESTAMP": int(time.time()),
        "TOKEN": create_token(from_user_id, "broadcast")
    }

def create_group_create(from_user, group_name, members):
    ts = int(time.time())
    return {
        "TYPE": MessageType.GROUP_CREATE,
        "FROM": from_user,
        "GROUP_ID": f"{group_name.replace(' ', '').lower()}{ts}",
        "GROUP_NAME": group_name,
        "MEMBERS": ",".join(members),
        "TIMESTAMP": ts,
        "TOKEN": create_token(from_user, "group")
    }

def create_group_update(from_user, group_id, add=None, remove=None):
    msg = {
        "TYPE": "GROUP_UPDATE",
        "FROM": from_user,
        "GROUP_ID": group_id,
        "TIMESTAMP": int(time.time()),
        "TOKEN": create_token(from_user, "group")
    }
    if add: msg["ADD"] = ",".join(add)
    if remove: msg["REMOVE"] = ",".join(remove)
    return msg

def create_group_message(from_user, group_id, content):
    return {
        "TYPE": "GROUP_MESSAGE",
        "FROM": from_user,
        "GROUP_ID": group_id,
        "CONTENT": content,
        "TIMESTAMP": int(time.time()),
        "TOKEN": create_token(from_user, "group")
    }

def serialize_message(message_dict):
    """Converts a message dictionary into a string for transmission."""
    lines = [f"{key}:{value}" for key, value in message_dict.items()]
    return "\n".join(lines) + "\n\n"

def parse_message(message_str):
    """Parses an LSNP message string into a dictionary."""
    message = {}
    lines = message_str.strip().split('\n')
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            message[key] = value
    return message
