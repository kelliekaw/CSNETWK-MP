import protocol
from shared import print_safe
        
class Logger:
    def __init__(self, verbose=False, user_id=None):
        self.verbose = verbose
        self.user_id = user_id

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
            print_safe(f"\n> {message.get('DISPLAY_NAME', 'Unknown')}: {message.get('STATUS', '')}")
        elif msg_type == protocol.MessageType.POST:
            # Only log posts if we're following the sender or if we sent it
            from_user_id = message.get('USER_ID')
            if from_user_id in self.following or message.get('origin') == "Sent":  # Add following as parameter
                print_safe(f"\n> Post from {message.get('USER_ID')}: {message.get('CONTENT')}")
        elif msg_type == protocol.MessageType.DM:
            from_id = message.get('FROM')
            to_id = message.get('TO')
            is_outgoing = from_id == self.user_id
            direction = f"To {to_id}" if is_outgoing else f"From {from_id}"
            print_safe(f"\n> [DM {direction}]: {message.get('CONTENT')}")
        elif msg_type == protocol.MessageType.FOLLOW:
            print_safe(f"\n> User {message.get('FROM')} has followed you.")
        elif msg_type == protocol.MessageType.UNFOLLOW:
            print_safe(f"\n> User {message.get('FROM')} has unfollowed you.")
        # PING, ACK, and other automatic messages are not printed in non-verbose mode
