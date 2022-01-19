from re import S, T
import socket
from ssl import SSL_ERROR_INVALID_ERROR_CODE
from struct import pack
import threading
import time
from typing import Dict

from utils.RTSP_packet import RTSPPacket
from utils.RTP_packet import RTPPacket
from utils.camera_stream import CameraStream

class MediaClient():
    IP = "127.0.0.0"
    RTPport: int = None
    mediaServer: socket.socket
    RTSP_STATUS = RTSPPacket.INVALID
    RTP_IP = None
    RTP_send_port = None
    RTP_recv_port = None
    RTSP_Thread = None
    sendThread = None
    recvThread = None
    Cseq: int = 1
    SERVER_BUFFER = 1024
    RTP_TIMEOUT = 5  # ms
    SERVER_TIMEOUT = 100  # ms

    def __init__(self, port = 4000):
        self.mediaServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Use TCP as protocal
        self.RTPport = port  # Port for RTP connection
    
    def start(self):
        print(f'Media client starts at {self.IP}:{self.RTPport}')
        self.mediaServer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.mediaServer.connect((self.IP, self.RTPport))

    def Send_SETUP_request(self):
        if self.RTSP_STATUS == RTSPPacket.INVALID:
            req = RTSPPacket(request_type = RTSPPacket.SETUP, cseq = self.Cseq).to_bytes()
            self.mediaServer.send(req)
            while self.RTSP_STATUS != RTSPPacket.SETUP:
                message = self.mediaServer.recv(self.SERVER_BUFFER)
                packet = RTSPPacket.from_bytes(message)
                if packet.request_type == RTSPPacket.SETUP:
                    self.RTSP_STATUS = RTSPPacket.SETUP    # 1 : SETUP
                    self.RTP_send_port = packet.dst_port
                    self.RTP_IP = packet.ip
                    self.Cseq += 1
                    self.recvThread = threading.Thread(target = self.RTP_recv, args = (self.RTP_IP, self.RTP_recv_port))

    def Send_PLAY_request(self):
        if self.RTSP_STATUS == RTSPPacket.SETUP or self.RTSP_STATUS == RTSPPacket.PAUSE:
            req = RTPPacket(request_type = RTSPPacket.PLAY, cseq = self.Cseq).to_bytes()
            self.mediaServer.send(req)
            while self.RTSP_STATUS != RTSPPacket.PLAY:
                message = self.mediaServer.recv(self.SERVER_BUFFER)
                packet = RTSPPacket.from_bytes(message)
                if packet.request_type == RTPPacket.PLAY:
                    self.Cseq += 1
                    self.RTSP_STATUS = RTSPPacket.PLAY
                    self.sendThread = threading.Thread(target = self.RTP_send, args = (self.RTP_IP, self.RTP_send_port))

    def Send_PAUSE_request(self):
        if self.RTSP_STATUS == RTSPPacket.PLAY:
            req = RTPPacket(request_type = RTSPPacket.PAUSE, cseq = self.Cseq).to_bytes()
            self.mediaServer.send(req)
            while self.RTSP_STATUS != RTSPPacket.PAUSE:
                message = self.mediaServer.recv(self.SERVER_BUFFER)
                packet = RTSPPacket.from_bytes(message)
                if packet.request_type == RTPPacket.PAUSE:
                    self.RTSP_STATUS = RTSPPacket.PAUSE
                    self.Cseq += 1

    def Send_TEARDOWN_request(self):
        if self.RTSP_STATUS != RTSPPacket.TEARDOWN:
            req = RTPPacket(request_type = RTSPPacket.TEARDOWN, cseq = self.Cseq).to_bytes()
            self.mediaServer.send(req)
            while self.RTSP_STATUS != RTSPPacket.TEARDOWN:
                message = self.mediaServer.recv(self.SERVER_BUFFER)
                packet = RTSPPacket.from_bytes(message)
                if packet.request_type == RTSPPacket.TEARDOWN:
                    self.RTSP_STATUS = RTSPPacket.INVALID
                    self.RTP_send_port = None
                    self.RTP_IP = None
                    self.Cseq += 1

    def RTP_recv(self, send_ip, RTP_recv_port):
        print("receiving thread started")
        ip = send_ip
        port = RTP_recv_port
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
        send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        send_socket.connect((ip, port))
        send_socket.settimeout(self.RTP_TIMEOUT / 1000.)
        while self.RTSP_STATUS != RTSPPacket.INVALID and self.RTSP_STATUS != RTSPPacket.TEARDOWN:
            payload = {}
            packet = RTPPacket(
                RTPPacket.TYPE.IMG,
                int(time.time()),
                int(time.time()),
                bytes(payload)
            ).get_packet()
            send_socket.sendto(packet, (ip, port))

    def RTP_send(self, send_ip, RTP_send_port):
        print("sending thread started")
        ip = send_ip
        port = RTP_send_port
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
        send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        send_socket.connect((ip, port))
        send_socket.settimeout(self.RTP_TIMEOUT / 1000.)
        frame, _ = CameraStream.get_next_frame()
        while self.RTSP_STATUS == RTSPPacket.PLAY:
            payload = {
                "current_display": frame
            }
            packet = RTPPacket(
                RTPPacket.TYPE.IMG,
                int(time.time()),
                int(time.time()),
                bytes(payload)
            ).get_packet()
            send_socket.sendto(packet, (ip, port))
        
    
