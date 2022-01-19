import socket

from RTSP_packet import RTSPPacket
from RTP_packet import RTPPacket

if __name__ == "__main__":
    ip = "127.0.0.1"
    rtsp_port = 3000
    rtp_port = None

    rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    rtsp_socket.connect((ip, rtsp_port))

    cseq = 1
    init_packet = RTSPPacket(RTSPPacket.SETUP, cseq, ip, dst_port=4000, name="Daniel")
    print(init_packet)
    print(len(init_packet.to_bytes()))
    rtsp_socket.send(init_packet.to_bytes())

    while True:
        recv_packet = RTSPPacket.from_bytes(rtsp_socket.recv(1024))
        print(recv_packet)
        mes = input()
        cseq += 1
        rtsp_socket.send(RTSPPacket(
            request_type=mes,
            cseq=cseq,
            ip=ip,
            session="lalalala"
        ).to_bytes())