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
        request_type: str,
        cseq: int,
        ip: str,
        session: str = None,
        dst_port: int = None,
        name: str = None,
    ):
        self.cseq = cseq
        self.session = session
        self.request_type = request_type
        self.dst_port = dst_port
        self.name = name,
        self.ip = ip

    def __str__(self) -> str:
        return (
            f"request_type: {self.request_type}"
            f"cseq: {self.cseq}"
            f"ip: {self.ip}"
            f"session: {self.session}"
            f"dst_port: {self.dst_port}"
            f"name: {self.name}"
        )

    @classmethod
    def from_bytes(cls, data: bytes):
        match = re.match(
            r"(?P<request_type>\w+) rtsp://(?P<ip>\S+) (?P<rtsp_version>RTSP/\d+.\d+)\r?\n"
            r"CSeq: (?P<cseq>\d+)\r?\n"
            r"(Transport: .*client_port=(?P<dst_port>\d+).*\r?\n)?"  # in case of SETUP request
            r"(Session: (?P<session>\d+)\r?\n)?"
            r"(a=name: (?P<name>)\r?\n)?",
            data.decode()
        )
        response = match.groupdict()
        if match is None:
            raise Exception(f"failed to parse request: {data}")
        req_type = response.get("request_type")
        if req_type not in [cls.SETUP, cls.PLAY, cls.PAUSE, cls.TEARDOWN]:
            raise Exception(f"Invalid request type: {req_type}")

        ip = response.get("ip")
        cseq = int(response.get("cseq"))
        name, dst_port, session = None, None, None
        if req_type == cls.SETUP:
            name = response.get("name")
            dst_port = int(response.get("dst_port"))
        else:
            session = response.get("session")

        return cls(
            request_type=req_type,
            cseq=cseq,
            ip=ip,
            session=session,
            name=name,
            dst_port=dst_port
        )

    def to_bytes(self):
        request_lines = [
            f"{self.request_type} rtsp://{self.ip} {self.RTSP_VERSION}",
            f"CSeq: {self.cseq}"
        ]

        if self.request_type == self.SETUP:
            if self.dst_port == None:
                raise Exception("Missing dst_port while request type is SETUP")
            if self.name == None:
                raise Exception("Missing name while request type is SETUP")
            request_lines.append(f"Transport: RTP/UDP;client_port={self.dst_port}")
            request_lines.append(f"a=name: {self.name}")
        else:
            request_lines.append(f"Session: {self.session}")
        request = "\r\n".join(request_lines) + "\r\n"
        return request.encode()
