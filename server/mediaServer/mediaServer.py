import base64
from io import StringIO
import socket
from multiprocessing import Process
from threading import Thread
# from threading import Thread
import time
from tkinter import Frame
from typing import Dict
import json
import numpy as np
import cv2

from .user import User
from .RTSP_packet import RTSPPacket
from .RTP_packet import RTPPacket
from .camera_stream import CameraStream


class MediaServer():
    IP = "192.168.98.43"
    PORT = 3000
    CLIENT_BUFFER = 1024
    RTP_TIMEOUT = 1000  # ms
    SERVER_TIMEOUT = 100  # ms

    def __init__(self, maximum_user: int = 2):
        self.RTSPsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Use TCP as protocal
        self.RTPport = []  # Port for RTP connection
        self.users: Dict[str, User] = {}
        self.maximum_user = maximum_user
        self.testuser = User()
        # self.last_port = 3000

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
                    RTSP_thread=Thread(target=self.RTSP_connection, args=(url, self.RTPport, self.users))
                    # RTSP_thread=Thread(target=self.RTSP_connection, args=(url, ))
                )
                print(self.users.keys())
                self.users[url].RTSP_thread.setDaemon(True)
                self.users[url].RTSP_thread.start()

    def RTSP_connection(self, user_url: str, RTPport: list, users: Dict[str, User]):
        print("%s RTSP thread started" % user_url)
        client = users[user_url].client
        while True:
            message = client.recv(self.CLIENT_BUFFER)
            print("message")
            print(message)
            packet = RTSPPacket.from_bytes(message)

            if packet.request_type == RTSPPacket.SETUP:
                if users[user_url].RTSP_STATUS == RTSPPacket.INVALID:
                    users[user_url].RTSP_STATUS = RTSPPacket.SETUP
                    last_port = self.PORT if len(RTPport) == 0 else RTPport[-1]
                    RTPport.append(last_port + 1)
                    RTPport.append(last_port + 2)
                    print(RTPport)

                    users[user_url].name = packet.name
                    users[user_url].RTP_recv_port = last_port + 1
                    users[user_url].RTP_send_port = last_port + 2
                    users[user_url].RTP_recv_thread = Thread(target=self.RTP_recv, args=(user_url, users))
                    users[user_url].RTP_send_thread = Thread(target=self.RTP_send, args=(user_url, users))
                    users[user_url].RTP_recv_thread.setDaemon(True)
                    users[user_url].RTP_send_thread.setDaemon(True)
                    users[user_url].RTP_recv_thread.start()
                    users[user_url].RTP_send_thread.start()

                    print("%s with send port %d, recv port %d" % (user_url, last_port + 2, last_port + 1))
                    
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
                            users[user_url].RTP_recv_port,
                            users[user_url].RTP_send_port
                    ))
            elif packet.request_type == RTSPPacket.PLAY:
                if users[user_url].RTSP_STATUS not in [RTSPPacket.INVALID, RTSPPacket.TEARDOWN]:
                    print("Sending playing response")
                    users[user_url].RTSP_STATUS = RTSPPacket.PLAY
                    res = RTSPPacket(
                        request_type=packet.request_type,
                        cseq=packet.cseq,
                        ip=self.IP,
                        session="none"
                    ).to_bytes()
                    client.send(res)
            elif packet.request_type == RTSPPacket.PAUSE:
                if users[user_url].RTSP_STATUS == RTSPPacket.PLAY:
                    users[user_url].RTSP_STATUS = RTSPPacket.PAUSE
                    res = RTSPPacket(
                        request_type=packet.request_type,
                        cseq=packet.cseq,
                        ip=self.IP,
                        session="none"
                    ).to_bytes()
                    client.send(res)
            elif packet.request_type == RTSPPacket.TEARDOWN:
                if users[user_url].RTSP_STATUS != RTSPPacket.INVALID:
                    users[user_url].RTSP_STATUS = RTSPPacket.INVALID
                    res = RTSPPacket(
                        request_type=packet.request_type,
                        cseq=packet.cseq,
                        ip=self.IP,
                        session="none"
                    ).to_bytes()
                    client.send(res)

    def RTP_recv(self, user_url: str, users: Dict[str, User]):
        print("%s recv thread started" % user_url)
        user_addr = user_url.split(":")
        user_ip, user_port = user_addr[0], int(user_addr[1])
        ip = self.IP
        port = users[user_url].RTP_recv_port
        
        recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
        recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_socket.bind((ip, port))

        while True:
            print("RECV status: ", users[user_url].RTSP_STATUS)
            if users[user_url].RTSP_STATUS not in [RTSPPacket.TEARDOWN, RTSPPacket.INVALID]:
                recv = bytes()
                while True:
                    try:
                        data = recv_socket.recv(self.CLIENT_BUFFER)
                        recv += data
                        if recv.endswith(CameraStream.IMG_END):
                            print("end of image")
                            break
                    except socket.timeout:
                        continue
                payload = RTPPacket.from_packet(recv).get_payload()
                frame = base64.decodebytes(payload)
                print(type(frame))

                users[user_url].current_display = frame
            time.sleep(self.SERVER_TIMEOUT / 1000.)

    def RTP_send(self, user_url: str, users: Dict[str, User]):
        print("%s send thread started" % user_url)
        user_addr = user_url.split(":")
        user_ip, user_port = user_addr[0], int(user_addr[1])
        ip = self.IP
        port = users[user_url].RTP_send_port

        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
        send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        send_socket.bind((ip, port))
        send_socket.settimeout(self.RTP_TIMEOUT / 1000.)

        while True:
            if users[user_url].RTSP_STATUS not in [RTSPPacket.TEARDOWN, RTSPPacket.INVALID]:
                for user in users:
                    if user != user_url and users[user].RTSP_STATUS in [RTSPPacket.PLAY]:
                        frame = cv2.imencode('.jpg', users[user_url].current_display)[1]
                        data_frame = np.array(frame)
                        str_frame = data_frame.tostring()

                        packet = RTPPacket(
                            RTPPacket.TYPE.IMG,
                            0,
                            0,
                            str_frame
                        ).get_packet()
                
                        to_send = packet[:]
                        while to_send:
                            try:
                                send_socket.sendto(to_send[: self.CLIENT_BUFFER], (user_ip, user_port))
                            except socket.error as e:
                                print(f"failed to send rtp packet: {e}")
                                return
                            to_send = to_send[self.CLIENT_BUFFER :]
            time.sleep(self.SERVER_TIMEOUT / 1000.)
        