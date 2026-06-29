#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 设置任务栏中的图标显示
import ctypes
import os
import sys

from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QComboBox, QLabel, QTextEdit,
    QGroupBox, QGridLayout, QProgressBar, QMessageBox,
    QFileDialog, QSpinBox
)

from video_parser import VideoParser

my_app_id = "myVipApp"
# Windows 特有：设置任务栏图标
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)
except AttributeError:
    pass  # 非 Windows 平台跳过


def get_system_font(size=12):
    """
    获取跨平台的系统字体
    按优先级尝试不同平台的中文字体
    """
    font_families = [
        'Noto Sans CJK SC',
        'Noto Sans CJK TC',
        'Microsoft YaHei',
        'PingFang SC',
        'Hiragino Sans GB',
        'Heiti SC',
        'SimHei',
        'WenQuanYi Micro Hei',
        'Arial Unicode MS',
        'Arial'
    ]

    font = QFont()

    for family in font_families:
        if QFont(family).exactMatch():
            font.setFamily(family)
            font.setPointSize(size)
            return font

    font.setPointSize(size)
    return font


class DownloadThread(QThread):
    """
    视频下载线程
    用于在后台执行下载任务，避免阻塞UI
    """
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)

    def __init__(self, video_url, output_path, quality, original_url=None):
        super().__init__()
        self.video_url = video_url
        self.output_path = output_path
        self.quality = quality
        self.original_url = original_url
        self.parser = VideoParser()

    def run(self):
        """执行下载任务"""
        result = self.parser.download_video(
            self.video_url, self.output_path, self.quality, self.original_url
        )
        self.finished.emit(result)


class BatchDownloadThread(QThread):
    """
    批量下载线程
    用于在后台执行批量下载任务
    """
    progress = pyqtSignal(int, int, str, str)  # completed, total, status, message
    finished = pyqtSignal(dict)

    def __init__(self, start_url, output_path, quality, api_key='a', max_episodes=None, max_workers=3):
        super().__init__()
        self.start_url = start_url
        self.output_path = output_path
        self.quality = quality
        self.api_key = api_key
        self.max_episodes = max_episodes
        self.max_workers = max_workers
        self.parser = VideoParser()

    def run(self):
        """执行批量下载任务"""

        def progress_callback(completed, total, status, message):
            self.progress.emit(completed, total, status, message)

        result = self.parser.batch_download(
            self.start_url,
            self.output_path,
            self.quality,
            self.api_key,
            self.max_episodes,
            progress_callback,
            self.max_workers
        )
        self.finished.emit(result)


class EpisodeListThread(QThread):
    """
    获取剧集列表线程
    """
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)

    def __init__(self, video_url):
        super().__init__()
        self.video_url = video_url
        self.parser = VideoParser()

    def run(self):
        self.progress.emit("正在获取剧集列表，请稍候...")
        result = self.parser.get_episode_list(self.video_url)
        self.finished.emit(result)


