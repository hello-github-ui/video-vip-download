#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 设置任务栏中的图标显示
import ctypes
import os
import signal
import sys

from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QComboBox, QLabel, QTextEdit,
    QGroupBox, QGridLayout, QProgressBar, QMessageBox,
    QFileDialog, QSpinBox, QTabWidget, QCheckBox
)

from video_parser import VideoParser

my_app_id = "myVipApp"
# Windows 特有：设置任务栏图标
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)
except AttributeError:
    pass  # 非 Windows 平台跳过


# =====================================================================
# 全局日志拦截系统（类似 Java AOP 的切面拦截思想）
# =====================================================================
# 原理说明：
#   在 Python 中，所有的 print() 函数本质上是向 sys.stdout 这个"标准输出流"写入内容。
#   sys.stdout 默认指向的是控制台（终端/命令行）。
#
#   如果我们把 sys.stdout 替换成一个我们自己写的"假的输出流对象"，
#   那么所有 print() 调用就都会写入我们这个对象，
#   我们就可以在里面做任何想做的事情（比如转发到 GUI 文本框、写文件等）。
#
#   这就类似 Java 中的 AOP（面向切面编程）：
#   - 被代理的对象：原来的 sys.stdout（控制台输出）
#   - 切面逻辑：拦截每一行输出，同时做两件事（写控制台 + 发信号给GUI）
#   - 织入方式：替换 sys.stdout 这个全局变量
#
#   关键点：
#   1. 我们自己的流对象必须实现 write() 和 flush() 方法（这是 Python 对"流"的基本约定）
#   2. 必须保存原来的 sys.stdout，否则就丢失了控制台输出
#   3. 多线程安全：sys.stdout 是全局变量，所有线程共享，所以子线程的 print 也会被拦截
#   4. GUI 更新必须在主线程：所以用 pyqtSignal 把日志从子线程转发到主线程
# =====================================================================


class LogStream:
    """
    自定义的标准输出流（stdout），用于全局拦截所有 print 输出。
    
    相当于一个"代理/包装器"模式：
    - 把输出同时转发到原来的控制台（保证终端里仍然能看到输出）
    - 同时通过回调函数转发给 GUI 显示（可选）
    """

    def __init__(self, original_stdout):
        # 保存原来的标准输出（控制台），必须保留，否则 print 就没地方输出了
        self.original_stdout = original_stdout
        # 日志回调函数，有新的就调用
        self._callback = None
        # 行缓冲区：print 会分多次 write（比如内容 + 换行符），我们攒到一整行再回调
        self._buffer = ''

    def set_callback(self, callback):
        """设置日志回调函数，当有新的一行日志时调用"""
        self._callback = callback

    def write(self, message):
        """
        这是最核心的拦截方法。
        所有 print() 最终都会调用 sys.stdout.write(message)。
        我们在这里做了之后，就相当于在所有 print 执行时插入了自己的逻辑。
        """
        # 第一步：照常输出到原来的控制台（保证终端里仍然能看到）
        self.original_stdout.write(message)

        # 第二步：如果设置了回调，就把日志行传过去
        if self._callback is not None:
            # print 会分多次写入：比如 print("hello") 会先 write("hello") 再 write("\n")
            # 所以我们用缓冲区攒到一整行（遇到换行符）再回调，避免半行半行地显示
            self._buffer += message
            while '\n' in self._buffer:
                # 按换行符分割，取出完整的一行
                line, self._buffer = self._buffer.split('\n', 1)
                # 空行跳过（只是换行符的情况）
                if line.strip():
                    try:
                        self._callback(line)
                    except Exception:
                        # 回调出错不能影响正常输出，直接忽略
                        pass

    def flush(self):
        """
        刷新缓冲区。
        这是流对象必须实现的方法，否则某些库会调用 flush() 来强制输出。
        我们把它转发给原来的 stdout。
        """
        self.original_stdout.flush()


# 全局的日志流对象（单例模式，整个程序共用一个
_global_log_stream = None


def setup_global_logging():
    """
    初始化全局日志拦截系统。
    把 sys.stdout 替换成我们自己的 LogStream 对象。
    之后所有的 print 都会被拦截。
    """
    global _global_log_stream
    if _global_log_stream is None:
        # 保存原来的 stdout，并创建我们的日志流
        _global_log_stream = LogStream(sys.stdout)
        # 替换全局的 sys.stdout
        sys.stdout = _global_log_stream
    return _global_log_stream


