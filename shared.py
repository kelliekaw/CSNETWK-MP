#Sidney Chan
#Kellie Kaw
import threading

print_lock = threading.Lock()

def print_safe(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)