from PyQt5.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QMainWindow, QWidget, QPushButton
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import pyqtSignal, QTimer
import cv2

from .inc import *

class ClientGUI(QMainWindow):
    _update_image_signal = pyqtSignal()
    time_interval = 100  # ms

    def __init__(self):
        super().__init__()
        self.self_player = QLabel()
        self.other_player = []
        self.leave_button = QPushButton()
        # self.attending_label = QLabel()

        self.video_stream = CameraStream()
        self._update_image_signal.connect(self.update_image)
        self._update_image_timer = QTimer()
        self._update_image_timer.timeout.connect(self._update_image_signal.emit)
        self._update_image_timer.start(self.time_interval)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("I'm the best, I'm Daniel")

        self.leave_button.setEnabled(True)
        self.leave_button.setText("Leave")
        self.leave_button.clicked.connect(self.handle_leave)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.addWidget(self.leave_button)

        layout = QVBoxLayout()
        layout.addWidget(self.self_player)
        layout.addLayout(control_layout)

        central_widget.setLayout(layout)

    def update_image(self):
        frame, width, height, fps, _ = self.video_stream.get_next_frame()
        width = int(width // 2)
        height = int(height // 2)
        frame = self.processcv2(frame, width, height)
        if frame is not None:
            img = QImage(frame.data.tobytes(), width, height, QImage.Format_RGB888)
            pix = QPixmap.fromImage(img)
            self.self_player.setPixmap(pix)

    def handle_leave(self):
        self.leave_button.setEnabled(False)
        exit(0)

    def processcv2(self, img, width, height):
        img = cv2.resize(img, (width, height))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return img