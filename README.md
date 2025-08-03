# LSNP Client - Milestone 1

This is a Python implementation of the Local Social Networking Protocol (LSNP), focused on completing the requirements for Milestone #1.

## Implemented Features

*   **Peer Discovery:** Clients discover each other using a `PING`/`PROFILE` exchange.
*   **Message Parsing:** Correctly parses `PROFILE`, `POST`, and `DM` messages.
*   **Concurrent Operation:** Sends and receives messages simultaneously using multiple threads.
*   **Verbose/Non-Verbose Logging:** Supports both logging modes via a `--verbose` flag.
*   **Message Storage & Viewing:** Stores all received `POST` and `DM` messages and allows viewing them on a per-user basis.

## How to Run

1.  Open a command prompt or terminal.
2.  Navigate to the project directory.
3.  Run the client using the following command format:

    ```
    python lsnp_client.py <user_id> <display_name> [--verbose]
    ```

    *   `<user_id>`: A unique identifier, e.g., `alice@192.168.1.11`. **You must use the machine's actual local IP address.**
    *   `<display_name>`: The name to display to other users.
    *   `--verbose` (Optional): Enables detailed message logging.

    **Example:**
    ```
    python lsnp_client.py alice@192.168.1.11 Alice --verbose
    ```

## Available Commands

Once the client is running, you can use the following commands:

*   `peers`: Lists all other users currently detected on the network.
*   `post <message>`: Broadcasts a public message to all peers.
*   `dm <user_id> <message>`: Sends a private Direct Message to a specific user.
*   `view <user_id>`: Displays the message history (Posts and DMs) for a specific user.
