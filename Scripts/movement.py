# Patrick Sacchet
# This script serves to explore possible approaches following network analysis of movement commands sent to the Sanpyl-Indoor-Camera

# TODO:
    # Spin up listener thread?
    # Look into initial exchange to ensure we dont need any other traffic sent prior to commands 


import socket
from pynput import keyboard
from enum import Enum

# Supposed 'keep alive' bytes 
KEEP_ALIVE = b'\xf1\xe1\x00\x00'

# Define the different sections of our 36 byte payload 
HEADER = b'\xF1\xd0\x00\x20\xd1\x00' # From our analysis only the first 6 bytes are the same for some reason
HEADER_RAND = b'\x00\x49' # Random two bytes.. idk 
BODY = b'\x00\x10\x00\x00\x14\x00\x00\x00' # Next 8 bytes are the same
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

# Build out a packet to tell our robot to move its head up, down, left or right 
def constructCommandPacket(direction: Direction) -> bytes:
    packet = b''

    # Build everything thats the same for our packet
    packet+= HEADER + HEADER_RAND + BODY

    match direction:
        case Direction.UP:
            packet += UP_COMMAND
        case Direction.DOWN:
            packet += DOWN_COMMAND
        case Direction.LEFT:
            packet += LEFT_COMMAND
        case Direction.RIGHT:
            packet += RIGHT_COMMAND

    packet += FOOTER
    return packet

# Callback for our listener thread
    # From here, depending on the keystroke given by the user, we send the appropiate packet to the target device
def onPress(key, target_ip, port, sock):
    try:
        match key:
                case keyboard.Key.up:
                    print("Sending move up command...\n")
                    packet = constructCommandPacket(Direction.UP)
                case keyboard.Key.down:
                    print("Sending move down command...\n")
                    packet = constructCommandPacket(Direction.DOWN)                
                case keyboard.Key.left:
                    print("Sending move left command...\n")
                    packet = constructCommandPacket(Direction.LEFT)                
                case keyboard.Key.right:
                    print("Sending move right command...\n")
                    packet = constructCommandPacket(Direction.RIGHT)                
                case keyboard.Key.esc:
                    return False
        sock.sendto(packet, (target_ip, port))
    except socket.error as e:
        print("ERROR: Failed to send packet " + str(e))
        return False

# Create a UDP connection to target using user specified ip and port
def establishSocket() -> socket.socket:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    except socket.error as e:
        print("ERROR: Failed to establish socket \n" + str(e))
        return False
    
    return sock


def determinePort():
    return


def main():
    # Grab the target ip and desired port (if any) from user
    target_ip = input("Input target ip > ")
    port = input("Input target port > ")

    sock = establishSocket()

    # Keep taking input from user, use arrow keys to map to head movement 
    with keyboard.Listener(on_press=lambda event:onPress(event, target_ip=target_ip, port=int(port), sock=sock)) as listener:
        listener.join()
        

if __name__ == '__main__':
    main()