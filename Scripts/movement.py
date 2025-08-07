# Patrick Sacchet
# This script serves to explore possible approaches following network analysis of movement commands sent to the Sanpyl-Indoor-Camera

import socket
from pynput import keyboard
from enum import Enum

# Supposed 'keep alive' bytes 
KEEP_ALIVE = b'\xf1\xe1\x00\x00'

# Define the different sections of our 36 byte payload 
HEADER = b'\x00' # From our analysis only the first 6 bytes are the same for some reason
HEADER_RAND = b'\x00' # Random two bytes.. idk 
BODY_1 = b'\x00\x10\x00\x00\x14\x00\x00\x00' # Next 8 bytes are the same
# The following 8 bytes are direction dependent
UP_COMMAND = b'\x00\x00\x00\x00\x0a\x00\x00\x00'
DOWN_COMMAND = b'\x00\x00\x00\x00\xf6\xff\xff\xff'
LEFT_COMMAND = b'\xfb\xff\xff\xff\x00\x00\x00\x00'
RIGHT_COMMAND = b'\x05\x00\x00\x00\x00\x00\x00\x00'
# Last 12 bytes are all 0's
FOOTER = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

class Direction(Enum):
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4


def constructCommandPacket(direction: Direction) -> bytes:
    return

# Callback for our listener thread
    # From here, depending on the keystroke given by the user, we send the appropiate packet to the target device
def onPress(key, target_ip):
    print(target_ip)
    match key:
            case keyboard.Key.up:
                print("up key")
                
            case keyboard.Key.down:
                print("down key")
            case keyboard.Key.left:
                print("left key")
            case keyboard.Key.right:
                print("right key ")
            case keyboard.Key.esc:
                return False





def determinePort():
    return


def main():
    # Grab the target ip and desired port (if any) from user
    target_ip = input("Input target ip > ")

    # Keep taking input from user, use arrow keys to map to head movement 
    with keyboard.Listener(on_press=lambda event:onPress(event, target_ip=target_ip)) as listener:
        listener.join()
        






if __name__ == '__main__':
    main()