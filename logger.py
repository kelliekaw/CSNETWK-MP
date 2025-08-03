import protocol

class Logger:
    def __init__(self, verbose=False):
        self.verbose = verbose

    def log(self, message, origin=None):
        if self.verbose:
            self._log_verbose(message, origin)
        else:
            self._log_non_verbose(message)

    def _log_verbose(self, message, origin):
        print(f"\n--- Verbose Log ---")
        if origin:
            print(f"Origin: {origin}")
        for key, value in message.items():
            print(f"  {key}: {value}")
        print("---------------------")

    def _log_non_verbose(self, message):
        msg_type = message.get("TYPE")
        if msg_type == protocol.MessageType.PROFILE:
            print(f"> {message.get('DISPLAY_NAME', 'Unknown')}: {message.get('STATUS', '')}")
        elif msg_type == protocol.MessageType.POST:
            # This will be improved later to show the display name
            print(f"> Post from {message.get('USER_ID')}: {message.get('CONTENT')}")
        elif msg_type == protocol.MessageType.DM:
            direction = "To" if message.get('TO') else "From"
            user = message.get('TO') or message.get('FROM')
            print(f"> [DM {direction} {user}]: {message.get('CONTENT')}")
        # PING, ACK, and other automatic messages are not printed in non-verbose mode
