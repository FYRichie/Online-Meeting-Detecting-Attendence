import socket
import threading
import time
from turtle import width
import json
import cv2
import numpy as np
import base64

from typing import Optional, List, Tuple
from PIL import Image
from io import StringIO

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
    _frame_buffer_send = None
    _current_frame_number = None
    Cseq: int = 1
    SERVER_BUFFER = 1024
    RTP_TIMEOUT = 100  # ms
    SERVER_TIMEOUT = 100  # ms

    def __init__(self, ip = "127.0.0.1", port = 4000):
        self.mediaServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Use TCP as protocal
        self.RTSP_port = port
        self.RTSP_IP = ip
        self._frame_buffer: List[Image.Image] = []
        self._frame_buffer_send: List[Image.Image] =[]
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
            print("req:",req)
            print("status",self.RTSP_STATUS)
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
                    self.RTP_recv_port = packet.dst_port + 1
                    self.RTP_IP = packet.ip
                    self.Cseq += 1
                    self.recvThread = threading.Thread(target = self.RTP_recv, args = (self.RTP_IP, self.RTP_recv_port))
                    self.recvThread.setDaemon(True)
                    self.recvThread.start()

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
            print("req:",req)
            self.mediaServer.send(req)
            print("status",self.RTSP_STATUS)
            while self.RTSP_STATUS != RTSPPacket.PLAY:
                print("Waiting for playing response")
                message = self.mediaServer.recv(self.SERVER_BUFFER)
                packet = RTSPPacket.from_bytes(message)
                print("!!!!!!!!!!!!!!!!!", packet)
                if packet.request_type == RTSPPacket.PLAY:
                    self.Cseq += 1
                    self.RTSP_STATUS = RTSPPacket.PLAY
                    self.sendThread = threading.Thread(target = self.RTP_send, args = (self.RTP_IP, self.RTP_send_port))
                    self.sendThread.setDaemon(True)
                    self.sendThread.start()

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
            print("req:",req)
            print("status",self.RTSP_STATUS)
            self.mediaServer.send(req)
            while self.RTSP_STATUS != RTSPPacket.PAUSE:
                message = self.mediaServer.recv(self.SERVER_BUFFER)
                packet = RTSPPacket.from_bytes(message)
                if packet.request_type == RTSPPacket.PAUSE:
                    self.RTSP_STATUS = RTSPPacket.PAUSE
                    self.Cseq += 1

    def Send_TEARDOWN_request(self):
        if self.RTSP_STATUS not in [RTSPPacket.TEARDOWN, RTSPPacket.INVALID]:
            req = RTSPPacket(
                            request_type = RTSPPacket.TEARDOWN,
                            cseq = self.Cseq,
                            session = 0,
                            dst_port = self.RTSP_port,
                            name = "",
                            ip = self.RTSP_IP
                            ).to_bytes()
            print("req:",req)
            print("status",self.RTSP_STATUS)
            self.mediaServer.send(req)
            while self.RTSP_STATUS != RTSPPacket.TEARDOWN:
                message = self.mediaServer.recv(self.SERVER_BUFFER)
                packet = RTSPPacket.from_bytes(message)
                if packet.request_type == RTSPPacket.TEARDOWN:
                    self.RTSP_STATUS = RTSPPacket.TEARDOWN
                    self.RTP_send_port = None
                    self.RTP_recv_port = None
                    self.RTP_IP = None
                    self.RTSP_IP = None
                    self.Cseq += 1
            self.RTSP_STATUS = RTSPPacket.INVALID

    def RTP_recv(self, send_ip, RTP_recv_port):
        print("receiving thread started")
        ip = send_ip
        port = RTP_recv_port
        print(type(ip), ip)
        print(type(port), port)
        recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
        recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_socket.settimeout(self.RTP_TIMEOUT / 1000.)
        while self.RTSP_STATUS != RTSPPacket.INVALID and self.RTSP_STATUS != RTSPPacket.TEARDOWN:
            recv = bytes()
            while True:
                try:
                    data = recv_socket.recv(self.SERVER_BUFFER)
                    recv += data

                    if recv.endswith(CameraStream.IMG_END):
                        break
                except socket.timeout:
                    continue
            # recv = recv_socket.recv(self.SERVER_BUFFER)
            payload = RTPPacket.from_packet(recv).get_payload()
            frame = base64.decodebytes(payload)
            self._frame_buffer.append(frame)
            time.sleep(self.SERVER_TIMEOUT / 1000.)

    def RTP_send(self, send_ip, RTP_send_port):
        print("sending thread started")
        ip = send_ip
        port = RTP_send_port
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
        send_socket.settimeout(self.RTP_TIMEOUT / 1000.)
        frame, _, _, _, _ = CameraStream().get_next_frame()

        while self.RTSP_STATUS == RTSPPacket.PLAY:
            frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_AREA)
            frame = cv2.imencode(".jpg", frame)[1]
            data_frame = np.array(frame)
            str_frame = data_frame.tostring()

            packet = RTPPacket(
                RTPPacket.TYPE.IMG,
                0,
                0,
                str_frame
            ).get_packet()
            print(len(packet))
            to_send = packet[:]
            while to_send:
                try:
                    send_socket.sendto(to_send[: self.SERVER_BUFFER], (ip, port))
                except socket.error as e:
                    print(f"failed to send rtp packet: {e}")
                    return
                to_send = to_send[self.SERVER_BUFFER :]
            time.sleep(2 * self.SERVER_TIMEOUT / 1000.)
