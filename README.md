Sidney Chan, 
Kellie Kaw

# LSNP Client - Full Implementation

This is a Python implementation of the Local Social Networking Protocol (LSNP), a decentralized communication framework that facilitates social networking functionality within local area networks (LANs) without relying on centralized servers or internet connectivity.

## Implemented Features

### Core Functionality
*   **Peer Discovery:** Clients discover each other using a `PING`/`PROFILE` exchange.
*   **Message Parsing:** Correctly parses all LSNP message types.
*   **Concurrent Operation:** Sends and receives messages simultaneously using multiple threads.
*   **Verbose/Non-Verbose Logging:** Supports both logging modes via a `--verbose` flag.
*   **Message Storage & Viewing:** Stores all received messages and allows viewing them on a per-user basis.

### Social Features
*   **Profiles:** Users can set display names, status messages, and avatars (under 20KB).
*   **Posts:** Broadcast public messages to all followers with customizable TTL.
*   **Direct Messages:** Private messaging between users.
*   **Following System:** Follow/unfollow other users to control content visibility.
*   **Likes:** Like and unlike posts from other users.

### File Sharing
*   **File Transfer:** Send and receive files between users with automatic chunking.
*   **Offer/Accept Model:** Files must be accepted before transfer begins.


### Groups
*   **Group Creation:** Create groups with multiple members.
*   **Group Management:** Add or remove members from existing groups.
*   **Group Messaging:** Send messages visible to all group members.

### Gaming
*   **Tic-Tac-Toe:** Play Tic-Tac-Toe games with other users on the network.
*   **Game Invites:** Send and accept game invitations.
*   **Move Validation:** Automatic validation of game moves.

### Security & Privacy
*   **Token-Based Authentication:** All actions are authorized with scoped, time-limited tokens.
*   **Token Revocation:** Revoke tokens to immediately prevent further use.
*   **Message Acknowledgements:** Automatic ACKs for reliable message delivery.

## How to Run

1.  Open a command prompt or terminal.
2.  Navigate to the project directory.
3.  Run the client using the following command:

    ```bash
    python lsnp_client.py [--verbose]
    ```

    *   `--verbose` (Optional): Enables detailed message logging.
    *   The client will prompt for user information (username, display name, status, avatar) at startup.

    **Example:**
    ```bash
    python lsnp_client.py --verbose
    ```

## Available Commands

Once the client is running, you can use the interactive menu system to access all features:

### Main Menu
*   `[1] Posts`: View, create, like, and unlike posts
*   `[2] DMs`: View and send direct messages
*   `[3] Peers`: View peers, follow/unfollow users, and view profiles
*   `[4] Files`: Send and receive files
*   `[5] Groups`: Create, update, and message groups
*   `[6] Tic-Tac-Toe`: Play Tic-Tac-Toe games
*   `[7] Exit`: Exit the client and revoke all tokens

### Detailed Operations

#### Posts
*   `View Posts`: See posts from a specific user
*   `Create Post`: Broadcast a new post to your followers
*   `Like Post`: Like a post from another user
*   `Unlike Post`: Remove your like from a post

#### DMs
*   `View DMs`: See your message history with a specific user
*   `Send DM`: Send a private message to another user

#### Peers
*   `Show Peers`: List all detected users on the network
*   `View Profile`: See a user's profile and optionally download their avatar
*   `Follow`: Follow a user to see their posts
*   `Unfollow`: Stop following a user

#### Files
*   `Send File`: Offer a file to another user
*   `Accept File Offer`: Accept a file offer from another user

#### Groups
*   `Create Group`: Create a new group with selected members
*   `View Groups`: View information about your groups
*   `Update Group`: Add or remove members from a group
*   `Message Group`: Send a message to all group members
*   `Toggle Group Messages Only`: Filter display to show only group messages

#### Tic-Tac-Toe
*   `Send an Invite`: Invite another user to play Tic-Tac-Toe
*   `Accept Invite`: Accept a pending game invitation

## Protocol Details

This implementation follows the LSNP specification with support for all message types:

*   **User Management**: PROFILE, PING, ACK
*   **Messaging**: POST, DM, LIKE
*   **Social Graph**: FOLLOW, UNFOLLOW
*   **File Transfer**: FILE_OFFER, FILE_CHUNK, FILE_RECEIVED
*   **Session Management**: REVOKE
*   **Groups**: GROUP_CREATE, GROUP_UPDATE, GROUP_MESSAGE
*   **Gaming**: TICTACTOE_INVITE, TICTACTOE_MOVE, TICTACTOE_RESULT

## AI Disclosure

This project was developed with the assistance of AI tools, primarily Qwen and Gemini for generating, debugging and explaining code. The AI was also used to help with:
- Code structure and organization
- Implementation of complex features
- Documentation and comments

All AI code was carefully reviewed, tested, and validated to ensure it meets the project requirements and functions correctly.

