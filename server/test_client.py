import socket

if __name__ == "__main__":
    HOST = "0.0.0.0"
    PORT = 3000

    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Redirecting
    server_addr = (HOST, PORT)
    out_data = input("Input udp message: ")
    client.sendto(out_data.encode(), server_addr)

    in_data, addr = client.recvfrom(1024)
    print("Received data: " + in_data.decode())
    PORT = int(in_data.decode())

    server_addr = (HOST, PORT)
    while True:
        out_data = input("Input udp message: ")
        client.sendto(out_data.encode(), server_addr)

        in_data, addr = client.recvfrom(1024)
        print("Received data: " + in_data.decode())