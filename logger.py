import protocol
from shared import print_safe
        
class Logger:
    def __init__(self, verbose=False, user_id=None, own_display_name=None, online_peers=None, groups=None):
        self.verbose = verbose
        self.user_id = user_id
        self.own_display_name = own_display_name or user_id
        self.online_peers = online_peers if online_peers is not None else {}
        self.groups = groups if groups is not None else {}
        self.show_only_group_messages = False

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
        lines = ["\n--- Verbose Log ---"]
        if origin:
            lines.append(f"Origin: {origin}")
        for key, value in message.items():
            lines.append(f"  {key}: {value}")
        lines.append("--------------------")
        print_safe("\n".join(lines))

    def _log_non_verbose(self, message):
        if self.show_only_group_messages and message.get("TYPE") != protocol.MessageType.GROUP_MESSAGE:
            return

        msg_type = message.get("TYPE")
        from_id = message.get('FROM')
        to_id = message.get('TO')
        if msg_type == protocol.MessageType.PROFILE:
            display_name = message.get('DISPLAY_NAME') or message.get('USER_ID', 'Unknown')
            print_safe(f"\n> {display_name}: {message.get('STATUS', '')}")
        elif msg_type == protocol.MessageType.POST:
            # Only log posts if we're following the sender or if we sent it
            from_user_id = message.get('USER_ID')
            if from_user_id in self.following or message.get('origin') == "Sent":  # Add following as parameter
                print_safe(f"\n> Post from {message.get('USER_ID')}: {message.get('CONTENT')}")
        elif msg_type == protocol.MessageType.DM:
            is_outgoing = from_id == self.user_id
            if is_outgoing:
                name = self._get_display_name(to_id)
                direction = f"TO {name}"
            else:
                name = self._get_display_name(from_id)
                direction = f"FROM {name}"
            print_safe(f"\n> [DM {direction}]: {message.get('CONTENT')}")
        elif msg_type == protocol.MessageType.FOLLOW:
            if from_id == self.user_id:
                name = self._get_display_name(to_id)
                print_safe(f"\n> Started following User {name}.")
            else:
                name = self._get_display_name(from_id)
                print_safe(f"\n> User {name} has followed you.")
        elif msg_type == protocol.MessageType.UNFOLLOW:
            if from_id == self.user_id:
                name = self._get_display_name(to_id)
                print_safe(f"\n> User {name} has been unfollowed.")
            else:
                name = self._get_display_name(from_id)
                print_safe(f"\n> User {name} has unfollowed you.")
        elif msg_type == protocol.MessageType.GROUP_CREATE:
            print_safe(f"You've been added to {message.get('GROUP_NAME')}")
        elif msg_type == protocol.MessageType.GROUP_UPDATE:
            group_id = message.get("GROUP_ID")
            group_name = self.groups.get(group_id, {}).get("GROUP_NAME", "Unknown Group")
            print_safe(f"The group \"{group_name}\" member list was updated")
        elif msg_type == protocol.MessageType.GROUP_MESSAGE:
            if from_id == self.user_id: 
                name = self.own_display_name
            else:
                name = self._get_display_name(from_id)
            
            print_safe(f"{name} sent \"{message.get('CONTENT')}\"")

        elif msg_type == protocol.MessageType.TICTACTOE_INVITE:
            if to_id == self.user_id:
                name = self._get_display_name(from_id)
                print_safe(f"\n> {name} is inviting you to play tic-tac-toe.")
        # PING, ACK, and other automatic messages are not printed in non-verbose mode
