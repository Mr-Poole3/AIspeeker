import sys
import cv2
import requests
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PIL import Image, ImageDraw, ImageFont
import time
from mongodb import get_user  # 引入数据库操作函数

# CompreFace服务器配置
DOMAIN = 'http://localhost'
PORT = '8000'
API_KEY = 'f3dd0089-1396-4b69-8054-bfa6fee40d8f'
RECOGNITION_URL = f'{DOMAIN}:{PORT}/api/v1/recognition/recognize'

# 请求头
headers = {
    "x-api-key": API_KEY
}

# 加载支持中文的字体
font_path = "D:/AI/school/苹方字体.ttf"  # 请替换为支持中文的字体路径
font = ImageFont.truetype(font_path, 24) if font_path else ImageFont.load_default()

class RecognitionThread(QThread):
    recognition_result = pyqtSignal(dict)

    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.image = image

    def run(self):
        """在后台线程中调用 CompreFace API 进行人脸识别"""
        _, img_encoded = cv2.imencode('.jpg', self.image, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        files = {'file': ('image.jpg', img_encoded.tobytes(), 'image/jpeg')}

        try:
            response = requests.post(RECOGNITION_URL, headers=headers, files=files)
            response.raise_for_status()
            result = response.json()
            self.recognition_result.emit(result)
        except requests.RequestException:
            self.recognition_result.emit({})

class VideoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("实时人脸识别")
        self.layout = QVBoxLayout()
        self.label = QLabel()
        self.user_info_label = QLabel()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.user_info_label)
        self.setLayout(self.layout)

        self.cap = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        self.last_recognition_frame = None
        self.recognition_thread = None
        self.detected_faces = {}
        self.refresh_interval = 10

    def draw_chinese_text(self, image, text, position, color=(0, 255, 0)):
        """在图像上绘制中文字符"""
        image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(image_pil)
        draw.text(position, text, font=font, fill=color)
        return cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            print("无法获取摄像头帧")
            return

        if self.last_recognition_frame:
            for face in self.last_recognition_frame.get("result", []):
                box = face["box"]
                subjects = face["subjects"]
                x_min, y_min = box["x_min"], box["y_min"]
                x_max, y_max = box["x_max"], box["y_max"]
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

                if subjects:
                    subject = subjects[0]
                    name = subject["subject"]
                    similarity = subject["similarity"]
                    label = f"{name} ({similarity * 100:.2f}%)"
                    frame = self.draw_chinese_text(frame, label, (x_min, y_min - 30))

                    current_time = time.time()
                    last_update_time = self.detected_faces.get(name, 0)
                    if current_time - last_update_time > self.refresh_interval:
                        user_info = self.get_user_info(name)
                        if user_info:
                            self.display_user_info(user_info)
                            self.detected_faces[name] = current_time

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.label.setPixmap(QPixmap.fromImage(qt_image))

        if self.recognition_thread is None or not self.recognition_thread.isRunning():
            self.recognition_thread = RecognitionThread(frame)
            self.recognition_thread.recognition_result.connect(self.handle_recognition_result)
            self.recognition_thread.start()

    def get_user_info(self, name):
        """根据人脸识别的名字在 MongoDB 中查询用户信息"""
        user_info = get_user(name)
        if user_info:
            return {
                "username": user_info["username"],
                "email": user_info.get("email", "无"),
            }
        return None

    def display_user_info(self, user_info):
        """在界面上显示用户信息"""
        user_text = f"用户名: {user_info['username']}\n邮箱: {user_info['email']}\n"
        self.user_info_label.setText(user_text)

    def handle_recognition_result(self, result):
        """处理识别结果"""
        self.last_recognition_frame = result

    def closeEvent(self, event):
        self.cap.release()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VideoWindow()
    window.show()
    sys.exit(app.exec_())
