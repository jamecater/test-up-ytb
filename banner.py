from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QGroupBox, QComboBox, QLineEdit, QLabel, QProgressBar, QStatusBar
)
from PyQt5.QtCore import Qt

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard Demo")
        self.setGeometry(100, 100, 1100, 700)
        self.setStyleSheet("""
            QWidget { background: #23272e; color: #f8f8f2; }
            QGroupBox { border: 1.5px solid #44475a; border-radius: 8px; margin-top: 10px; }
            QTableWidget { background: #282a36; color: #f8f8f2; border: 1px solid #44475a; }
            QPushButton { background: #6272a4; color: #fff; border-radius: 5px; padding: 6px 12px; }
            QPushButton:hover { background: #50fa7b; color: #23272e; }
        """)

        main_layout = QVBoxLayout(self)

        # Account panel
        account_group = QGroupBox("Account")
        account_layout = QVBoxLayout()
        self.account_table = QTableWidget(1, 4)
        self.account_table.setHorizontalHeaderLabels(["Name", "Open", "Edit", "Delete"])
        self.account_table.setItem(0, 0, QTableWidgetItem("DHB Tools"))
        for i, icon in enumerate(["Open", "Edit", "Delete"], 1):
            btn = QPushButton(icon)
            self.account_table.setCellWidget(0, i, btn)
        account_layout.addWidget(self.account_table)
        account_group.setLayout(account_layout)

        # Setting panel
        setting_group = QGroupBox("Setting")
        setting_layout = QVBoxLayout()
        setting_layout.addWidget(QLabel("Type:"))
        setting_layout.addWidget(QComboBox())
        setting_layout.addWidget(QLabel("Input:"))
        setting_layout.addWidget(QLineEdit())
        setting_layout.addWidget(QLabel("Save to:"))
        setting_layout.addWidget(QLineEdit())
        setting_layout.addWidget(QPushButton("Start"))
        setting_group.setLayout(setting_layout)

        # Top layout
        top_layout = QHBoxLayout()
        top_layout.addWidget(account_group, 2)
        top_layout.addWidget(setting_group, 3)
        main_layout.addLayout(top_layout)

        # Video table
        self.video_table = QTableWidget(10, 10)
        self.video_table.setHorizontalHeaderLabels([
            "#", "Caption", "Privacy", "Schedule", "Account", "Status",
            "Download", "Render", "Upload", "Edit", "Delete"
        ])
        main_layout.addWidget(self.video_table)

        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready")
        main_layout.addWidget(self.status_bar)

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())