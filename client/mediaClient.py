from PyQt5.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout
from PyQt5.QtWidgets import QMainWindow, QWidget, QPushButton
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import pyqtSignal, QTimer, Qt
from PIL.ImageQt import ImageQt
import cv2

from client import MediaClient as Client
from utils.camera_stream import CameraStream


class ClientWindow(QMainWindow):
    _update_image_signal = pyqtSignal()
    time_interval = 100
    def __init__(
            self,
            host_address: str,
            host_port: int,
            parent=None):
        super(ClientWindow, self).__init__(parent)
        self.video_player = QLabel()
        self.video_player2 = QLabel()
        self.camera = CameraStream()

        self.video_player2.setAlignment(Qt.AlignBottom)
        self.setup_button = QPushButton()
        
        self.resize_button = QPushButton()
        
        self.play_button = QPushButton()
        self.pause_button = QPushButton()
        self.tear_button = QPushButton()
        self.error_label = QLabel()

        self._media_client = Client(host_address, host_port)
        self._media_client.start()
        self._update_image_signal.connect(self.update_image)
        self._update_image_timer = QTimer()
        self._update_image_timer.timeout.connect(self._update_image_signal.emit)
        self._update_image_timer.start(self.time_interval)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Client")

        self.setup_button.setEnabled(True)
        self.setup_button.setText('Setup')
        self.setup_button.clicked.connect(self.handle_setup)
        # self.setup_button.setGeometry(0,0,200,100)
    
        self.resize_button.setEnabled(True)
        self.resize_button.setText('test')
        self.resize_button.clicked.connect(self.handle_resize)

        self.play_button.setEnabled(False)
        self.play_button.setText('Play')
        self.play_button.clicked.connect(self.handle_play)

        self.pause_button.setEnabled(False)
        self.pause_button.setText('Pause')
        self.pause_button.clicked.connect(self.handle_pause)

        self.tear_button.setEnabled(False)
        self.tear_button.setText('Teardown')
        self.tear_button.clicked.connect(self.handle_teardown)

        self.error_label.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Maximum)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        control_layout = QVBoxLayout()
        control_layout.setContentsMargins(50, 0, 20, 10)
        # control_layout.addWidget(self.video_player)
        control_layout.addWidget(self.video_player)
        control_layout.addWidget(self.setup_button)
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.tear_button)
        control_layout.addWidget(self.resize_button)
        
        
        layout = QHBoxLayout()
        layout.setContentsMargins(50, 0, 0, 20)
        layout.addWidget(self.video_player2)
        # layout.addLayout(left_layout)
        layout.addLayout(control_layout)   
        # layout.addWidget(self.error_label)

        central_widget.setLayout(layout)

    def update_image(self):
        # print(len(self._media_client._frame_buffer))
        frame_c, width_c, height_c, fps, _ = self.camera.get_next_frame()
        width_c = int(width_c)
        height_c = int(height_c)
        # print(width_c)
        # print(height_c)
        frame_real = self.processcv2(frame_c, width_c, height_c)
        if frame_real is not None:
            img = QImage(frame_real.data.tobytes(), width_c, height_c, QImage.Format_RGB888)
            pix_c = QPixmap.fromImage(img)
            self.video_player.setPixmap(pix_c)


        # if not self._media_client.is_receiving_rtp:
        #     print(len(self._media_client._frame_buffer))
        #     return
        # print(len(self._media_client._frame_buffer))
        frame = self._media_client.get_next_frame()
        if frame is not None:
            pix = QPixmap.fromImage(ImageQt(frame[0]).copy())
            # print(pix.height())
            # print(pix.width())
            ori_h = pix.height()
            ori_w = pix.width()
            h2 = self.video_player2.height()
            w2 = self.video_player2.width()
            if (h2/ori_h)>(w2/ori_w):
                pix_sca2 = pix.scaledToWidth(w2)
            else:
                pix_sca2 = pix.scaledToHeight(h2)
            self.video_player2.setPixmap(pix_sca2)

    def handle_setup(self):
        self._media_client.Send_SETUP_request()
        self.setup_button.setEnabled(False)
        self.play_button.setEnabled(True)
        self.tear_button.setEnabled(True)
        # self._update_image_timer.start(1000//VideoStream.DEFAULT_FPS)

    def handle_resize(self):
        he = self.video_player.height()
        we = self.video_player.width()
        print("video height :", he)
        print("video width :",we)
        he2 = self.video_player2.height()
        we2 = self.video_player2.width()
        print("video height2 :", he2)
        print("video width2 :",we2)
        # scale1 = self.video_player.pixmap.sca


    def handle_play(self):
        self._media_client.Send_PLAY_request()
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(True)

    def handle_pause(self):
        self._media_client.Send_PAUSE_request()
        self.pause_button.setEnabled(False)
        self.play_button.setEnabled(True)

    def handle_teardown(self):
        self._media_client.Send_TEARDOWN_request()
        self.setup_button.setEnabled(True)
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        # exit(0)

    def handle_error(self):
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.tear_button.setEnabled(False)
        self.error_label.setText(f"Error: {self.media_player.errorString()}")
    
   
    def processcv2(self, img, width, height):
        img = cv2.resize(img, (width, height))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return img