def get_global_log_stream():
    """获取全局日志流对象（用于设置回调等）"""
    return _global_log_stream


def get_system_font(size=12):
    """
    获取跨平台的系统字体
    按优先级尝试不同平台的中文字体
    """
    font_families = [
        'Arial',
        'Noto Sans CJK SC',
        'Noto Sans CJK TC',
        'Microsoft YaHei',
        'PingFang SC',
        'Hiragino Sans GB',
        'Heiti SC',
        'SimHei',
        'WenQuanYi Micro Hei',
        'Arial Unicode MS'
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
    
    日志输出说明：
    下载过程中的 print 输出会被全局 LogStream 拦截，
    不需要在这里单独处理日志信号，统一由 MainWindow 的 _on_log_line 处理。
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


class MainWindow(QMainWindow):
    """
    主窗口类
    提供视频解析工具的图形界面
    
    日志系统说明：
    - 使用全局 LogStream 拦截所有 print 输出（类似Java AOP切面）
    - 通过 _log_bridge（QObject+信号）把日志从任意线程转发到主线程
    - 用户勾选"显示详细日志"时，日志追加到"解析结果"文本框
    - 默认不显示详细日志
    """

    def __init__(self):
        super().__init__()
        self.parser = VideoParser()
        self.download_thread = None
        self.batch_thread = None
        self.next_thread = None
        self.episode_list_thread = None

        # 初始化全局日志拦截系统（替换 sys.stdout）
        # 这一步之后，程序里所有的 print() 都会被我们的 LogStream 拦截
        self._log_stream = setup_global_logging()

        # 日志桥接器：把 LogStream 的回调（可能在子线程）转换成 Qt 信号（主线程处理）
        # 为什么需要这个桥接器？
        #   - LogStream 的 write() 方法可能在任何线程被调用（比如下载线程里的 print）
        #   - 但 PyQt 的 GUI 控件只能在主线程更新
        #   - 所以用 pyqtSignal 做一次转发，Qt 会自动把信号投递到主线程
        class LogBridge(QThread):
            log_line = pyqtSignal(str)

            def handle_log(self, line):
                self.log_line.emit(line)

        self._log_bridge = LogBridge()
        # 把桥接器的槽函数注册到全局日志流
        self._log_stream.set_callback(self._log_bridge.handle_log)
        # 桥接器的信号连接到我们的显示方法
        self._log_bridge.log_line.connect(self._append_log_line)

        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('VIP 视频解析工具')
        self.setGeometry(100, 100, 880, 650)
        icon_path = get_icon_path()
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # 注意下面几行代码的书写顺序会影响gui的界面构建效果
        self.create_url_input()
        self.create_api_selector()
        self.create_action_buttons()
        self.create_tab_widget()
        self.result_text.append("解析结果将显示在这里...")
        self.result_text.append(f"欢迎使用VIP 视频解析工具")
        # 注意：此时 self.parser.parse_apis 已经初始化过了
        self.result_text.append(f"已加载默认解析接口: {self.parser.parse_apis[0].get('name')} ✅ (推荐使用)")
        # self.create_batch_download_section()
        self.create_quick_links()
        self.create_download_section()
        self.create_status_bar()

        self.setStyleSheet(self.get_style_sheet())

    def create_url_input(self):
        """创建URL输入区域"""
        url_group = QGroupBox('视频链接')
        url_layout = QHBoxLayout(url_group)
        url_layout.setSpacing(10)

        platforms = ['自动检测', '腾讯视频', '优酷', '哔哩哔哩', '爱奇艺', '芒果TV', '搜狐视频', 'PP视频', '乐视视频',
                     '土豆视频', 'AcFun']

        self.platform_combo = QComboBox()
        self.platform_combo.setFont(get_system_font(12))
        for p in platforms:
            self.platform_combo.addItem(p)
        self.platform_combo.setCurrentIndex(0)
        self.platform_combo.setMinimumWidth(120)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('请输入视频链接...')
        self.url_input.setFont(get_system_font(12))
        self.url_input.returnPressed.connect(self.on_parse_click)

        url_layout.addWidget(self.platform_combo)
        url_layout.addWidget(self.url_input)

        self.main_layout.addWidget(url_group)

    def create_api_selector(self):
        """创建解析线路选择器"""
        api_group = QGroupBox('解析线路')
        api_layout = QHBoxLayout(api_group)

        # QComboBox Qt部件，用于显示和选择下拉框列表中的项，提供了一组选项供用户选择，并且允许用户输入自定义的项
        self.api_combo = QComboBox()
        self.api_combo.setFont(get_system_font(12))

        apis = self.parser.parse_apis
        for api in apis:
            status = ' ✅' if api['status'] == 'active' else ' ❌'
            note = f" ({api['note']})" if api['note'] else ''
            self.api_combo.addItem(f"{api['name']}. {api['name']}{status}{note}", api)
        current_default_choice_text = f"{apis[0].get('name')} ✅ (推荐使用)"
        # current_default_choice_text: 万能稳定解析
        print(f"current_default_choice_text: {current_default_choice_text}")
        self.api_combo.setCurrentText(current_default_choice_text)

        api_layout.addWidget(QLabel('选择解析线路:'))
        api_layout.addWidget(self.api_combo)

        self.main_layout.addWidget(api_group)

    def create_action_buttons(self):
        """创建操作按钮"""
        btn_layout = QHBoxLayout()

        self.parse_btn = QPushButton('开始解析')
        self.parse_btn.setFont(get_system_font(12))
        self.parse_btn.clicked.connect(self.on_parse_click)

        # self.episode_list_btn = QPushButton('获取全部剧集')
        # self.episode_list_btn.setFont(get_system_font(12))
        # self.episode_list_btn.clicked.connect(self.on_episode_list_click)
        # self.episode_list_btn.setEnabled(False)
        # self.episode_list_btn.setToolTip('获取当前视频的全部剧集列表（支持腾讯、爱奇艺）')

        self.open_btn = QPushButton('在浏览器打开')
        self.open_btn.setFont(get_system_font(12))
        self.open_btn.clicked.connect(self.on_open_browser)
        self.open_btn.setEnabled(False)

        # self.copy_btn = QPushButton('复制链接')
        # self.copy_btn.setFont(get_system_font(12))
        # self.copy_btn.clicked.connect(self.copy_to_clipboard)
        # self.copy_btn.setEnabled(False)

        # self.next_btn = QPushButton('下一集')
        # self.next_btn.setFont(get_system_font(12))
        # self.next_btn.clicked.connect(self.on_next_episode)
        # self.next_btn.setEnabled(False)
        # self.next_btn.setToolTip('自动获取并解析下一集（支持腾讯、爱奇艺）')

        # self.play_btn = QPushButton('在浏览器播放')
        # self.play_btn.setFont(get_system_font(12))
        # self.play_btn.clicked.connect(self.on_play_click)
        # self.play_btn.setEnabled(False)
        # self.play_btn.setToolTip('在浏览器中播放解析后的视频')

        btn_layout.addWidget(self.parse_btn)
        # btn_layout.addWidget(self.episode_list_btn)
        btn_layout.addWidget(self.open_btn)
        # btn_layout.addWidget(self.copy_btn)
        # btn_layout.addWidget(self.next_btn)
        # btn_layout.addWidget(self.play_btn)

        self.main_layout.addLayout(btn_layout)

    def create_tab_widget(self):
        """创建选项卡区域"""
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(get_system_font(11))

        # ===== 解析结果 =====
        result_tab = QWidget()
        result_layout = QVBoxLayout(result_tab)
        result_layout.setContentsMargins(5, 5, 5, 5)

        # --- 解析结果文本 ---
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(get_system_font(11))
        # self.result_text.setPlaceholderText('解析结果将显示在这里...')
        result_layout.addWidget(self.result_text)

        self.tab_widget.addTab(result_tab, '解析结果')

        self.main_layout.addWidget(self.tab_widget, stretch=1)

    # def create_batch_download_section(self):
    #     """创建批量下载区域"""
    #     batch_group = QGroupBox('批量下载电视剧（支持腾讯、爱奇艺）')
    #     batch_layout = QVBoxLayout(batch_group)
    #
    #     # 保存目录选择
    #     dir_layout = QHBoxLayout()
    #     self.output_path_label = QLabel('保存目录:')
    #     self.output_path_input = QLineEdit()
    #     self.output_path_input.setPlaceholderText('点击右侧按钮选择保存目录...')
    #     self.output_path_input.setReadOnly(True)
    #     self.select_dir_btn = QPushButton('选择目录')
    #     self.select_dir_btn.clicked.connect(self.on_select_directory)
    #
    #     dir_layout.addWidget(self.output_path_label)
    #     dir_layout.addWidget(self.output_path_input)
    #     dir_layout.addWidget(self.select_dir_btn)
    #     batch_layout.addLayout(dir_layout)
    #
    #     # 下载选项
    #     options_layout = QHBoxLayout()
    #
    #     self.max_episodes_spin = QSpinBox()
    #     self.max_episodes_spin.setRange(0, 100)
    #     self.max_episodes_spin.setValue(0)
    #     self.max_episodes_spin.setSpecialValueText('全部')
    #     self.max_episodes_spin.setPrefix('下载集数: ')
    #     self.max_episodes_spin.setSuffix(' 集')
    #     self.max_episodes_spin.setToolTip('0表示下载全部剧集')
    #
    #     self.thread_spin = QSpinBox()
    #     self.thread_spin.setRange(1, 10)
    #     self.thread_spin.setValue(3)
    #     self.thread_spin.setPrefix('并发数: ')
    #     self.thread_spin.setSuffix(' 线程')
    #     self.thread_spin.setToolTip('同时下载的剧集数量，建议2-5个')
    #
    #     self.batch_quality_combo = QComboBox()
    #     self.batch_quality_combo.addItems(['best - 最佳画质', '1080p', '720p', '480p', '360p'])
    #     self.batch_quality_combo.setFont(get_system_font(11))
    #
    #     self.batch_download_btn = QPushButton('批量下载全部剧集')
    #     self.batch_download_btn.setFont(get_system_font(12))
    #     self.batch_download_btn.clicked.connect(self.on_batch_download_click)
    #     self.batch_download_btn.setEnabled(False)
    #
    #     options_layout.addWidget(self.max_episodes_spin)
    #     options_layout.addWidget(self.thread_spin)
    #     options_layout.addWidget(QLabel('画质:'))
    #     options_layout.addWidget(self.batch_quality_combo)
    #     options_layout.addWidget(self.batch_download_btn)
    #
    #     batch_layout.addLayout(options_layout)
    #
    #     # 批量下载进度条
    #     self.batch_progress_bar = QProgressBar()
    #     self.batch_progress_bar.setVisible(False)
    #     batch_layout.addWidget(self.batch_progress_bar)
    #
    #     self.main_layout.addWidget(batch_group)

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

        self.log_checkbox = QCheckBox('显示详细日志')
        self.log_checkbox.setFont(get_system_font(11))
        self.log_checkbox.setChecked(False)
        self.log_checkbox.stateChanged.connect(self._on_log_toggled)

        sub_layout.addWidget(QLabel('画质选择:'))
        sub_layout.addWidget(self.quality_combo)
        sub_layout.addWidget(self.download_btn)
        sub_layout.addStretch()
        sub_layout.addWidget(self.log_checkbox)

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

        self.version_label = QLabel('v1.0.0')
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
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: bold;
                color: #1a1a1a;
                background-color: #fafafa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 3px 10px;
                background-color: #ffffff;
                border-radius: 6px;
                color: #1e90ff;
                font-size: 13px;
            }
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 13px;
                background-color: #ffffff;
                color: #1a1a1a;
                selection-background-color: #1e90ff;
                selection-color: #ffffff;
            }
            QLineEdit:hover {
                border-color: #b0b0b0;
            }
            QLineEdit:focus {
                border-color: #1e90ff;
                background-color: #f8fbff;
            }
            QLineEdit::placeholder {
                color: #aaaaaa;
            }
            QPushButton {
                padding: 9px 20px;
                border: none;
                border-radius: 8px;
                background-color: #1e90ff;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #187bcd;
            }
            QPushButton:pressed {
                background-color: #1565c0;
            }
            QPushButton:disabled {
                background-color: #e0e0e0;
                color: #999999;
            }
            QComboBox {
                padding: 6px 10px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                min-width: 150px;
                background-color: #ffffff;
                color: #1a1a1a;
                font-size: 13px;
                selection-background-color: #1e90ff;
                selection-color: #ffffff;
            }
            QComboBox:hover {
                border-color: #b0b0b0;
            }
            QComboBox:focus {
                border-color: #1e90ff;
                background-color: #f8fbff;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background-color: #ffffff;
                color: #1a1a1a;
                selection-background-color: #e6f3ff;
                selection-color: #1e90ff;
                padding: 6px;
                outline: 0;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px 12px;
                border-radius: 4px;
                margin: 2px 0;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #f0f7ff;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #e6f3ff;
                color: #1e90ff;
                font-weight: bold;
            }
            QTextEdit {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background-color: #ffffff;
                color: #1a1a1a;
                padding: 10px 12px;
                font-size: 13px;
                selection-background-color: #1e90ff;
                selection-color: #ffffff;
            }
            QTextEdit:hover {
                border-color: #b0b0b0;
            }
            QTextEdit:focus {
                border-color: #1e90ff;
            }
            QTextEdit::placeholder {
                color: #aaaaaa;
            }
            QLabel {
                color: #1a1a1a;
                font-size: 13px;
            }
            QProgressBar {
                height: 20px;
                border-radius: 10px;
                text-align: center;
                background-color: #f0f0f0;
                color: #1a1a1a;
            }
            QProgressBar::chunk {
                background-color: #1e90ff;
                border-radius: 10px;
            }
            QSpinBox {
                padding: 6px 8px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background-color: #ffffff;
                color: #1a1a1a;
                font-size: 13px;
                selection-background-color: #1e90ff;
                selection-color: #ffffff;
            }
            QSpinBox:hover {
                border-color: #b0b0b0;
            }
            QSpinBox:focus {
                border-color: #1e90ff;
                background-color: #f8fbff;
            }
        """

    # def paste_from_clipboard(self):
    #     """从剪贴板粘贴内容"""
    #     clipboard = QApplication.clipboard()
    #     text = clipboard.text()
    #     if text:
    #         self.url_input.setText(text)

    # def copy_to_clipboard(self):
    #     """复制链接到剪贴板"""
    #     clipboard = QApplication.clipboard()
    #     clipboard.setText(self.parsed_url)
    #     # 该种提示框，需要手动关闭
    #     # QMessageBox.information(self, '提示', '链接已复制到剪贴板！')
    #     # 使用自动关闭的提示框，2秒后自动关闭
    #     self.show_auto_close_info('提示', '链接已复制到剪贴板！')

    # def on_select_directory(self):
    #     """选择下载保存目录"""
    #     directory = QFileDialog.getExistingDirectory(
    #         self,
    #         '选择下载保存目录',
    #         os.path.expanduser('~/Downloads'),
    #         QFileDialog.ShowDirsOnly
    #     )
    #     if directory:
    #         self.output_path_input.setText(directory)

    def on_parse_click(self):
        """处理解析按钮点击"""
        video_url = self.url_input.text().strip()

        if not video_url:
            QMessageBox.warning(self, '警告', '请输入视频链接！')
            return

        api_key = self.api_combo.currentData()
        # api_key: {'name': '万能稳定解析', 'note': '推荐使用', 'status': 'active', 'url': 'https://jx.m3u8.tv/jiexi/?url='}
        print(f"api_key: {api_key}")

        # 不使用 clear()，因为会清掉之前的详细日志
        # 改为加分隔线追加，保留历史日志
        self.result_text.append(f"\n{'='*50}")
        self.result_text.append(f"正在解析: {video_url}")
        self.result_text.append(f"使用线路: {self.api_combo.currentText().split(' ')[1]}")
        self.result_text.append(f"{'='*50}")

        result = self.parser.parse_url(video_url, api_key)

        if result['success']:
            self.parsed_url = result['data']['parsed_url']
            self.original_url = video_url

            selected_platform = self.platform_combo.currentText()
            if selected_platform == '自动检测':
                platform = self.parser.detect_platform(video_url)
                # 自动选中检测到的平台
                platforms = ['自动检测', '腾讯视频', '优酷', '哔哩哔哩', '爱奇艺', '芒果TV', '搜狐视频', 'PP视频',
                             '乐视视频', '土豆视频', 'AcFun']
                if platform in platforms:
                    self.platform_combo.setCurrentText(platform)
            else:
                platform = selected_platform

            self.result_text.append("\n解析成功！")
            self.result_text.append(f"视频平台: {platform}")
            self.result_text.append(f"原始视频链接: {self.original_url}")
            self.result_text.append(f"解析后的链接: {self.parsed_url}")

            self.open_btn.setEnabled(True)
            # self.copy_btn.setEnabled(True)
            self.download_btn.setEnabled(True)
            # if platform in ['腾讯视频', '爱奇艺']:
                # self.next_btn.setEnabled(True)
                # self.batch_download_btn.setEnabled(True)
                # self.episode_list_btn.setEnabled(True)
            # else:
                # self.next_btn.setEnabled(False)
                # self.batch_download_btn.setEnabled(False)
                # self.episode_list_btn.setEnabled(False)
        else:
            self.result_text.append(f"\n解析失败: {result['message']}")
            self.open_btn.setEnabled(False)
            # self.copy_btn.setEnabled(False)
            # self.download_btn.setEnabled(False)
            # self.next_btn.setEnabled(False)
            # self.batch_download_btn.setEnabled(False)
            # self.episode_list_btn.setEnabled(False)

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
                # self.show_auto_close_info('提示', '浏览器已打开！')
                print(f"浏览器已打开,链接为: {self.parsed_url}")
                self.result_text.append(f"浏览器已打开,链接为: {self.parsed_url}")
            else:
                QMessageBox.warning(self, '警告', '打开浏览器失败，请手动复制链接！')

    def on_play_click(self):
        """在浏览器中播放视频"""
        if not hasattr(self, 'parsed_url'):
            QMessageBox.warning(self, '警告', '请先解析视频链接！')
            return
        # 直接调用浏览器播放
        self.on_open_browser()

    def _append_log_line(self, line):
        """
        追加一行日志到结果文本框。
        这个方法由日志桥接器的信号触发，始终在主线程执行，安全。
        
        只有当用户勾选了"显示详细日志"时才显示。
        日志是追加的（不是覆盖），并且自动滚动到底部。
        
        注意：初始化顺序问题
        - 全局日志拦截在 init_ui() 之前就设置了
        - log_checkbox 在 init_ui() 里才创建
        - 所以早期的 print 可能触发这个方法，此时 log_checkbox 还不存在
        - 用 hasattr 检查避免 AttributeError
        """
        # 防止初始化顺序问题：log_checkbox 可能还没创建
        if hasattr(self, 'log_checkbox') and self.log_checkbox.isChecked():
            self.result_text.append(line)
            # 自动滚动到底部，保证最新的日志始终可见
            cursor = self.result_text.textCursor()
            cursor.movePosition(cursor.End)
            self.result_text.setTextCursor(cursor)

    def _on_log_toggled(self, state):
        """
        用户点击"显示详细日志"复选框时触发。
        state: Qt.Checked(2) 或 Qt.Unchecked(0)
        """
        if state == Qt.Checked:
            self.result_text.append("\n--- 详细日志已开启 ---")
        else:
            self.result_text.append("\n--- 详细日志已关闭 ---")

    def on_download_click(self):
        """使用 yt-dlp 下载视频（直接下载原始视频URL）"""
        if not hasattr(self, 'parsed_url'):
            QMessageBox.warning(self, '警告', '请先解析视频链接！')
            return

        # 选择下载保存目录
        output_path = QFileDialog.getExistingDirectory(
            self,
            '选择下载保存目录',
            os.path.expanduser('~/Downloads'),
            QFileDialog.ShowDirsOnly
        )
        if not output_path:
            return

        # 获取画质选择（取下拉框文本的第一段，如 "best - 最佳画质" -> "best"）
        quality_text = self.quality_combo.currentText()
        quality = quality_text.split(' ')[0]

        # 使用原始视频URL进行下载（yt-dlp 直接支持各大视频平台的原始链接）
        download_url = self.original_url if hasattr(self, 'original_url') else self.parsed_url

        self.result_text.append(f"\n{'='*40}")
        self.result_text.append(f"开始下载: {download_url}")
        self.result_text.append(f"保存目录: {output_path}")
        self.result_text.append(f"画质: {quality}")
        self.result_text.append(f"{'='*40}")

        # 禁用按钮，显示进度条
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度模式（滚动条）

        # 启动下载线程
        # 注意：下载过程中的所有 print 输出都会被全局 LogStream 拦截，
        # 如果用户勾选了"显示详细日志"，就会自动显示在解析结果文本框中
        self.download_thread = DownloadThread(download_url, output_path, quality)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.start()

        # 旧的 aria2c 实现方式（已弃用，改用 yt-dlp 原生下载）
        # import time
        # ts = int(time.time() * 1000)
        # download_cmd=f'yt-dlp --external-downloader aria2c --external-downloader-args "-x 8 -s 8 -k 1M" --concurrent-fragments 4 "{self.original_url}" -o "{ts}.mp4"'

    def on_download_finished(self, result):
        """下载完成处理"""
        self.progress_bar.setVisible(False)
        self.download_btn.setEnabled(True)

        if result['success']:
            self.result_text.append(f"\n✅ {result['message']}")
            QMessageBox.information(self, '下载成功', f"视频下载成功！\n保存位置: {result['data']['output_path']}")
        else:
            self.result_text.append(f"\n❌ {result['message']}")
            QMessageBox.warning(self, '下载失败', result['message'])

    # def on_batch_download_click(self):
    #     """处理批量下载按钮点击"""
    #     video_url = self.url_input.text().strip()
    #     if not video_url:
    #         QMessageBox.warning(self, '警告', '请输入视频链接！')
    #         return
    #
    #     # 检查保存目录
    #     output_path = self.output_path_input.text().strip()
    #     if not output_path:
    #         output_path = QFileDialog.getExistingDirectory(
    #             self,
    #             '选择下载保存目录',
    #             os.path.expanduser('~/Downloads'),
    #             QFileDialog.ShowDirsOnly
    #         )
    #         if not output_path:
    #             QMessageBox.warning(self, '警告', '请选择下载保存目录！')
    #             return
    #         self.output_path_input.setText(output_path)
    #
    #     platform = self.parser.detect_platform(video_url)
    #     if platform not in ['腾讯视频', '爱奇艺']:
    #         QMessageBox.warning(self, '警告', f'暂不支持{platform}的批量下载')
    #         return
    #
    #     # 获取下载集数限制
    #     max_episodes = self.max_episodes_spin.value()
    #     if max_episodes == 0:
    #         max_episodes = None
    #
    #     quality = self.batch_quality_combo.currentText().split(' ')[0]
    #     api_key = self.api_combo.currentData()
    #     max_workers = self.thread_spin.value()
    #
    #     # 确认对话框
    #     reply = QMessageBox.question(
    #         self,
    #         '批量下载确认',
    #         f'即将开始批量下载，保存目录: {output_path}\n'
    #         f'下载集数: {max_episodes if max_episodes else "全部"}\n'
    #         f'并发数: {max_workers} 线程\n'
    #         f'画质: {quality}\n'
    #         f'是否继续？',
    #         QMessageBox.Yes | QMessageBox.No
    #     )
    #
    #     if reply != QMessageBox.Yes:
    #         return
    #
    #     self.result_text.append(f"\n开始批量下载电视剧...")
    #     self.result_text.append(f"保存目录: {output_path}")
    #     self.result_text.append(f"画质: {quality}")
    #     self.result_text.append(f"并发数: {max_workers} 线程")
    #
    #     self.batch_download_btn.setEnabled(False)
    #     self.batch_progress_bar.setVisible(True)
    #     self.batch_progress_bar.setRange(0, 100)
    #     self.batch_progress_bar.setValue(0)
    #
    #     self.batch_thread = BatchDownloadThread(
    #         video_url, output_path, quality, api_key, max_episodes, max_workers
    #     )
    #     self.batch_thread.progress.connect(self.on_batch_progress)
    #     self.batch_thread.finished.connect(self.on_batch_finished)
    #     self.batch_thread.start()

    # def on_batch_progress(self, completed, total, status, message):
    #     """批量下载进度更新"""
    #     self.result_text.append(message)
    #     if total > 0:
    #         progress = int((completed / total) * 100)
    #         self.batch_progress_bar.setValue(min(progress, 100))

    # def on_batch_finished(self, result):
    #     """批量下载完成处理"""
    #     self.batch_progress_bar.setVisible(False)
    #     self.batch_download_btn.setEnabled(True)
    #
    #     if result['success']:
    #         data = result['data']
    #         msg = (
    #             f"批量下载完成！\n\n"
    #             f"成功: {len(data['downloaded'])} 集\n"
    #             f"失败: {len(data['failed'])} 集\n"
    #             f"总计: {data['total']} 集\n"
    #             f"保存位置: {data['output_path']}"
    #         )
    #         QMessageBox.information(self, '批量下载完成', msg)
    #     else:
    #         QMessageBox.warning(self, '批量下载失败', result['message'])

    def open_platform(self, url):
        """打开视频平台"""
        self.parser.open_in_browser(url)

    # def on_episode_list_click(self):
    #     """处理获取全部剧集按钮点击"""
    #     if not hasattr(self, 'original_url'):
    #         QMessageBox.warning(self, '警告', '请先解析视频链接！')
    #         return
    #
    #     video_url = self.original_url
    #     platform = self.parser.detect_platform(video_url)
    #
    #     if platform not in ['腾讯视频', '爱奇艺']:
    #         QMessageBox.warning(self, '警告', f'暂不支持{platform}的获取剧集列表功能')
    #         return
    #
    #     self.result_text.append(f"\n正在获取全部剧集列表...")
    #     self.result_text.append(f"请稍候，这可能需要几秒钟...")
    #     self.episode_list_btn.setEnabled(False)
    #
    #     self.episode_list_thread = EpisodeListThread(video_url)
    #     self.episode_list_thread.progress.connect(self.on_episode_list_progress)
    #     self.episode_list_thread.finished.connect(self.on_episode_list_finished)
    #     self.episode_list_thread.start()

    # def on_episode_list_progress(self, message):
    #     """获取剧集列表进度"""
    #     self.result_text.append(message)

    # def on_episode_list_finished(self, result):
    #     """获取剧集列表完成"""
    #     self.episode_list_btn.setEnabled(True)
    #
    #     if result['success']:
    #         data = result['data']
    #         episodes = data['episodes']
    #         total = data['total']
    #
    #         self.result_text.append(f"\n{'=' * 60}")
    #         self.result_text.append(f"📺 平台: {data['platform']}")
    #         self.result_text.append(f"✅ 共找到 {total} 集")
    #         self.result_text.append(f"{'=' * 60}")
    #         self.result_text.append(f"{'集数':<8} {'链接'}")
    #         self.result_text.append(f"{'-' * 60}")
    #
    #         for ep in episodes:
    #             self.result_text.append(f"第{ep['episode_num']:<4}集  {ep['url']}")
    #
    #         self.result_text.append(f"{'=' * 60}")
    #         self.result_text.append(f"\n提示：可以通过\"批量下载\"功能下载全部剧集")
    #
    #         QMessageBox.information(
    #             self, '获取成功',
    #             f"已获取 {total} 集的剧集列表！\n\n"
    #             f"可以使用\"批量下载全部剧集\"功能进行下载。"
    #         )
    #     else:
    #         self.result_text.append(f"\n❌ 获取剧集列表失败: {result['message']}")
    #         QMessageBox.warning(self, '获取失败', result['message'])

    # def on_next_episode(self):
    #     """处理下一集按钮点击"""
    #     if not hasattr(self, 'original_url'):
    #         QMessageBox.warning(self, '警告', '请先解析视频链接！')
    #         return
    #
    #     current_url = self.original_url
    #     platform = self.parser.detect_platform(current_url)
    #
    #     if platform not in ['腾讯视频', '爱奇艺']:
    #         QMessageBox.warning(self, '警告', f'暂不支持{platform}的自动获取下一集功能')
    #         return
    #
    #     self.result_text.append(f"\n正在获取下一集...")
    #     self.next_btn.setEnabled(False)
    #
    #     self.next_thread = NextEpisodeThread(current_url)
    #     self.next_thread.finished.connect(self.on_next_episode_finished)
    #     self.next_thread.start()

    # def on_next_episode_finished(self, result):
    #     """下一集获取完成处理"""
    #     self.next_btn.setEnabled(True)
    #
    #     if result['success']:
    #         next_url = result['data']['next_url']
    #         episode_num = result['data']['episode_num']
    #
    #         self.result_text.append(f"找到下一集：第{episode_num}集")
    #
    #         reply = QMessageBox.question(
    #             self,
    #             '下一集',
    #             f'已找到第{episode_num}集，是否自动解析？',
    #             QMessageBox.Yes | QMessageBox.No
    #         )
    #
    #         if reply == QMessageBox.Yes:
    #             self.url_input.setText(next_url)
    #             self.on_parse_click()
    #     else:
    #         self.result_text.append(f"{result['message']}")
    #         QMessageBox.warning(self, '获取下一集失败', result['message'])


def get_icon_path():
    """获取图标文件路径，支持打包后运行"""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'icon.ico')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')


def main():
    """图形界面入口函数"""
    # 让 Ctrl+C 能够正常终止程序
    # PyQt5 的事件循环会阻塞 Python 的信号处理，
    # 因此需要设置默认的信号处理方式让系统直接处理 SIGINT
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)

    icon_path = get_icon_path()
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
