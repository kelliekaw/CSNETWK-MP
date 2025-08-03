# Defines the LSNP message formats and provides functions for creating and parsing messages.
import time
import secrets

class MessageType:
    # Milestone 1 Required Types
    PROFILE = "PROFILE"
    POST = "POST"
    DM = "DM"
    PING = "PING"
    ACK = "ACK"

def create_profile_message(user_id, display_name, status, avatar_type=None, avatar_encoding=None, avatar_data=None):
    """Creates a PROFILE message dictionary."""
    message = {
        "TYPE": MessageType.PROFILE,
        "USER_ID": user_id,
        "DISPLAY_NAME": display_name,
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
