import protocol
from shared import print_safe
        
class Logger:
    def __init__(self, verbose=False, user_id=None, online_peers=None):
        self.verbose = verbose
        self.user_id = user_id
        self.online_peers = online_peers if online_peers is not None else {}

    def _get_display_name(self, user_id):
        # Return display name if known, else user_id (for non verbose printing)
        peer_info = self.online_peers.get(user_id)
        if peer_info:
            return peer_info.get('DISPLAY_NAME') or user_id
        return user_id
    
    def log(self, message, origin=None):
        if self.verbose:
            self._log_verbose(message, origin)
        else:
            self._log_non_verbose(message)

    def _log_verbose(self, message, origin):
        # print_safe(f"\n--- Verbose Log ---")
        # if origin:
        #     print_safe(f"Origin: {origin}")
        # for key, value in message.items():
        #     print_safe(f"  {key}: {value}")
        # print_safe("---------------------")
        lines = ["\n--- Verbose Log ---"]
        if origin:
            lines.append(f"Origin: {origin}")
        for key, value in message.items():
            lines.append(f"  {key}: {value}")
        lines.append("--------------------")
        print_safe("\n".join(lines))

    def _log_non_verbose(self, message):
        msg_type = message.get("TYPE")
        if msg_type == protocol.MessageType.PROFILE:
            display_name = message.get('DISPLAY_NAME') or message.get('USER_ID', 'Unknown')
            print_safe(f"\n> {display_name}: {message.get('STATUS', '')}")
        elif msg_type == protocol.MessageType.POST:
            # Only log posts if we're following the sender or if we sent it
            from_user_id = message.get('USER_ID')
            if from_user_id in self.following or message.get('origin') == "Sent":  # Add following as parameter
                print_safe(f"\n> Post from {message.get('USER_ID')}: {message.get('CONTENT')}")
        elif msg_type == protocol.MessageType.DM:
            from_id = message.get('FROM')
            to_id = message.get('TO')
            is_outgoing = from_id == self.user_id
            if is_outgoing:
                name = self._get_display_name(to_id)
                direction = f"TO {name}"
            else:
                name = self._get_display_name(from_id)
                direction = f"FROM {name}"
            print_safe(f"\n> [DM {direction}]: {message.get('CONTENT')}")
        elif msg_type == protocol.MessageType.FOLLOW:
            print_safe(f"\n> User {message.get('FROM')} has followed you.")
        elif msg_type == protocol.MessageType.UNFOLLOW:
            print_safe(f"\n> User {message.get('FROM')} has unfollowed you.")
        # PING, ACK, and other automatic messages are not printed in non-verbose mode
