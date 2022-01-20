import cv2

class CameraStream():
    IMG_END = b'\xff\xd9'

    def __init__(self):
        self.cap = cv2.VideoCapture(0)

    def close(self):
        self.cap.release()
        
    def get_next_frame(self):
        if self.cap.isOpened():
            width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            frame_count = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
            
            ret, frame = self.cap.read()
            if not ret:
                raise RuntimeError("Camera fail to read.")
            return frame, width, height, fps, frame_count

if __name__ == "__main__":
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        cv2.imshow('frame', frame)
        if cv2.waitKey(5) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()