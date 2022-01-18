import re

class RTSPPacket:
    RTSP_VERSION = "RTSP/1.0"
    INVALID = -1
    SETUP = "SETUP"
    PLAY = "PLAY"
    PAUSE = "PAUSE"
    TEARDOWN = "TEARDOWN"
    RESPONSE = "RESPONSE"

    def __init__(
        self,
        request_type,
        seq_num: int = None,
        dst_port: int = None,
        session_id: str = "",
        payload: str = ""
    ):
        self.request_type = request_type
        self.seq_num = seq_num
        self.dst_port = dst_port
        self.session_id = session_id
        self.payload = payload

    @classmethod
    def from_response(cls):
        pass