# Patrick Sacchet
# This script serves to explore possible approaches following network analysis of movement commands sent to the Sanpyl-Indoor-Camera

# This script requires that the actor knows what the active listening port is on the device; they must watch network traffic 
    # in order to determine this. Otherwise, we will be get a 'destination unreachable error'
    # The device changes port approx. every 5 minutes, sending packets confirming this roughly every 32 seconds 

# TODO:
    # Allow user to choose which port we listen on for the device; change bytes to dynamically generate packet contents for our connect command
    # Look into initial exchange to ensure we dont need any other traffic sent prior to commands 
    # Fix our program not exiting when entering 'escape' key 


import socket
import threading
from pynput import keyboard
from enum import Enum

TERMINATE = False
# Keep count of the number of commands we've sent; the device seems to like to keep track of the current number we're on 
DIRECTION_COMMAND_COUTNER = 0

RESPONDED_TO_STARTUP = False

SENT_KEEP_ALIVE = False

AUTH_DONE = False

# Device seems to like to send 3 blobs before we respond?
COMMAND_BLOBS_SENT = 0

KEEP_ALIVES_RECEIVED = 0

FIRST_SUCCESS = True



# Initial 'connect to us' command (20 bytes)
    # We need to specify our port and ip address so the robot reaches out to us
    # TODO: change connect command ip to user configured 
CONNECT_COMMAND = b'\xf1\x40\x00\x10\x00\x00' # first six bytes seem standard
CONNECT_COMMAND_PORT =b'\xb8\x22' # next two bytes are for our port number (little endian) (8888) 
CONNECT_COMMAND_IP = b'\x01\x89\xa8\xc0' # next four bytes are for our ip address (little endian) (192.168.137.1)
CONNECT_COMMAND_FOOTER = b'\x00\x00\x00\x00\x00\x00\x00\x00' # last 8 bytes are all 0

# Device sends this a ton; once we repond to it initially it will ask us to send auth stuff I think
STARTUP_PACKET = b'\xf1\x41\x00\x14\x54\x47\x53\x56\x00\x00\x00\x00\x00\x01\x50\xc8\x46\x48\x53\x47\x42\x00\x00\x00'

# Weird 14 and 16 byte packets that I think inidcate something is broken
MID_PACKET_1 = b'\xf1\xd1\x00\x0a\xd1\x00\x00\x03\x00\x00\x00\x00\x00\x00'
MID_PACKET_2 = b'\xf1\xd1\x00\x0c\xd1\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00'


# Weird 10 and 12 byte blobs I've seen sent from our phone and device
AUTH_SUCCESS_1 = b'\xf1\xd1\x00\x06\xd1\x00\x00\x01\x00\x00'
AUTH_SUCCESS_2 = b'\xf1\xd1\x00\x08\xd1\x00\x00\x02\x00\x00\x00\x00'

# I think the device may prompt us to send auth with this message, dont echo it 
SEND_AUTH_COMMAND = b'\xf1\x42\x00\x14\x54\x47\x53\x56\x00\x00\x00\x00\x00\x01\x50\xc8\x46\x48\x53\x47\x42\x00\x00\x00'
# This seems to be send from the device after sending our auth blob 
AUTH_ACCEPTED = b'\xf1\xd0\x00\x14\xd1\x00\x00\x00\x03\x80\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x3c\x00\x00\x00'

# Maybe an auth blob? idk
AUTH_BLOB = b'\xf1\xd0\x00\x48\xd1\x00\x00\x00\x02\x80\x00\x00\x3c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x61\x75\x77\x59\x72\x38\x74\x74\x43\x59\x53\x43\x61\x79\x39\x6b\x6e\x52\x54\x7a\x50\x79\x4a\x47\x4e\x69\x54\x31\x54\x6d\x6c\x34\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

# Supposed 'keep alive' bytes 
    # Our phone app alternates between these two packets 
KEEP_ALIVE_1 = b'\xf1\xe0\x00\x00'
KEEP_ALIVE_2 = b'\xf1\xe1\x00\x00'

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

# Send options to start receiving video and hopefully be able to send commands?
    # These are huge so I just copied from Wireshark
