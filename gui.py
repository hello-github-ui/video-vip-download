#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QComboBox, QLabel, QTextEdit,
    QGroupBox, QGridLayout, QProgressBar, QMessageBox,
    QShortcut, QClipboard
)
from PyQt5.QtGui import QIcon, QFont, QKeySequence
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from video_parser import VideoParser

class DownloadThread(QThread):
    """
    视频下载线程
    用于在后台执行下载任务，避免阻塞UI
    """
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    
    def __init__(self, video_url, output_path, quality):
        super().__init__()
        self.video_url = video_url
        self.output_path = output_path
        self.quality = quality
        self.parser = VideoParser()
    
    def run(self):
        """执行下载任务"""
        result = self.parser.download_video(self.video_url, self.output_path, self.quality)
        self.finished.emit(result)

class MainWindow(QMainWindow):
    """
    主窗口类
    提供视频解析工具的图形界面
    """
    
    def __init__(self):
        super().__init__()
        self.parser = VideoParser()
        self.download_thread = None
        
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('🎥 henVIP 视频解析工具')
        self.setGeometry(100, 100, 700, 550)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        self.create_url_input()
        self.create_api_selector()
        self.create_action_buttons()
        self.create_result_area()
        self.create_quick_links()
        self.create_download_section()
        
        self.setStyleSheet(self.get_style_sheet())
    
    def create_url_input(self):
        """创建URL输入区域"""
        url_group = QGroupBox('视频链接')
        url_layout = QHBoxLayout(url_group)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('请输入视频链接，支持腾讯视频、优酷、哔哩哔哩、爱奇艺等...')
        self.url_input.setFont(QFont('微软雅黑', 12))
        self.url_input.returnPressed.connect(self.on_parse_click)
        
        self.paste_btn = QPushButton('粘贴')
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.paste_btn)
        
        self.main_layout.addWidget(url_group)
    
    def create_api_selector(self):
        """创建解析线路选择器"""
        api_group = QGroupBox('解析线路')
        api_layout = QHBoxLayout(api_group)
        
        self.api_combo = QComboBox()
        self.api_combo.setFont(QFont('微软雅黑', 12))
        
        apis = self.parser.get_all_apis()
        for key, api in apis.items():
            status = ' ✅' if api['status'] == 'active' else ' ❌'
            note = f" ({api['note']})" if api['note'] else ''
            self.api_combo.addItem(f"{key}. {api['name']}{status}{note}", key)
        
        self.api_combo.setCurrentText('b. 夜幕解析 ✅ (推荐使用)')
        
        api_layout.addWidget(QLabel('选择解析线路:'))
        api_layout.addWidget(self.api_combo)
        
        self.main_layout.addWidget(api_group)
    
    def create_action_buttons(self):
        """创建操作按钮"""
        btn_layout = QHBoxLayout()
        
        self.parse_btn = QPushButton('🔍 开始解析')
        self.parse_btn.setFont(QFont('微软雅黑', 12))
        self.parse_btn.clicked.connect(self.on_parse_click)
        
        self.open_btn = QPushButton('🌐 在浏览器打开')
        self.open_btn.setFont(QFont('微软雅黑', 12))
        self.open_btn.clicked.connect(self.on_open_browser)
        self.open_btn.setEnabled(False)
        
        self.copy_btn = QPushButton('📋 复制链接')
        self.copy_btn.setFont(QFont('微软雅黑', 12))
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.copy_btn.setEnabled(False)
        
        btn_layout.addWidget(self.parse_btn)
        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.copy_btn)
        
        self.main_layout.addLayout(btn_layout)
    
    def create_result_area(self):
        """创建结果显示区域"""
        result_group = QGroupBox('解析结果')
        result_layout = QVBoxLayout(result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont('微软雅黑', 11))
        self.result_text.setPlaceholderText('解析结果将显示在这里...')
        
        result_layout.addWidget(self.result_text)
        
        self.main_layout.addWidget(result_group)
    
    def create_quick_links(self):
        """创建快速访问按钮"""
        quick_group = QGroupBox('快速访问')
        quick_layout = QGridLayout(quick_group)
        
        platforms = [
            ('腾讯视频', 'https://v.qq.com'),
            ('优酷', 'https://www.youku.com'),
            ('哔哩哔哩', 'https://www.bilibili.com'),
            ('爱奇艺', 'https://www.iqiyi.com'),
            ('芒果TV', 'https://www.mgtv.com'),
            ('搜狐视频', 'https://tv.sohu.com')
        ]
        
        for i, (name, url) in enumerate(platforms):
            btn = QPushButton(name)
            btn.setFont(QFont('微软雅黑', 10))
            btn.clicked.connect(lambda checked, u=url: self.open_platform(u))
            quick_layout.addWidget(btn, i // 3, i % 3)
        
        self.main_layout.addWidget(quick_group)
    
    def create_download_section(self):
        """创建下载区域"""
        download_group = QGroupBox('视频下载')
        download_layout = QVBoxLayout(download_group)
        
        sub_layout = QHBoxLayout()
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(['best - 最佳画质', '1080p', '720p', '480p', '360p', 'worst - 最低画质'])
        self.quality_combo.setFont(QFont('微软雅黑', 11))
        
        self.download_btn = QPushButton('📥 下载视频')
        self.download_btn.setFont(QFont('微软雅黑', 12))
        self.download_btn.clicked.connect(self.on_download_click)
        self.download_btn.setEnabled(False)
        
        sub_layout.addWidget(QLabel('画质选择:'))
        sub_layout.addWidget(self.quality_combo)
        sub_layout.addWidget(self.download_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        download_layout.addLayout(sub_layout)
        download_layout.addWidget(self.progress_bar)
        
        self.main_layout.addWidget(download_group)
    
    def get_style_sheet(self):
        """获取样式表"""
        return """
            QWidget {
                background-color: #f5f5f5;
            }
            QGroupBox {
                border: 2px solid #1e90ff;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #f5f5f5;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #1e90ff;
            }
            QPushButton {
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                background-color: #1e90ff;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4169e1;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
            QComboBox {
                padding: 6px;
                border: 2px solid #ddd;
                border-radius: 6px;
                min-width: 200px;
            }
            QTextEdit {
                border: 2px solid #ddd;
                border-radius: 6px;
            }
            QProgressBar {
                height: 20px;
                border-radius: 10px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #1e90ff;
                border-radius: 10px;
            }
        """
    
    def paste_from_clipboard(self):
        """从剪贴板粘贴内容"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.url_input.setText(text)
    
    def copy_to_clipboard(self):
        """复制链接到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.parsed_url)
        QMessageBox.information(self, '提示', '链接已复制到剪贴板！')
    
    def on_parse_click(self):
        """处理解析按钮点击"""
        video_url = self.url_input.text().strip()
        
        if not video_url:
            QMessageBox.warning(self, '警告', '请输入视频链接！')
            return
        
        api_key = self.api_combo.currentData()
        
        self.result_text.clear()
        self.result_text.append(f"🔍 正在解析: {video_url}")
        self.result_text.append(f"📡 使用线路: {self.api_combo.currentText().split(' ')[0]}")
        
        result = self.parser.parse_url(video_url, api_key)
        
        if result['success']:
            self.parsed_url = result['data']['parsed_url']
            platform = self.parser.detect_platform(video_url)
            
            self.result_text.append("\n✅ 解析成功！")
            self.result_text.append(f"📺 视频平台: {platform}")
            self.result_text.append(f"🔗 解析链接: {self.parsed_url}")
            
            self.open_btn.setEnabled(True)
            self.copy_btn.setEnabled(True)
            self.download_btn.setEnabled(True)
        else:
            self.result_text.append(f"\n❌ 解析失败: {result['message']}")
            self.open_btn.setEnabled(False)
            self.copy_btn.setEnabled(False)
            self.download_btn.setEnabled(False)
    
    def on_open_browser(self):
        """在浏览器中打开解析链接"""
        if hasattr(self, 'parsed_url'):
            if self.parser.open_in_browser(self.parsed_url):
                QMessageBox.information(self, '提示', '浏览器已打开！')
            else:
                QMessageBox.warning(self, '警告', '打开浏览器失败，请手动复制链接！')
    
    def on_download_click(self):
        """处理下载按钮点击"""
        if not hasattr(self, 'parsed_url'):
            QMessageBox.warning(self, '警告', '请先解析视频链接！')
            return
        
        video_url = self.parsed_url
        
        quality = self.quality_combo.currentText().split(' ')[0]
        
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.download_thread = DownloadThread(video_url, None, quality)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.start()
    
    def on_download_finished(self, result):
        """下载完成处理"""
        self.progress_bar.setVisible(False)
        self.download_btn.setEnabled(True)
        
        if result['success']:
            QMessageBox.information(self, '成功', f"视频下载成功！\n保存位置: {result['data']['output_path']}")
        else:
            QMessageBox.warning(self, '失败', result['message'])
    
    def open_platform(self, url):
        """打开视频平台"""
        self.parser.open_in_browser(url)

def main():
    """图形界面入口函数"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()