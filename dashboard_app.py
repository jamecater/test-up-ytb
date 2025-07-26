import sys
import time
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QGroupBox, QComboBox, QLineEdit, QLabel, QStatusBar,
    QTextEdit, QCheckBox
)
from PyQt5.QtCore import Qt

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Shorts Uploader - Dashboard")
        self.setGeometry(100, 100, 1100, 700)
        self.setStyleSheet("""
            QWidget { background: #23272e; color: #f8f8f2; }
            QGroupBox { border: 1.5px solid #44475a; border-radius: 8px; margin-top: 10px; }
            QTableWidget { background: #282a36; color: #f8f8f2; border: 1px solid #44475a; }
            QPushButton { background: #6272a4; color: #fff; border-radius: 5px; padding: 6px 12px; }
            QPushButton:hover { background: #50fa7b; color: #23272e; }
            QComboBox, QLineEdit { background: #44475a; color: #f8f8f2; border-radius: 3px; padding: 4px; }
            QTextEdit { background: #282a36; color: #f8f8f2; border: 1px solid #44475a; }
            QCheckBox { font-size: 15px; }
        """)

        main_layout = QVBoxLayout(self)

        # Account panel
        account_group = QGroupBox("Account")
        account_layout = QVBoxLayout()
        self.account_table = QTableWidget(1, 4)
        self.account_table.setHorizontalHeaderLabels(["Name", "Open", "Edit", "Delete"])
        self.account_table.setItem(0, 0, QTableWidgetItem("Tâm Kem"))
        for i, icon in enumerate(["Open", "Edit", "Delete"], 1):
            btn = QPushButton(icon)
            self.account_table.setCellWidget(0, i, btn)
        account_layout.addWidget(self.account_table)
        account_group.setLayout(account_layout)

        # Setting panel
        setting_group = QGroupBox("Setting")
        setting_layout = QVBoxLayout()

        # Chế độ chạy
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Chạy bằng API", "Chạy bằng yt_dlp"])
        setting_layout.addWidget(QLabel("Chế độ lấy video:"))
        setting_layout.addWidget(self.mode_combo)

        # Quản lý API key
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Nhập API key mới...")
        self.btn_add_api = QPushButton("Thêm API Key")
        self.btn_add_api.clicked.connect(self.add_api_key)
        api_hbox = QHBoxLayout()
        api_hbox.addWidget(self.api_input)
        api_hbox.addWidget(self.btn_add_api)
        setting_layout.addLayout(api_hbox)
        self.api_list = QComboBox()
        setting_layout.addWidget(self.api_list)

        # Bật/tắt sọc đen
        self.chk_black_bar = QCheckBox("Bật sọc đen cắt ngang màn hình")
        self.chk_black_bar.setChecked(True)
        setting_layout.addWidget(self.chk_black_bar)

        # Nút Start/Stop
        self.btn_start = QPushButton("Bắt đầu")
        self.btn_stop = QPushButton("Dừng lại")
        self.btn_stop.setEnabled(False)
        self.btn_start.clicked.connect(self.start_process)
        self.btn_stop.clicked.connect(self.stop_process)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        setting_layout.addLayout(btn_layout)

        setting_group.setLayout(setting_layout)

        # Top layout
        top_layout = QHBoxLayout()
        top_layout.addWidget(account_group, 2)
        top_layout.addWidget(setting_group, 3)
        main_layout.addLayout(top_layout)

        # Video table
        self.video_table = QTableWidget(10, 11)
        self.video_table.setHorizontalHeaderLabels([
            "#", "Caption", "Privacy", "Schedule", "Account", "Status",
            "Download", "Render", "Upload", "Edit", "Delete"
        ])
        main_layout.addWidget(self.video_table)

        # Log area
        main_layout.addWidget(QLabel("Log:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        main_layout.addWidget(self.log_area)

        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready")
        main_layout.addWidget(self.status_bar)

        # Data
        self.api_keys = []
        self.running = False
        self.worker_thread = None

    def add_api_key(self):
        key = self.api_input.text().strip()
        if key and key not in [self.api_list.itemText(i) for i in range(self.api_list.count())]:
            self.api_list.addItem(key)
            self.api_input.clear()
            self.log(f"Thêm API key: {key}")
        else:
            self.log("API key đã tồn tại hoặc rỗng.")

    def start_process(self):
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.running = True
        mode = self.mode_combo.currentText()
        api_keys = [self.api_list.itemText(i) for i in range(self.api_list.count())]
        black_bar = self.chk_black_bar.isChecked()
        self.log(f"Chế độ: {mode}, API keys: {api_keys}, Sọc đen: {black_bar}")
        if mode == "Chạy bằng API":
            self.worker_thread = threading.Thread(target=self.worker_api, args=(api_keys, black_bar), daemon=True)
        else:
            self.worker_thread = threading.Thread(target=self.worker_ytdlp, args=(black_bar,), daemon=True)
        self.worker_thread.start()

    def stop_process(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.running = False
        self.log("Đã dừng quá trình upload.")

    def log(self, msg):
        self.log_area.append(msg)

    # Worker mô phỏng cho chế độ API
    def worker_api(self, api_keys, black_bar):
        idx = 0
        quota_exceeded = False
        while self.running:
            if not api_keys:
                self.log("Không có API key nào!")
                break
            key = api_keys[idx % len(api_keys)]
            self.log(f"Đang dùng API key: {key}")
            # Mô phỏng quotaExceeded
            if quota_exceeded:
                self.log(f"API key {key} quota exceeded, chuyển key tiếp theo...")
                idx += 1
                quota_exceeded = False
                time.sleep(1)
                continue
            # Mô phỏng xử lý video
            for i in range(3):
                if not self.running: return
                self.log(f"Đang xử lý video {i+1} (API)... Sọc đen: {black_bar}")
                time.sleep(2)
            # Mô phỏng quotaExceeded sau 1 vòng
            quota_exceeded = True
        self.log("Kết thúc worker API.")

    # Worker mô phỏng cho chế độ yt_dlp
    def worker_ytdlp(self, black_bar):
        for i in range(5):
            if not self.running: return
            self.log(f"Đang xử lý video {i+1} (yt_dlp)... Sọc đen: {black_bar}")
            time.sleep(2)
        self.log("Kết thúc worker yt_dlp.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
