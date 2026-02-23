from socket import *
from datetime import datetime
import json

with open("messenger.json", "r") as data:
    MESSENGER = json.load(data)
FILTER_WORDS = MESSENGER["filter_words"]
USERS = MESSENGER["users"]

def encode(msg, shift=13):
    res = ""
    for c in msg:
        if c.isalpha():
            if 'A'<= c <= 'Z': # char is uppercase :
                point = ord('A')
            else:
                point = ord('a')
            res += (chr(point + (ord(c) - point + shift) % 26))
        else: # if char is number we append it self
            res += c
    return res # now our msg is encoded using ROT with custom shift or 13 as default

def decode(msg, shift=13): # our encoding is symmetric so...
    return encode(msg, 26 - shift) # returns decoded message 

def xor_encode(msg, val): # we use xor_encoding as our custom symmetrical encode
    res = ""
    for c in msg:
        char_code = ord(c)
        char_code_xor = char_code ^ val
        encoded_char = chr(char_code_xor)
        res += encoded_char
    return res

def xor_decode(msg, val):
    return xor_encode(msg, val)

def setup_server(port):
    print("Starting server on port:", port)
    listening_s = socket(family=AF_INET, type=SOCK_STREAM, proto=0) # ipv4, tcp
    try:
        listening_s.bind(('0.0.0.0', port)) # listens for every ip address we could also use 127.0.0.1 for only this computer (localhost)
        print("Bound to port:", port)
        listening_s.listen(1) # have maximum number of 1 guests in queue
        print("Listening for connection...")
        conn, addr = listening_s.accept() # accept the first guest in the queue
        print("Connection established with:", addr)
        print(conn.getsockname(), conn.getpeername())
        return conn, addr
    except Exception:
        print("setup_server failed")
        return None, None # will reaise error in gui

def setup_client(host, port):
    print(f"Client trying to connect to {host}:{port}")
    s = socket(AF_INET, SOCK_STREAM)
    s.settimeout(10)
    try:
        s.connect((host, port))
        print("client socket:", s.getsockname())   
        return s
    except Exception as e:
        print(f"error in setup_client: {e}")
        return None

def send_message(sock, msg, shift, username, custom_encode_mode=False):
    if custom_encode_mode:
        encoded_msg = xor_encode(msg, shift)  # Use shift as the XOR key
    else:
        encoded_msg = encode(msg, shift)      # Regular encoding
        
    log_message("sent", msg, username)
    log_cipher_message("sent", encoded_msg, username)
    # Now we should convert our string message to bytes so it can be sent over in socket since they only transfer rawbytes
    data = encoded_msg.encode('utf-8')
    length = len(data) # length is integer so it should be converted to bytes
    length_byte = length.to_bytes(4, 'big') 
    sock.sendall(length_byte + data)



def receive_message(sock, shift, username=None, custom_encode_mode=False):
    sock.settimeout(0) # we can check every 500ms for new message(even empty ones) without freezing program 
    try:
        length_bytes = sock.recv(4)
        if not length_bytes:
            return None
        length = int.from_bytes(length_bytes, 'big')
        data = b''
        while len(data) < length:
            packet = sock.recv(length - len(data))
            if not packet:
                return None
            data += packet
        encoded_msg = data.decode("utf-8")
        log_cipher_message("recv", encoded_msg, username)
        if custom_encode_mode:
            decoded_msg = xor_decode(encoded_msg, shift)  # Use shift as the XOR key
        else:
            decoded_msg = decode(encoded_msg, shift)
        log_message("recv", decoded_msg, username)
        return decoded_msg
    except Exception:
        return None

def close_socket(sock):
    try:
        print(f"Socket is being shut down: {sock.getsockname()}")
        sock.shutdown(SHUT_RDWR) # shuts down reading and writing in socket shut_rd shut_wr shut_rdwr
        sock.close()
    except Exception:
        print("Socket shutdown failed.")

def log_message(direction, msg, username):
    now = datetime.now()
    nowDay = now.strftime("%Y%m%d")
    nowTime = now.strftime('%H:%M:%S')
    chat_log_file_name = f"chat_log_{nowDay}.txt"
    with open(chat_log_file_name, "a", encoding="utf-8") as f:
        f.write(f"{nowTime} {username} {direction} : {msg}\n")

def log_cipher_message(direction, data, username):
    now = datetime.now()
    nowDay = now.strftime("%Y%m%d")
    nowTime = now.strftime('%H:%M:%S')
    cipher_log_file_name = f"cipher_log_{nowDay}.txt"
    with open(cipher_log_file_name, "a", encoding="utf-8") as f:
        f.write(f"{nowTime} {username} {direction} : {data}\n")
        

