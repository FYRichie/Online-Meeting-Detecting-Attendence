from re import T
import socket
import threading
import time
from typing import Dict

from .user import User
from utils.RTSP_packet import RTSPPacket
from utils.RTP_packet import RTPPacket
from utils.camera_stream import CameraStream

class MediaClient():
    IP = "127.0.0.0"
    RTPport: int = None
    mediaServer: socket.socket
    RTSP_SETUP = False
    RTP_IP = None
    RTP_send_port = None
    RTP_recv_port = None
    sendThread = None
    recvThread = None
    Cseq: int = 1
    CLIENT_BUFFER = 1024
    RTP_TIMEOUT = 5  # ms
    SERVER_TIMEOUT = 100  # ms

    def __init__(self, port = 4000):
        self.mediaServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Use TCP as protocal
        self.RTPport = port  # Port for RTP connection
    
    def start(self):
        print(f'Media client start at {self.IP}:{self.RTPport}')
        self.mediaServer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.mediaServer.bind((self.IP, self.RTPport))

    def Send_SETUP_request(self):
        while True:
            req = RTSPPacket(request_type="SETUP", cseq=self.Cseq).to_bytes()
            self.mediaServer.send(req)
            while True:
                message = self.mediaServer.recv(self.CLIENT_BUFFER)
                packet = RTSPPacket.from_bytes(message)
                if packet.request_type == RTSPPacket.SETUP:
                    self.RTSP_SETUP = True
                    self.RTP_send_port = packet.dst_port
                    self.RTP_IP = packet.ip
                    self.sendThread = threading.Thread(target = self.RTP_send, args = (self.RTP_IP, self.RTP_send_port, ))
                    self.recvThread = threading.Thread(target = self.RTP_recv, args = (self.RTP_IP, self.RTP_recv_port, ))

    def RTP_recv(self, RTP_IP, TRP_recv_port):
        print("recv thread started")
        ip = RTP_IP
        port = TRP_recv_port
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
            time.sleep(self.SERVER_TIMEOUT / 1000.)

    def RTP_send(self, send_ip, RTP_send_port):
        print("sending thread started")
        ip = send_ip
        port = RTP_send_port
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
        send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        send_socket.bind((ip, port))
        send_socket.settimeout(self.RTP_TIMEOUT / 1000.)

        while True:
            payload = {}
            packet = RTPPacket(
                RTPPacket.TYPE.IMG,
                int(time.time()),
                int(time.time()),
                bytes(payload)
            ).get_packet()
            send_socket.sendto(packet, (ip, port))
        