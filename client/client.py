from PyQt5.QtWidgets import QApplication
import sys

from lib import *

if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = ClientGUI()
    client.resize(800, 600)
    client.show()
    sys.exit(app.exec_())