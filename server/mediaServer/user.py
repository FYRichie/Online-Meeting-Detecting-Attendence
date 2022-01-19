from multiprocessing import Process

from .RTSP_packet import RTSPPacket

class User():
    def __init__(
        self,
        name: str = None,
        current_display = None,
        client = None,
        RTSP_thread: Process = None,
        RTP_recv_port: int = None,
        RTP_send_port: int = None,
        RTP_recv_thread: Process = None,
        RTP_send_thread: Process = None
    ):
        self.name = name
        self.current_display = current_display
        self.client = client
        self.RTSP_STATUS = RTSPPacket.INVALID
        self.RTSP_thread = RTSP_thread
        self.RTP_recv_port = RTP_recv_port
        self.RTP_send_port = RTP_send_port
        self.RTP_recv_thread = RTP_recv_thread
        self.RTP_send_thread = RTP_send_thread
