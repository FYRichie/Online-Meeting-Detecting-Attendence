import socket

from utils.RTSP_packet import RTSPPacket
from utils.RTP_packet import RTPPacket

if __name__ == "__main__":
    ip = "127.0.0.1"
    rtsp_port = 3000
    rtp_port = None

    rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    rtsp_socket.connect((ip, rtsp_port))