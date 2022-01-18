from mediaServer import MediaServer

if __name__ == "__main__":
    mediaServer = MediaServer(
        ip="0.0.0.0",
        port=3000
    )
    mediaServer.start()