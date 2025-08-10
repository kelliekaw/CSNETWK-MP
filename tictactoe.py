class TicTacToe:
    def __init__(self, player_id, opponent_id):
        self.board = [str(i) for i in range(9)]
        self.turn_number = 0
        self.player_symbol = None
        self.player_id = player_id
        self.opponent_symbol = None
        self.opponent_id = opponent_id

    def assign_symbols(self, player_symbol):
        self.player_symbol = player_symbol
        self.opponent_symbol = "O" if player_symbol == "X" else "X"

    def display_board(self):
        return (
            f"\n"
            f" {self.board[0]} | {self.board[1]} | {self.board[2]}\n"
            f"---+---+---\n"
            f" {self.board[3]} | {self.board[4]} | {self.board[5]}\n"
            f"---+---+---\n"
            f" {self.board[6]} | {self.board[7]} | {self.board[8]}\n"
        )

    def make_move(self, position, symbol):
        if 0 <= position <= 8 and self.board[position] not in ["X", "O"]:
            self.board[position] = symbol
            self.turn_number += 1
            return True
        return False

    def check_winner(self):
        wins = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6)
        ]
        for a, b, c in wins:
            if self.board[a] != " " and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        if " " not in self.board:
            return "Draw"
        return None
