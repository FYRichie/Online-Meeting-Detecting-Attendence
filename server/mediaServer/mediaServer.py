import socket
import threading
import time

class MediaServer():
    def __init__(self, ip: str = "0.0.0.0", port: int = 4000, maximum_user: int = 2):
        # self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # RTSP uses TCP, RTP uses UDP
        self.ip = ip
        self.port = [port]
        # self.maximum_user = maximum_user
        self.users = {}
        self.thread_send = {}
        self.thread_recv = {}

    def start(self):
        print("Media server start at %s:%d" % (self.ip, self.port[0]))
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.ip, self.port[0]))

        while True:
            in_data, addr = self.socket.recvfrom(1024)
            print(in_data)
            url = "%s:%d" % addr
            if url not in self.users:
                self.users[url] = {
                    "current_display": None,
                    "recv_port": self.port[-1] + 1,
                    "send_port": self.port[-1] + 2
                }
                self.port.append(self.port[-1] + 1)
                self.port.append(self.port[-1] + 2)
                self.socket.sendto(str(self.users[url]["recv_port"]).encode(), addr)

                self.thread_recv[url] = threading.Thread(target=self.recv, args=(addr[0], addr[1]))
                self.thread_send[url] = threading.Thread(target=self.send, args=(addr[0], addr[1]))
                self.thread_recv[url].start()
                self.thread_send[url].start()
                
            else:
                print("%s alreading inside socket" % url)
                print(self.users.keys())

    # server get new frame
    def recv(self, user_ip: str, user_port: int):
        print("%s:%d recv thread started" % (user_ip, user_port))
        recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        user = "%s:%d" % (user_ip, user_port)
        recv_socket.bind((self.ip, self.users[user]["recv_port"]))
        
        while True:
            # 1920 * 1680 rgb image plus other informations
            size = 1920 * 1680 * 3 + 4096
            data, addr = recv_socket.recvfrom(size)
            print("Port %d received: %s" % (self.users[user]["recv_port"], data.decode()))
            data = data.decode()
            if user_ip == addr[0] and user_port == addr[1]:
                user = "%s:%d" % (addr)
                # self.users[user]["current_display"] = data["img"]
                self.users[user]["current_display"] = data
            time.sleep(5)
    
    # thread listen to current status, then send frame
    def send(self, user_ip: str, user_port: int):
        print("%s:%d send thread started" % (user_ip, user_port))
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        user = "%s:%d" % (user_ip, user_port)
        send_socket.bind((self.ip, self.users[user]["send_port"]))

        while True:
            # RTP packet
            data = {
                "display": [],
                "RTP_header": None
            }
            print("Port %d send: " % (self.users[user]["send_port"]), data)
            send_socket.sendto(str(data).encode(), (user_ip, user_port))
            time.sleep(5)
