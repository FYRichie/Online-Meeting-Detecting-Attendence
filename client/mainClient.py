from pydoc import cli
from PyQt5.QtWidgets import QApplication
from mediaClient import ClientWindow

if __name__ == "__main__":
    import sys
    app = QApplication([])
    client = ClientWindow("192.168.98.43", 3000)
    client.resize(1280, 720)
    client.setFixedSize(1280,720)
    client.show()
    sys.exit(app.exec_())