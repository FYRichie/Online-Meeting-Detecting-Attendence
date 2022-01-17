from flask import Flask

class WebServer():
    def __init__(self, name: str, ip: str = "0.0.0.0", port: str = 8080):
        self.app = Flask(name)
        self.ip = ip
        self.port = port
    
    def start(self):
        @self.app.route("/")
        def home():
            # return home page
            # index.html
            return

        @self.app.route("join")
        def join():
            # return joining page
            return

        self.app.run()