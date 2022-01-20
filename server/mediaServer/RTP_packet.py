class RTPPacket:
    HEADER_SIZE = 12
    VERSION = 0b10
    PADDING = 0b0
    EXTENSION = 0b0
    CONTRIBUTOR_COUNT = 0x0
    MARKER = 0b0
    SSRC = 0x00000000

    class TYPE:
        IMG = 0
        SOUND = 1
        BOTH = 2
        NONE = 3


    def __init__(
        self,
        payload_type: int = None,
        sequence_num: int = None,
        timestamp: int = None,
        payload: bytes = None
    ):
        self.payload = payload
        self.payload_type = payload_type
        self.sequence_num = sequence_num
        self.timestamp = timestamp

        zeroth_byte = (self.VERSION << 6) | (self.PADDING << 5) | (self.EXTENSION << 4) | self.CONTRIBUTOR_COUNT
        first_byte = (self.MARKER << 7) | self.payload_type
        second_byte = self.sequence_num >> 8
        third_byte = self.sequence_num & 0xFF
        fourth_to_seventh_bytes = [
            (self.timestamp >> shift) & 0xFF for shift in (24, 16, 8, 0)
        ]
        eigth_to_eleventh_bytes = [
            (self.SSRC >> shift) & 0xFF for shift in (24, 16, 8, 0)
        ]
        
        self.header = bytes((
            zeroth_byte,
            first_byte,
            second_byte,
            third_byte,
            *fourth_to_seventh_bytes,
            *eigth_to_eleventh_bytes
        ))

    @classmethod
    def from_packet(cls, packet: bytes):
        if len(packet) < cls.HEADER_SIZE:
            raise Exception("Packet length is shorter than RTP header size.")

        header = packet[: cls.HEADER_SIZE]
        payload = packet[cls.HEADER_SIZE :]

        payload_type = header[1] & 0x7F
        sequence_number = header[2] << 8 | header[3]
        timestamp = 0
        for i, b in enumerate(header[4:8]):
            timestamp = timestamp | b << (3 - i) * 8

        return cls(
            payload_type,
            sequence_number,
            timestamp,
            payload
        )
    
    def get_packet(self) -> bytes:
        return bytes((*self.header, *self.payload))

    def print_header(self):
        for i, by in enumerate(self.header[:8]):
            s = ' '.join(f"{by:08b}")
            print(s, end=' ' if i not in (3, 7) else '\n')

    def get_payload(self):
        return self.payload.decode("utf-8")