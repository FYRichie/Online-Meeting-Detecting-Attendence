import threading

class User():
    def __init__(
        self,
        name: str = None,
        current_display = None,
        client = None,
        is_setup: bool = False,
        is_playing: bool = False,
        RTSP_thread: threading.Thread = None,
        RTP_recv_port: int = None,
        RTP_send_port: int = None,
        RTP_recv_thread: threading.Thread = None,
        RTP_send_thread: threading.Thread = None
    ):
        self.name = name
        self.current_display = current_display
        self.client = client
        self.is_setup = is_setup
        self.is_playing = is_playing
        self.RTSP_thread = RTSP_thread
        self.RTP_recv_port = RTP_recv_port
        self.RTP_send_port = RTP_send_port
        self.RTP_recv_thread = RTP_recv_thread
        self.RTP_send_thread = RTP_send_thread
