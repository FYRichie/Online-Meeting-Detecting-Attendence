from re import S, T
import socket
from ssl import SSL_ERROR_INVALID_ERROR_CODE
from struct import pack
import threading
import time

from typing import Optional, List, Tuple
from PIL import Image
from io import BytesIO

from utils.RTSP_packet import RTSPPacket
from utils.RTP_packet import RTPPacket
from utils.camera_stream import CameraStream

class MediaClient():
    RTSP_port: int = None
    mediaServer: socket.socket
    RTSP_STATUS = RTSPPacket.INVALID
    RTSP_IP = None
    RTP_IP = None
    RTP_send_port = None
    RTP_recv_port = None
    RTSP_Thread = None
    sendThread = None
    recvThread = None
    _frame_buffer = None
    _current_frame_number = None
    Cseq: int = 1
    SERVER_BUFFER = 1024
    RTP_TIMEOUT = 5  # ms
    SERVER_TIMEOUT = 100  # ms

    def __init__(self, ip = "127.0.0.1", port = 4000):
        self.mediaServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Use TCP as protocal
        self.RTSP_port = port
        self.RTSP_IP = ip
        self._frame_buffer: List[Image.Image] = []
        self._current_frame_number = -1

    def get_next_frame(self) -> Optional[Tuple[Image.Image, int]]:
        if self._frame_buffer:
            self._current_frame_number += 1
            return self._frame_buffer.pop(0), self._current_frame_number
        return None
    
    def start(self):
        print(f'Media client starts at {self.RTSP_IP}:{self.RTSP_port}')
        self.mediaServer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.mediaServer.connect((self.RTSP_IP, self.RTSP_port))

    def Send_SETUP_request(self):
        if self.RTSP_STATUS == RTSPPacket.INVALID:
            req = RTSPPacket(
                            request_type = RTSPPacket.SETUP,
                            cseq = self.Cseq,
                            session = 0,
                            dst_port = self.RTSP_port,
                            name = "",
                            ip = self.RTSP_IP
                            ).to_bytes()
            self.mediaServer.send(req)
            print("RTSP packet send successfully")
            while self.RTSP_STATUS != RTSPPacket.SETUP:
                message = self.mediaServer.recv(self.SERVER_BUFFER)
                packet = RTSPPacket.from_bytes(message)
                print("received package")
                if packet.request_type == RTSPPacket.SETUP:
                    print("setup successful")
                    self.RTSP_STATUS = RTSPPacket.SETUP    # 1 : SETUP
                    self.RTP_send_port = packet.dst_port
                    self.RTP_IP = packet.ip
                    self.Cseq += 1
                    self.recvThread = threading.Thread(target = self.RTP_recv, args = (self.RTP_IP, self.RTP_recv_port))

    def Send_PLAY_request(self):
        if self.RTSP_STATUS == RTSPPacket.SETUP or self.RTSP_STATUS == RTSPPacket.PAUSE:
            req = RTSPPacket(
                            request_type = RTSPPacket.PLAY,
                            cseq = self.Cseq,
                            session = 0,
                            dst_port = self.RTSP_port,
                            name = "",
                            ip = self.RTSP_IP
                            ).to_bytes()
            self.mediaServer.send(req)
            while self.RTSP_STATUS != RTSPPacket.PLAY:
                message = self.mediaServer.recv(self.SERVER_BUFFER)
                packet = RTSPPacket.from_bytes(message)
                print(packet)
                if packet.request_type == RTSPPacket.PLAY:
                    self.Cseq += 1
                    self.RTSP_STATUS = RTSPPacket.PLAY
                    self.sendThread = threading.Thread(target = self.RTP_send, args = (self.RTP_IP, self.RTP_send_port))

    def Send_PAUSE_request(self):
        if self.RTSP_STATUS == RTSPPacket.PLAY:
            req = RTSPPacket(
                            request_type = RTSPPacket.PAUSE,
                            cseq = self.Cseq,
                            session = 0,
                            dst_port = self.RTSP_port,
                            name = "",
                            ip = self.RTSP_IP
                            ).to_bytes()
            self.mediaServer.send(req)
            while self.RTSP_STATUS != RTSPPacket.PAUSE:
                message = self.mediaServer.recv(self.SERVER_BUFFER)
                packet = RTSPPacket.from_bytes(message)
                if packet.request_type == RTSPPacket.PAUSE:
                    self.RTSP_STATUS = RTSPPacket.PAUSE
                    self.Cseq += 1

    def Send_TEARDOWN_request(self):
        if self.RTSP_STATUS != RTSPPacket.TEARDOWN:
            req = RTSPPacket(
                            request_type = RTSPPacket.TEARDOWN,
                            cseq = self.Cseq,
                            session = 0,
                            dst_port = self.RTSP_port,
                            name = "",
                            ip = self.RTSP_IP
                            ).to_bytes()
            self.mediaServer.send(req)
            while self.RTSP_STATUS != RTSPPacket.TEARDOWN:
                message = self.mediaServer.recv(self.SERVER_BUFFER)
                packet = RTSPPacket.from_bytes(message)
                if packet.request_type == RTSPPacket.TEARDOWN:
                    self.RTSP_STATUS = RTSPPacket.INVALID
                    self.RTP_send_port = None
                    self.RTP_recv_port = None
                    self.RTP_IP = None
                    self.RTSP_IP = None
                    self.Cseq += 1

    def RTP_recv(self, send_ip, RTP_recv_port):
        print("receiving thread started")
        ip = send_ip
        port = RTP_recv_port
        recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
        recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_socket.connect((ip, port))
        recv_socket.settimeout(self.RTP_TIMEOUT / 1000.)
        while self.RTSP_STATUS != RTSPPacket.INVALID and self.RTSP_STATUS != RTSPPacket.TEARDOWN:
            recv = bytes()
            while True:
                try:
                    data, addr = recv_socket.recvfrom(1024)
                    if ip == addr[0] and port == addr[1]:
                        recv += data
                    else:
                        break
                    if recv.endswith(CameraStream.IMG_END.encode()):
                        break
                except socket.timeout:
                    continue
            payload = RTPPacket.from_packet(recv).get_payload()
            frame = Image.open(BytesIO(payload))
            self._frame_buffer.append(frame)
            time.sleep(self.SERVER_TIMEOUT / 1000.)

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
                0,
                0,
                (str(payload) + CameraStream.IMG_END).encode()
            ).get_packet()
            send_socket.sendto(packet, (ip, port))