DEVICE_OPTIONS = bytes.fromhex("f1d00404d1000001ff010000080000000100000000000000200300000800000000000000010000005204000008000000010000000000000052040000080000000000000000000000580400000800000000000000000000005204000008000000010001000000000052040000080000000000010000000000580400000800000001000000000000005204000008000000010002000000000052040000080000000000020000000000580400000800000002000000000000005204000008000000010003000000000052040000080000000000030000000000580400000800000003000000000000003280000008000000000000000000000088030000040000000000000024800000000400007b2266656174757265223a5b224175746f547261636b696e67222c224461794e69676874222c22537570706f727450545a222c22446f75626c654c69676874222c224d6963726f70686f6e65222c22416c657274536f756e64222c224d442d4361706162696c6974696573222c224361702d446566656e6365222c224361702d5a6f6f6d222c22457874496e737472756374696f6e73225d2c2273657474696e67223a5b22534446726565222c225344546f74616c222c2244657669636554797065222c2276656e646f72222c2276657273696f6e222c2273747265616d5175616c697479222c2253445265636f72644d6f6465222c226d6972726f724d6f6465222c22506f7765724672657175656e6379222c22747261636b4d6f6465222c226e69676874566973696f6e222c22646f75626c654c69676874537461747573222c2243566964656f5175616c697479222c224d6963726f70686f6e65222c2242757a7a6572222c22416c657274536f756e64225d2c2275756964223a22363833324437584355414558227d0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")
DEVICE_OPTIONS_EPILOGUE = bytes.fromhex("f1d00108d10000020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")

# Now its time to attempt to interpret how we respond to the device after we've initiated our control sequence
# Device seems to like to send this first, we seem to echo it 
CONTROL_START = b'\xf1\xd1\x00\x0a\xd1\x00\x00\x03\x00\x01\x00\x02\x00\x01'

