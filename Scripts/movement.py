# Patrick Sacchet
# This script serves to explore possible approaches following network analysis of movement commands sent to the Sanpyl-Indoor-Camera

# This script requires that the actor knows what the active listening port is on the device; they must watch network traffic 
    # in order to determine this. Otherwise, we will be get a 'destination unreachable error'
    # The device changes port approx. every 5 minutes, sending packets confirming this roughly every 32 seconds 

# TODO:
    # Spin up listener thread?
    # Look into initial exchange to ensure we dont need any other traffic sent prior to commands 


import socket
import threading
from pynput import keyboard
from enum import Enum

DIRECTION_COMMAND_COUTNER = 0

# Initial 'connect to us' command (20 bytes)
    # We need to specify our port and ip address so the robot reaches out to us
    # TODO: change connect command ip to user configured 
CONNECT_COMMAND = b'\xf1\x40\x00\x10\x00\x00' # first six bytes seem standard
CONNECT_COMMAND_PORT =b'\xb8\x22' # next two bytes are for our port number (little endian) (8888) 
CONNECT_COMMAND_IP = b'\x01\x89\xa8\xc0' # next four bytes are for our ip address (little endian) (192.168.137.1)
CONNECT_COMMAND_FOOTER = b'\x00\x00\x00\x00\x00\x00\x00\x00' # last 8 bytes are all 0

# Maybe an auth blob? idk
AUTH_BLOB = b'\xf1\xd0\x00\x48\xd1\x00\x00\x00\x02\x80\x00\x00\x3c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x61\x75\x77\x59\x72\x38\x74\x74\x43\x59\x53\x43\x61\x79\x39\x6b\x6e\x52\x54\x7a\x50\x79\x4a\x47\x4e\x69\x54\x31\x54\x6d\x6c\x34\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

# Supposed 'keep alive' bytes 
    # Our phone app alternates between these two packets 
KEEP_ALIVE_1 = b'\xf1\xe1\x00\x00'
KEEP_ALIVE_2 = b'\xf1\xe0\x00\x00'

# Define the different sections of our 36 byte payload 
HEADER = b'\xF1\xd0\x00\x20\xd1\x00' # From our analysis only the first 6 bytes are the same for some reason
HEADER_RAND = b'\x00\x00' # Random two bytes.. idk (serves as a counter?)
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
def constructDirectionCommandPacket(direction: Direction) -> bytes:
    packet = b''
    global DIRECTION_COMMAND_COUTNER

    counter_bytes = DIRECTION_COMMAND_COUTNER.to_bytes(2, 'big')

    # Build everything thats the same for our packet
        # TODO: change HEADER_RAND to counter we increment 
    packet+= HEADER + counter_bytes + BODY

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
    # Increment our counter for next command 
    DIRECTION_COMMAND_COUTNER += 1
    return packet

def constructConnectCommandPacket() -> bytes:
    packet = b''
    
    packet += CONNECT_COMMAND + CONNECT_COMMAND_PORT + CONNECT_COMMAND_IP + CONNECT_COMMAND_FOOTER

    return packet

# Callback for our listener thread
    # From here, depending on the keystroke given by the user, we send the appropiate packet to the target device
def onPress(key, target_ip, port, sock):
    try:
        match key:
                case keyboard.Key.up:
                    print("Sending move up command...")
                    packet = constructDirectionCommandPacket(Direction.UP)
                case keyboard.Key.down:
                    print("Sending move down command...")
                    packet = constructDirectionCommandPacket(Direction.DOWN)                
                case keyboard.Key.left:
                    print("Sending move left command...")
                    packet = constructDirectionCommandPacket(Direction.LEFT)                
                case keyboard.Key.right:
                    print("Sending move right command...")
                    packet = constructDirectionCommandPacket(Direction.RIGHT)                
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
        print("ERROR: Failed to establish socket" + str(e))
        return False
    
    return sock

# Listen on our UDP port for packets from our robot 
def receiveData():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        sock.bind(("0.0.0.0", 8888))

        while True:
            data, addr = sock.recvfrom(1024)
            print("Recevied " + str(data) + " from " + str(addr[0]) + " on port " + str(addr[1]))
            sock.sendto(data, (addr[0], int(addr[1]))) # echo back to the device 
    except socket.error as e:
        print("ERROR: Failed listener socket " + str(e))

    return

# Do all the things!
def main():
    # Grab the target ip and desired port (if any) from user
    target_ip = input("Input target ip > ")
    port = input("Input target port > ")

    # Spin up a listener thread to get everything the bot sends us 
    print("Spinning up listening thread...")
    listen_thread = threading.Thread(target=receiveData)

    listen_thread.start()

    # Establish our own socket we'll use for sending 
    sock = establishSocket()

    # Now tell the robot to reach out to us, and establish a socket to listen for data 
        # A lot of data we receive will need to be echoed back I fear
    sock.sendto(constructConnectCommandPacket(), (target_ip, int(port)))

    # Send this 'auth blob' type thing we always send on connect 
    sock.sendto(AUTH_BLOB, (target_ip, int(port)))

    # Send ok after we get the all clear?

    # Keep taking input from user, use arrow keys to map to head movement 
    with keyboard.Listener(on_press=lambda event:onPress(event, target_ip=target_ip, port=int(port), sock=sock)) as listener:
        listener.join()
        listen_thread.join()
        

if __name__ == '__main__':
    main()