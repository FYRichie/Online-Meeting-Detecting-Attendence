from inc.webServer import WebServer

if __name__ == "__main__":
    webserver = WebServer(
        name=__name__,
        ip="0.0.0.0",
        port=4000
    )

    webserver.start()