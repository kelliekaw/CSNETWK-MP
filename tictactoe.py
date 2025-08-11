from shared import print_safe

class TicTacToe:
    def __init__(self, player_x, player_o):
        self.player_x = player_x  # user_id with X
        self.player_o = player_o  # user_id with O
        self.board = [' '] * 9  # 3x3 board flattened
        self.turn = 1  # X always starts
        self.winner = None
        self.is_draw = False
        self.current_symbol = 'X'
        self.winning_line = None
        self.winning_symbol = None


    def print_board(moves):
        # moves is a list of 9 elements: either 'X', 'O', or None (empty)
        display = [str(i) if moves[i] == ' ' else moves[i] for i in range(9)]
        
        print(f" {display[0]} | {display[1]} | {display[2]} ")
        print("---+---+---")
        print(f" {display[3]} | {display[4]} | {display[5]} ")
        print("---+---+---")
        print(f" {display[6]} | {display[7]} | {display[8]} ")

    def make_move(self, symbol, position, turn_number, user_id):
        if turn_number != self.turn:
            return False, "Invalid turn number"
        if symbol != self.current_symbol:
            return False, "Not this player's turn"
        if position < 0 or position > 8 or self.board[position] != ' ':
            return False, "Invalid position"

        self.board[position] = symbol
        # Check for win or draw
        if self.check_winner(symbol):
            self.winner = user_id
            self.winning_symbol = symbol
        elif self.check_draw():
            self.is_draw = True
        else:
            # Switch turns
            self.current_symbol = "O" if self.current_symbol == "X" else "X"
            self.turn += 1

        return True, "Move accepted"

    def check_winner(self, symbol):
        wins = [
            [0,1,2], [3,4,5], [6,7,8],  # rows
            [0,3,6], [1,4,7], [2,5,8],  # cols
            [0,4,8], [2,4,6]            # diagonals
        ]
        for line in wins:
            if all(self.board[pos] == symbol for pos in line):
                self.winning_line = line
                return True
        return False

    def check_draw(self):
        return all(s != ' ' for s in self.board) and not self.winner

    def print_board(self):
        b = self.board
        print_safe(f"\n {b[0]} | {b[1]} | {b[2]}\n---+---+---\n {b[3]} | {b[4]} | {b[5]}\n---+---+---\n {b[6]} | {b[7]} | {b[8]}\n")

    def get_status(self):
        if self.winner:
            return f"Game over! Winner: {self.winner}"
        elif self.is_draw:
            return "Game over! Draw."
        else:
            return f"Next turn: {self.turn}"
