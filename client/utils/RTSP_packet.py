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
        session_id: str = "",
        payload: dict = {}
    ):
        self.type = request_type
        self.seq_num = seq_num
        self.session_id = session_id
        self.payload = payload

    @classmethod
    def from_response(cls, response: bytes):
        match = re.match(
            r"(?P<rtsp_version>RTSP/\d+.\d+) 200 OK\r?\n"
            r"CSeq: (?P<sequence_number>\d+)\r?\n"
            r"Session: (?P<session_id>\d+)\r?\n",
            response.decode()
        )
        if match is None:
            raise Exception(f"failed to parse RTSP response: {response}")

        g = match.groupdict()
        sequence_number = g.get('sequence_number')
        session_id = g.get('session_id')
        try:
            sequence_number = int(sequence_number)
        except (ValueError, TypeError):
            raise Exception(f"failed to parse sequence number: {response}")

        if session_id is None:
            raise Exception(f"failed to parse session id: {response}")

        return cls(
            request_type=RTSPPacket.RESPONSE,
            sequence_number=sequence_number,
            session_id=session_id
        )