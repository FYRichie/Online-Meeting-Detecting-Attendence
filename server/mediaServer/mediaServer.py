import socket
from multiprocessing import Process
import time
from typing import Dict

from .user import User
from .RTSP_packet import RTSPPacket
from .RTP_packet import RTPPacket
from .camera_stream import CameraStream


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
        print("Media server start at %s:%d" % (self.IP, self.PORT))
        self.RTSPsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.RTSPsocket.bind((self.IP, self.PORT))
        self.RTSPsocket.listen(self.maximum_user)

        while True:
            client, addr = self.RTSPsocket.accept()
            url = "%s:%d" % addr
            if url not in self.users:
                self.users[url] = User(
                    client=client,
                    RTSP_thread=Process(target=self.RTSP_connection, args=(url, ))
                    # RTSP_thread=threading.Thread(target=self.RTSP_connection, args=(url, ))
                )
                self.users[url].RTSP_thread.start()

    def RTSP_connection(self, user_url: str):
        print("%s RTSP thread started" % user_url)
        client = self.users[user_url].client
        while True:
            message = client.recv(self.CLIENT_BUFFER)
            packet = RTSPPacket.from_bytes(message)

            if packet.request_type == RTSPPacket.SETUP:
                if self.users[user_url].RTSP_STATUS == RTSPPacket.INVALID:
                    self.users[user_url].RTSP_STATUS = RTSPPacket.SETUP
                    last_port = self.PORT if len(self.RTPport) == 0 else self.RTPport[-1]
                    self.RTPport.append(last_port + 1)
                    self.RTPport.append(last_port + 2)

                    self.users[user_url].name = packet.name
                    self.users[user_url].RTP_recv_port = last_port + 1
                    self.users[user_url].RTP_send_port = last_port + 2
                    self.users[user_url].RTP_recv_thread = Process(target=self.RTP_recv, args=(user_url, ))
                    self.users[user_url].RTP_send_thread = Process(target=self.RTP_send, args=(user_url, ))
                    self.users[user_url].RTP_recv_thread.start()
                    self.users[user_url].RTP_send_thread.start()
                    
                    res = RTSPPacket(
                        request_type=packet.request_type,
                        cseq=packet.cseq,
                        ip=self.IP,
                        dst_port=last_port + 1,
                        name=packet.name
                    ).to_bytes()
                    client.send(res)
                else:
                    print(
                        "User %s is setup already, using %d as recv port, %d as send port" % (
                            user_url,
                            self.users[user_url].RTP_recv_port,
                            self.users[user_url].RTP_send_port
                    ))
            elif packet.request_type == RTSPPacket.PLAY:
                if self.users[user_url].RTSP_STATUS not in [RTSPPacket.INVALID, RTSPPacket.TEARDOWN]:
                    self.users[user_url].RTSP_STATUS = RTSPPacket.PLAY
                    res = RTSPPacket(
                        request_type=packet.request_type,
                        cseq=packet.cseq,
                        ip=self.IP,
                        session="none"
                    ).to_bytes()
                    client.send(res)
            elif packet.request_type == RTSPPacket.PAUSE:
                if self.users[user_url].RTSP_STATUS == RTSPPacket.PLAY:
                    self.users[user_url].RTSP_STATUS = RTSPPacket.PAUSE
                    res = RTSPPacket(
                        request_type=packet.request_type,
                        cseq=packet.cseq,
                        ip=self.IP,
                        session="none"
                    ).to_bytes()
                    client.send(res)
            elif packet.request_type == RTSPPacket.TEARDOWN:
                if self.users[user_url].RTSP_STATUS != RTSPPacket.INVALID:
                    self.users[user_url].RTSP_STATUS = RTSPPacket.INVALID
                    res = RTSPPacket(
                        request_type=packet.request_type,
                        cseq=packet.cseq,
                        ip=self.IP,
                        session="none"
                    ).to_bytes()
                    client.send(res)
                    self.users[user_url].RTP_recv_thread.terminate()
                    self.users[user_url].RTP_send_thread.terminate()

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
            if self.users[user_url].RTSP_STATUS not in [RTSPPacket.TEARDOWN, RTSPPacket.INVALID]:
                recv = bytes()
                while True:
                    try:
                        data, addr = recv_socket.recvfrom(1024)
                        if user_ip == addr[0] and user_port == addr[1]:
                            recv += data
                        else:
                            break
                        if recv.endswith(CameraStream.IMG_END.encode()):
                            break
                    except socket.timeout:
                        continue
                payload = RTPPacket.from_packet(recv).get_payload()
                self.users[user_url].current_display = payload["img"]
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
            if self.users[user_url].RTSP_STATUS not in [RTSPPacket.TEARDOWN, RTSPPacket.INVALID]:
                payload = {}
                for user in self.users:
                    if user != user_url and self.users[user].RTSP_STATUS in [RTSPPacket.PLAY]:
                        payload[user] = {
                            "name": self.users[user_url].name,
                            "current_display": self.users[user].current_display
                        }
                packet = RTPPacket(
                    RTPPacket.TYPE.IMG,
                    0,
                    0,
                    (str(payload) + CameraStream.IMG_END).encode()
                ).get_packet()
                send_socket.sendto(packet, (user_ip, user_port))
            time.sleep(self.SERVER_TIMEOUT / 1000.)
        