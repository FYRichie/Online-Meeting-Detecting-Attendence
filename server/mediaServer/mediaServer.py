import socket
import threading
import time
from typing import Dict

from .user import User
from utils.RTSP_packet import RTSPPacket
from utils.RTP_packet import RTPPacket
from utils.camera_stream import CameraStream

class MediaServer():
    IP = "127.0.0.1"
    PORT = 3000
    CLIENT_BUFFER = 1024
    RTP_TIMEOUT = 5  # ms
    SERVER_TIMEOUT = 100  # ms

    def __init__(self, maximum_user: int = 2):
        self.RTSPsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Use TCP as protocal
        self.RTPport = []  # Port for RTP connection
        self.users: Dict[str, User] = {}
        self.maximum_user = maximum_user
        self.testuser = User()

    def start(self):
        print("Media server start at %s:%d" % self.IP, self.PORT)
        self.RTSPsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.RTSPsocket.bind((self.IP, self.PORT))

        while True:
            client, addr = self.RTSPsocket.accept()
            url = "%s:%d" % addr
            if url not in self.users:
                self.users[url] = User(
                    client=client,
                    RTSP_thread=threading.Thread(target=self.RTSP_connection, args=(url, ))
                )
                self.users[url].RTSP_thread.start()

    def RTSP_connection(self, user_url: str):
        client = self.users[user_url].client
        while True:
            message = client.recv(self.CLIENT_BUFFER)
            packet = RTSPPacket.from_response(message)

            if packet.type == RTSPPacket.SETUP:
                if not self.users[user_url].is_setup:
                    last_port = self.PORT if len(self.RTPport) == 0 else self.RTPport[-1]
                    self.users[user_url].RTP_recv_port = last_port + 1
                    self.users[user_url].RTP_send_port = last_port + 2
                    self.RTPport.append(last_port + 1)
                    self.RTPport.append(last_port + 2)


                    self.users[user_url].RTP_recv_thread = threading.Thread(target=self.RTP_recv, args=(user_url, ))
                    self.users[user_url].RTP_send_thread = threading.Thread(target=self.RTP_send, args=(user_url, ))
                    self.users[user_url].RTP_recv_thread.start()
                    self.users[user_url].RTP_send_thread.start()

                    res = {
                        "port_sendto": last_port + 1,  # Client sends to server "recv" port
                        "port_recvfrom": last_port + 2
                    }
                    client.send(bytes(res))
                else:
                    print(
                        "User %s is setup already, using %d as recv port, %d as send port" % (
                            user_url,
                            self.users[user_url].RTP_recv_port,
                            self.users[user_url].RTP_send_port
                    ))
            elif packet.type == RTSPPacket.PLAY:
                # TODO
                pass
            elif packet.type == RTSPPacket.PAUSE:
                # TODO
                pass
            elif packet.type == RTSPPacket.TEARDOWN:
                # TODO
                pass

    def RTP_recv(self, user_url: str):
        print("%s recv thread started" % user_url)
        user_addr = user_url.split(":")
        user_ip, user_port = user_addr[0], int(user_addr[1])
        ip = self.IP
        port = self.users[user_url].RTP_recv_port
        
        recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
        recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_socket.bind((ip, port))
        recv_socket.settimeout(self.RTP_TIMEOUT / 1000.)

        while True:
            recv = bytes()
            while True:
                try:
                    data, addr = recv_socket.recvfrom(1024)
                    if user_ip == addr[0] and user_port == addr[1]:
                        recv += data
                    else:
                        break
                    if recv.endswith(CameraStream.IMG_END):
                        break
                except socket.timeout:
                    continue
            payload = RTPPacket.from_packet(recv).get_payload()
            self.users[user_url].current_display = payload["img"]
            self.users[user_url].name = payload["name"]
            time.sleep(self.SERVER_TIMEOUT / 1000.)

    def RTP_send(self, user_url: str):
        print("%s send thread started" % user_url)
        user_addr = user_url.split(":")
        user_ip, user_port = user_addr[0], int(user_addr[1])
        ip = self.IP
        port = self.users[user_url].RTP_send_port

        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
        send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        send_socket.bind((ip, port))
        send_socket.settimeout(self.RTP_TIMEOUT / 1000.)

        while True:
            payload = {}
            for user in self.users:
                if user != user_url:
                    payload[user] = {
                        "name": self.users[user_url].name,
                        "current_display": self.users[user].current_display
                    }
            packet = RTPPacket(
                RTPPacket.TYPE.IMG,
                int(time.time()),
                int(time.time()),
                bytes(payload)
            ).get_packet()
            send_socket.sendto(packet, (user_ip, user_port))
        