import socket
from threading import Thread
from time import sleep
from PIL import Image
from io import BytesIO

from .rtsp_packet import RTSPPacket
from .rtp_packet import RTPPacket
from .cameraStream import CameraStream

class RTPClient():
    RTSP_IP = "0.0.0.0"
    RTSP_PORT = 80

    DEFAULT_MAX_PACKET = 4096

    RTSP_SOFT_TIMEOUT = 100.  # ms

    def __init__(self):
        self.rtsp_socket: socket.socket = None
        self.rtp_socket: socket.socket = None
        self.rtp_recv_thread: Thread = None
        self.cur_seq_num = 0
        self.frame_buffer = []
        self.session_id = ""

        self.is_rtsp_connected = False
        self.is_receving_rtp = False

        self.rtp_send_port: int = None

    def connect_rtsp(self):
        if self.is_rtsp_connected:
            print("RTSP already connected")
            return
        print("Connecting to %s:%d" % (self.RTSP_IP, self.RTSP_PORT))
        self.rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.rtsp_socket.connect((self.RTSP_IP, self.RTSP_PORT))
        self.rtsp_socket.settimeout(self.RTSP_SOFT_TIMEOUT / 1000.)
        self.is_rtsp_connected = True

    def close_rtsp(self):
        if not self.is_rtsp_connected:
            print("RTSP is not connected")
            return
        self.rtsp_socket.close()
        self.is_rtsp_connected = False

    def _send_request(self, request_type=RTSPPacket.INVALID):
        if not self.is_rtsp_connected:
            raise Exception("RTSP connection is not established, run connect_rtsp()")
        request = RTSPPacket(
            request_type,
            self.cur_seq_num,
            self.rtp_send_port,
            self.session_id
        ).to_request()
        self.rtsp_socket.send(request)
        self.cur_seq_num += 1
        return self._get_response()

    def _get_response(self, size=DEFAULT_MAX_PACKET) -> RTSPPacket:
        recv = None
        while True:
            try:
                recv = self.rtsp_socket.recv(size)
                break
            except socket.timeout:
                continue
        response = RTSPPacket.from_response(recv)
        return response

    def send_setup_req(self):
        res = self._send_request(RTSPPacket.SETUP)
        self.start_rtp_recv_thread()
        self.session_id = res.session_id
        # self.rtp_send_port = int(res.payload)
        return res

    def send_play_req(self):
        res = self._send_request(RTSPPacket.PLAY)
        self.is_receving_rtp = True
        return res

    def send_pause_req(self):
        res = self._send_request(RTSPPacket.PAUSE)
        self.is_receving_rtp = False
        return res
    
    def send_teardown_req(self):
        res = self._send_request(RTSPPacket.TEARDOWN)
        self.is_receving_rtp = False
        self.is_rtsp_connected = False
        return res

    def recv_rtp_packet(self, size=DEFAULT_MAX_PACKET):
        recv = bytes()
        print("Waiting RTP packet...")
        while True:
            try:
                recv += self.rtp_socket.recv(size)
                if recv.endswith(CameraStream.IMG_END):
                    break
            except socket.timeout:
                continue
        return RTPPacket.from_packet(recv)

    def start_rtp_recv_thread(self):
        # TODO: display to frontend
        pass

    def handle_frame_send(self):
        self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtp_socket.connect((self.RTSP_IP, self.rtp_send_port))

    def get_next_frame(self):
        if len(self.frame_buffer) > 0:
            return self.frame_buffer.pop(0)
        return None

    @staticmethod
    def get_frame_from_packet(packet: RTPPacket):
        raw = packet.payload
        frame = Image.open(BytesIO(raw))
        return frame