# Next 12 bytes it seems to send (echo it?)
CONTROL_NEXT = b'\xf1\xd1\x00\x08\xd1\x00\x00\x02\x00\x01\x00\x01'

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
                    print("Keypress listening thread exiting...")
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
    global TERMINATE # keep, rest should be local 
    global SENT_KEEP_ALIVE
    global AUTH_DONE
    global RESPONDED_TO_STARTUP
    global COMMAND_BLOBS_SENT
    global FIRST_SUCCESS

    SEND_START_COMMAND_PACKET = False

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        sock.bind(("0.0.0.0", 8888))

        while (not TERMINATE):
            data, addr = sock.recvfrom(1032)
            #print("Recevied " + str(data) + " from " + str(addr[0]) + " on port " + str(addr[1]))
            # Check for our special 'send auth' flag
            # Only start sending back keep alives if we're done with our auth sequence 
            if ((data == KEEP_ALIVE_1 or data == KEEP_ALIVE_2) and AUTH_DONE):
                print("Returning keep alive...")
                sock.sendto(data, (addr[0], int(addr[1]))) # echo back to the device
                # Go ahead and try to startup immediately (after we started our keep alives)
                if (not SEND_START_COMMAND_PACKET):
                    print("Sending our device options...")
                    sock.sendto(DEVICE_OPTIONS, (addr[0], int(addr[1])))
                    sock.sendto(DEVICE_OPTIONS_EPILOGUE, (addr[0], int(addr[1])))
                    SEND_START_COMMAND_PACKET = True
            elif (data == SEND_AUTH_COMMAND):
                print("Adding one more auth blob...")
                COMMAND_BLOBS_SENT += 1
                if (COMMAND_BLOBS_SENT == 4):
                    # Start off by sending three keep alives, I think the device expects these I guess (if we havent sent this already)
                    if (not SENT_KEEP_ALIVE):
                        print("Sending initial keep alive...")
                        sock.sendto(KEEP_ALIVE_1, (addr[0], int(addr[1])))
                        sock.sendto(KEEP_ALIVE_1, (addr[0], int(addr[1])))
                        sock.sendto(KEEP_ALIVE_1, (addr[0], int(addr[1])))
                        SENT_KEEP_ALIVE = True
                    print("Sending auth blob...")
                    sock.sendto(AUTH_BLOB, (addr[0], int(addr[1]))) 
                    #sock.sendto(AUTH_BLOB, (addr[0], int(addr[1])))
                    #sock.sendto(AUTH_BLOB, (addr[0], int(addr[1])))
                    #sock.sendto(AUTH_BLOB, (addr[0], int(addr[1])))
                    # TODO: we still send more responses from our phone, not sure if we have to do that here...
            elif (data == AUTH_ACCEPTED):
                print("Auth accepted!")
                AUTH_DONE = True
            elif (data == STARTUP_PACKET):
                print("Standard packet received....")
                if (not RESPONDED_TO_STARTUP):
                    print("Responding to startup sequence...")
                    sock.sendto(STARTUP_PACKET, (addr[0], int(addr[1])))
                    sock.sendto(STARTUP_PACKET, (addr[0], int(addr[1])))
                    sock.sendto(STARTUP_PACKET, (addr[0], int(addr[1])))
                    RESPONDED_TO_STARTUP = True
            # Weird 14 byte packet...
            elif (data == MID_PACKET_1):
                print("Weird 14 byte packet received; echoing back...")
                #sock.sendto(MID_PACKET, (addr[0], int(addr[1])))
                # Try sending our own success?
                sock.sendto(AUTH_SUCCESS_1, (addr[0], int(addr[1])))
                sock.sendto(AUTH_SUCCESS_2, (addr[0], int(addr[1])))
            elif (data == MID_PACKET_2):
                print("Weird 16 byte packet recevied; echoing back...")
                #sock.sendto(MID_PACKET_2, (addr[0], int(addr[1])))
                # Try sending our own success?
                sock.sendto(AUTH_SUCCESS_1, (addr[0], int(addr[1])))
                sock.sendto(AUTH_SUCCESS_2, (addr[0], int(addr[1])))
            elif (data == AUTH_SUCCESS_1):
                print("AUTH SUCCESS PACKET DETECTED!")
                # send our auth one more time 
                if (FIRST_SUCCESS):
                    sock.sendto(AUTH_BLOB, (addr[0], int(addr[1])))
                    FIRST_SUCCESS = False
                else:
                    sock.sendto(AUTH_SUCCESS_1, (addr[0], int(addr[1])))
                    sock.sendto(AUTH_SUCCESS_2, (addr[0], int(addr[1])))
            elif (data == AUTH_SUCCESS_2):
                sock.sendto(AUTH_SUCCESS_2, (addr[0], int(addr[1])))
            elif (data == CONTROL_START):
                print("Control start detected...")
                sock.sendto(CONTROL_START, (addr[0], int(addr[1])))
            elif (data == CONTROL_NEXT):
                print("Control next detected...")
                sock.sendto(CONTROL_NEXT, (addr[0], int(addr[1])))
            # Dont echo back anything else
            #else:
                #print("Not sure what this is: " + str(data))   
                #sock.sendto(data, (addr[0], int(addr[1])))
                
    except socket.error as e:
        print("ERROR: Failed listener socket " + str(e))
    print("Listen thread exiting...")

    return

# Do all the things!
def main():
    global TERMINATE

    # Grab the target ip and desired port from user
    target_ip = input("Input target ip > ")
    port = input("Input target port > ")

    # Spin up a listener thread to get everything the bot sends us 
        # Will send appropiate responses depending on what we get/where we are in the setup sequence 
    print("Spinning up listener thread...")
    listen_thread = threading.Thread(target=receiveData)

    listen_thread.start()

    # Establish our own socket we'll use for sending 
    sock = establishSocket()

    # Now tell the robot to reach out to us, and establish a socket to listen for data 
        # A lot of data we receive will need to be echoed back I fear
    sock.sendto(constructConnectCommandPacket(), (target_ip, int(port)))

    print("Spinning up keypress listener thread... (press ESC to exit)\n")

    # Keep taking input from user, use arrow keys to map to head movement 
    with keyboard.Listener(on_press=lambda event:onPress(event, target_ip=target_ip, port=int(port), sock=sock)) as listener:
        listener.join()
        # When the key press thread is exiting, that means the user is done so signal our listening thread to exit
        TERMINATE = True
        listen_thread.join()
        

if __name__ == '__main__':
    main()