class NextEpisodeThread(QThread):
    """
    获取下一集线程
    """
    finished = pyqtSignal(dict)

    def __init__(self, current_url):
        super().__init__()
        self.current_url = current_url
        self.parser = VideoParser()

    def run(self):
        result = self.parser.get_next_episode(self.current_url)
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
        self.batch_thread = None
        self.next_thread = None
        self.episode_list_thread = None

        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('VIP 视频解析工具')
        self.setGeometry(100, 100, 750, 650)
        icon_path = get_icon_path()
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.create_url_input()
        self.create_api_selector()
        self.create_action_buttons()
        self.create_result_area()
        self.create_batch_download_section()
        self.create_quick_links()
        self.create_download_section()
        self.create_status_bar()

        self.setStyleSheet(self.get_style_sheet())

    def create_url_input(self):
        """创建URL输入区域"""
        url_group = QGroupBox('视频链接')
        url_layout = QHBoxLayout(url_group)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            '视频链接，支持腾讯视频、优酷、哔哩哔哩、爱奇艺等...例如：https://v.qq.com/x/cover/wu1e7mrffzvibjy/x0030xogl32.html')
        self.url_input.setFont(get_system_font(12))
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
        self.api_combo.setFont(get_system_font(12))

        apis = self.parser.get_all_apis()
        for key, api in apis.items():
            status = ' ✅' if api['status'] == 'active' else ' ❌'
            note = f" ({api['note']})" if api['note'] else ''
            self.api_combo.addItem(f"{key}. {api['name']}{status}{note}", key)

        self.api_combo.setCurrentText('a. 万能稳定解析 ✅ (推荐使用)')

        api_layout.addWidget(QLabel('选择解析线路:'))
        api_layout.addWidget(self.api_combo)

        self.main_layout.addWidget(api_group)

    def create_action_buttons(self):
        """创建操作按钮"""
        btn_layout = QHBoxLayout()

        self.parse_btn = QPushButton('开始解析')
        self.parse_btn.setFont(get_system_font(12))
        self.parse_btn.clicked.connect(self.on_parse_click)

        self.episode_list_btn = QPushButton('获取全部剧集')
        self.episode_list_btn.setFont(get_system_font(12))
        self.episode_list_btn.clicked.connect(self.on_episode_list_click)
        self.episode_list_btn.setEnabled(False)
        self.episode_list_btn.setToolTip('获取当前视频的全部剧集列表（支持腾讯、爱奇艺）')

        self.open_btn = QPushButton('在浏览器打开')
        self.open_btn.setFont(get_system_font(12))
        self.open_btn.clicked.connect(self.on_open_browser)
        self.open_btn.setEnabled(False)

        self.copy_btn = QPushButton('复制链接')
        self.copy_btn.setFont(get_system_font(12))
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.copy_btn.setEnabled(False)

        self.next_btn = QPushButton('下一集')
        self.next_btn.setFont(get_system_font(12))
        self.next_btn.clicked.connect(self.on_next_episode)
        self.next_btn.setEnabled(False)
        self.next_btn.setToolTip('自动获取并解析下一集（支持腾讯、爱奇艺）')

        btn_layout.addWidget(self.parse_btn)
        btn_layout.addWidget(self.episode_list_btn)
        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.next_btn)

        self.main_layout.addLayout(btn_layout)

    def create_result_area(self):
        """创建结果显示区域"""
        result_group = QGroupBox('解析结果')
        result_layout = QVBoxLayout(result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(get_system_font(11))
        self.result_text.setPlaceholderText('解析结果将显示在这里...')

        result_layout.addWidget(self.result_text)

        self.main_layout.addWidget(result_group)

    def create_batch_download_section(self):
        """创建批量下载区域"""
        batch_group = QGroupBox('批量下载电视剧（支持腾讯、爱奇艺）')
        batch_layout = QVBoxLayout(batch_group)

        # 保存目录选择
        dir_layout = QHBoxLayout()
        self.output_path_label = QLabel('保存目录:')
        self.output_path_input = QLineEdit()
        self.output_path_input.setPlaceholderText('点击右侧按钮选择保存目录...')
        self.output_path_input.setReadOnly(True)
        self.select_dir_btn = QPushButton('选择目录')
        self.select_dir_btn.clicked.connect(self.on_select_directory)

        dir_layout.addWidget(self.output_path_label)
        dir_layout.addWidget(self.output_path_input)
        dir_layout.addWidget(self.select_dir_btn)
        batch_layout.addLayout(dir_layout)

        # 下载选项
        options_layout = QHBoxLayout()

        self.max_episodes_spin = QSpinBox()
        self.max_episodes_spin.setRange(0, 100)
        self.max_episodes_spin.setValue(0)
        self.max_episodes_spin.setSpecialValueText('全部')
        self.max_episodes_spin.setPrefix('下载集数: ')
        self.max_episodes_spin.setSuffix(' 集')
        self.max_episodes_spin.setToolTip('0表示下载全部剧集')

        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 10)
        self.thread_spin.setValue(3)
        self.thread_spin.setPrefix('并发数: ')
        self.thread_spin.setSuffix(' 线程')
        self.thread_spin.setToolTip('同时下载的剧集数量，建议2-5个')

        self.batch_quality_combo = QComboBox()
        self.batch_quality_combo.addItems(['best - 最佳画质', '1080p', '720p', '480p', '360p'])
        self.batch_quality_combo.setFont(get_system_font(11))

        self.batch_download_btn = QPushButton('批量下载全部剧集')
        self.batch_download_btn.setFont(get_system_font(12))
        self.batch_download_btn.clicked.connect(self.on_batch_download_click)
        self.batch_download_btn.setEnabled(False)

        options_layout.addWidget(self.max_episodes_spin)
        options_layout.addWidget(self.thread_spin)
        options_layout.addWidget(QLabel('画质:'))
        options_layout.addWidget(self.batch_quality_combo)
        options_layout.addWidget(self.batch_download_btn)

        batch_layout.addLayout(options_layout)

        # 批量下载进度条
        self.batch_progress_bar = QProgressBar()
        self.batch_progress_bar.setVisible(False)
        batch_layout.addWidget(self.batch_progress_bar)

        self.main_layout.addWidget(batch_group)

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
            btn.setFont(get_system_font(10))
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
        self.quality_combo.setFont(get_system_font(11))

        self.download_btn = QPushButton('下载视频')
        self.download_btn.setFont(get_system_font(12))
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

    def create_status_bar(self):
        """创建状态栏，显示作者信息"""
        status_bar = QWidget()
        status_bar.setFixedHeight(25)
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(10, 0, 10, 0)
        
        self.author_label = QLabel('© 作者: QiYue')
        self.author_label.setFont(get_system_font(10))
        self.author_label.setStyleSheet('color: #888888;')
        
        self.version_label = QLabel('v0.0.7')
        self.version_label.setFont(get_system_font(10))
        self.version_label.setStyleSheet('color: #888888;')
        self.version_label.setAlignment(Qt.AlignRight)
        
        status_layout.addWidget(self.author_label)
        status_layout.addStretch()
        status_layout.addWidget(self.version_label)
        
        self.main_layout.addWidget(status_bar)

    def get_style_sheet(self):
        """获取样式表"""
        return """
            QWidget {
                background-color: #ffffff;
                color: #1a1a1a;
            }
            QGroupBox {
                border: 2px solid #1e90ff;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #000000;
                background-color: #fafafa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 3px 8px;
                background-color: #ffffff;
                border-radius: 4px;
                color: #1e90ff;
            }
            QLineEdit {
                padding: 10px;
                border: 2px solid #cccccc;
                border-radius: 6px;
                font-size: 13px;
                background-color: #ffffff;
                color: #000000;
            }
            QLineEdit:focus {
                border-color: #1e90ff;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
            QPushButton {
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                background-color: #1e90ff;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4169e1;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #999999;
            }
            QComboBox {
                padding: 10px;
                border: 2px solid #cccccc;
                border-radius: 6px;
                min-width: 150px;
                background-color: #ffffff;
                color: #000000;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border-left: 2px solid #cccccc;
            }
            QTextEdit {
                border: 2px solid #cccccc;
                border-radius: 6px;
                background-color: #ffffff;
                color: #000000;
                padding: 10px;
                font-size: 13px;
            }
            QTextEdit::placeholder {
                color: #999999;
            }
            QLabel {
                color: #000000;
                font-size: 13px;
            }
            QProgressBar {
                height: 20px;
                border-radius: 10px;
                text-align: center;
                background-color: #eeeeee;
                color: #000000;
            }
            QProgressBar::chunk {
                background-color: #1e90ff;
                border-radius: 10px;
            }
            QSpinBox {
                padding: 8px;
                border: 2px solid #cccccc;
                border-radius: 6px;
                background-color: #ffffff;
                color: #000000;
                font-size: 13px;
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

    def on_select_directory(self):
        """选择下载保存目录"""
        directory = QFileDialog.getExistingDirectory(
            self,
            '选择下载保存目录',
            os.path.expanduser('~/Downloads'),
            QFileDialog.ShowDirsOnly
        )
        if directory:
            self.output_path_input.setText(directory)

    def on_parse_click(self):
        """处理解析按钮点击"""
        video_url = self.url_input.text().strip()

        if not video_url:
            QMessageBox.warning(self, '警告', '请输入视频链接！')
            return

        api_key = self.api_combo.currentData()

        self.result_text.clear()
        self.result_text.append(f"正在解析: {video_url}")
        self.result_text.append(f"使用线路: {self.api_combo.currentText().split(' ')[0]}")

        result = self.parser.parse_url(video_url, api_key)

        if result['success']:
            self.parsed_url = result['data']['parsed_url']
            self.original_url = video_url
            platform = self.parser.detect_platform(video_url)

            self.result_text.append("\n解析成功！")
            self.result_text.append(f"视频平台: {platform}")
            self.result_text.append(f"解析链接: {self.parsed_url}")

            self.open_btn.setEnabled(True)
            self.copy_btn.setEnabled(True)
            self.download_btn.setEnabled(True)

            # 如果是腾讯或爱奇艺，启用下一集和批量下载按钮
            if platform in ['腾讯视频', '爱奇艺']:
                self.next_btn.setEnabled(True)
                self.batch_download_btn.setEnabled(True)
                self.episode_list_btn.setEnabled(True)
            else:
                self.next_btn.setEnabled(False)
                self.batch_download_btn.setEnabled(False)
                self.episode_list_btn.setEnabled(False)
        else:
            self.result_text.append(f"\n解析失败: {result['message']}")
            self.open_btn.setEnabled(False)
            self.copy_btn.setEnabled(False)
            self.download_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            self.batch_download_btn.setEnabled(False)
            self.episode_list_btn.setEnabled(False)

    def show_auto_close_info(self, title, message, timeout=2000):
        """
        显示自动关闭的信息提示框
        :param title: 提示框标题
        :param message: 提示内容
        :param timeout: 自动关闭时间（毫秒），默认2000毫秒（2秒）
        """
        # 创建消息框实例，保存为成员变量防止被垃圾回收
        self._auto_close_msg_box = QMessageBox(self)
        self._auto_close_msg_box.setWindowTitle(title)
        self._auto_close_msg_box.setText(message)
        # 设置为信息图标
        self._auto_close_msg_box.setIcon(QMessageBox.Information)
        # 添加确定按钮，用户也可以手动关闭
        self._auto_close_msg_box.setStandardButtons(QMessageBox.Ok)
        # 显示消息框（非阻塞方式）
        self._auto_close_msg_box.show()
        # 使用定时器在指定时间后自动关闭消息框
        QTimer.singleShot(timeout, self._auto_close_msg_box.accept)

    def on_open_browser(self):
        """在浏览器中打开解析链接"""
        if hasattr(self, 'parsed_url'):
            if self.parser.open_in_browser(self.parsed_url):
                # 使用自动关闭的提示框，2秒后自动关闭
                self.show_auto_close_info('提示', '浏览器已打开！')
            else:
                QMessageBox.warning(self, '警告', '打开浏览器失败，请手动复制链接！')

    def on_download_click(self):
        """处理下载按钮点击"""
        if not hasattr(self, 'parsed_url'):
            QMessageBox.warning(self, '警告', '请先解析视频链接！')
            return

        # 检查是否选择了保存目录
        output_path = self.output_path_input.text().strip()
        if not output_path:
            output_path = QFileDialog.getExistingDirectory(
                self,
                '选择下载保存目录',
                os.path.expanduser('~/Downloads'),
                QFileDialog.ShowDirsOnly
            )
            if not output_path:
                QMessageBox.warning(self, '警告', '请选择下载保存目录！')
                return
            self.output_path_input.setText(output_path)

        video_url = self.parsed_url
        original_url = getattr(self, 'original_url', None)
        quality = self.quality_combo.currentText().split(' ')[0]

        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.download_thread = DownloadThread(video_url, output_path, quality, original_url)
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

    def on_batch_download_click(self):
        """处理批量下载按钮点击"""
        video_url = self.url_input.text().strip()
        if not video_url:
            QMessageBox.warning(self, '警告', '请输入视频链接！')
            return

        # 检查保存目录
        output_path = self.output_path_input.text().strip()
        if not output_path:
            output_path = QFileDialog.getExistingDirectory(
                self,
                '选择下载保存目录',
                os.path.expanduser('~/Downloads'),
                QFileDialog.ShowDirsOnly
            )
            if not output_path:
                QMessageBox.warning(self, '警告', '请选择下载保存目录！')
                return
            self.output_path_input.setText(output_path)

        platform = self.parser.detect_platform(video_url)
        if platform not in ['腾讯视频', '爱奇艺']:
            QMessageBox.warning(self, '警告', f'暂不支持{platform}的批量下载')
            return

        # 获取下载集数限制
        max_episodes = self.max_episodes_spin.value()
        if max_episodes == 0:
            max_episodes = None

        quality = self.batch_quality_combo.currentText().split(' ')[0]
        api_key = self.api_combo.currentData()
        max_workers = self.thread_spin.value()

        # 确认对话框
        reply = QMessageBox.question(
            self,
            '批量下载确认',
            f'即将开始批量下载，保存目录: {output_path}\n'
            f'下载集数: {max_episodes if max_episodes else "全部"}\n'
            f'并发数: {max_workers} 线程\n'
            f'画质: {quality}\n'
            f'是否继续？',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self.result_text.append(f"\n开始批量下载电视剧...")
        self.result_text.append(f"保存目录: {output_path}")
        self.result_text.append(f"画质: {quality}")
        self.result_text.append(f"并发数: {max_workers} 线程")

        self.batch_download_btn.setEnabled(False)
        self.batch_progress_bar.setVisible(True)
        self.batch_progress_bar.setRange(0, 100)
        self.batch_progress_bar.setValue(0)

        self.batch_thread = BatchDownloadThread(
            video_url, output_path, quality, api_key, max_episodes, max_workers
        )
        self.batch_thread.progress.connect(self.on_batch_progress)
        self.batch_thread.finished.connect(self.on_batch_finished)
        self.batch_thread.start()

    def on_batch_progress(self, completed, total, status, message):
        """批量下载进度更新"""
        self.result_text.append(message)
        if total > 0:
            progress = int((completed / total) * 100)
            self.batch_progress_bar.setValue(min(progress, 100))

    def on_batch_finished(self, result):
        """批量下载完成处理"""
        self.batch_progress_bar.setVisible(False)
        self.batch_download_btn.setEnabled(True)

        if result['success']:
            data = result['data']
            msg = (
                f"批量下载完成！\n\n"
                f"成功: {len(data['downloaded'])} 集\n"
                f"失败: {len(data['failed'])} 集\n"
                f"总计: {data['total']} 集\n"
                f"保存位置: {data['output_path']}"
            )
            QMessageBox.information(self, '批量下载完成', msg)
        else:
            QMessageBox.warning(self, '批量下载失败', result['message'])

    def open_platform(self, url):
        """打开视频平台"""
        self.parser.open_in_browser(url)

    def on_episode_list_click(self):
        """处理获取全部剧集按钮点击"""
        if not hasattr(self, 'original_url'):
            QMessageBox.warning(self, '警告', '请先解析视频链接！')
            return

        video_url = self.original_url
        platform = self.parser.detect_platform(video_url)

        if platform not in ['腾讯视频', '爱奇艺']:
            QMessageBox.warning(self, '警告', f'暂不支持{platform}的获取剧集列表功能')
            return

        self.result_text.append(f"\n正在获取全部剧集列表...")
        self.result_text.append(f"请稍候，这可能需要几秒钟...")
        self.episode_list_btn.setEnabled(False)

        self.episode_list_thread = EpisodeListThread(video_url)
        self.episode_list_thread.progress.connect(self.on_episode_list_progress)
        self.episode_list_thread.finished.connect(self.on_episode_list_finished)
        self.episode_list_thread.start()

    def on_episode_list_progress(self, message):
        """获取剧集列表进度"""
        self.result_text.append(message)

    def on_episode_list_finished(self, result):
        """获取剧集列表完成"""
        self.episode_list_btn.setEnabled(True)

        if result['success']:
            data = result['data']
            episodes = data['episodes']
            total = data['total']

            self.result_text.append(f"\n{'='*60}")
            self.result_text.append(f"📺 平台: {data['platform']}")
            self.result_text.append(f"✅ 共找到 {total} 集")
            self.result_text.append(f"{'='*60}")
            self.result_text.append(f"{'集数':<8} {'链接'}")
            self.result_text.append(f"{'-'*60}")

            for ep in episodes:
                self.result_text.append(f"第{ep['episode_num']:<4}集  {ep['url']}")

            self.result_text.append(f"{'='*60}")
            self.result_text.append(f"\n提示：可以通过\"批量下载\"功能下载全部剧集")

            QMessageBox.information(
                self, '获取成功',
                f"已获取 {total} 集的剧集列表！\n\n"
                f"可以使用\"批量下载全部剧集\"功能进行下载。"
            )
        else:
            self.result_text.append(f"\n❌ 获取剧集列表失败: {result['message']}")
            QMessageBox.warning(self, '获取失败', result['message'])

    def on_next_episode(self):
        """处理下一集按钮点击"""
        if not hasattr(self, 'original_url'):
            QMessageBox.warning(self, '警告', '请先解析视频链接！')
            return

        current_url = self.original_url
        platform = self.parser.detect_platform(current_url)

        if platform not in ['腾讯视频', '爱奇艺']:
            QMessageBox.warning(self, '警告', f'暂不支持{platform}的自动获取下一集功能')
            return

        self.result_text.append(f"\n正在获取下一集...")
        self.next_btn.setEnabled(False)

        self.next_thread = NextEpisodeThread(current_url)
        self.next_thread.finished.connect(self.on_next_episode_finished)
        self.next_thread.start()

    def on_next_episode_finished(self, result):
        """下一集获取完成处理"""
        self.next_btn.setEnabled(True)

        if result['success']:
            next_url = result['data']['next_url']
            episode_num = result['data']['episode_num']

            self.result_text.append(f"找到下一集：第{episode_num}集")

            reply = QMessageBox.question(
                self,
                '下一集',
                f'已找到第{episode_num}集，是否自动解析？',
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.url_input.setText(next_url)
                self.on_parse_click()
        else:
            self.result_text.append(f"{result['message']}")
            QMessageBox.warning(self, '获取下一集失败', result['message'])


def get_icon_path():
    """获取图标文件路径，支持打包后运行"""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'icon.ico')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')


def main():
    """图形界面入口函数"""
    app = QApplication(sys.argv)
    
    icon_path = get_icon_path()
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
