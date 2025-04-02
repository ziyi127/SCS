import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QSlider, 
                             QProgressBar, QSystemTrayIcon, QMessageBox, QHBoxLayout, QComboBox, 
                             QPushButton, QCheckBox, QGroupBox, QTabWidget, QSpinBox, QTextEdit, QMenu, QFileDialog, QFrame)
from PyQt5.QtCore import Qt, QPoint, QSize, QSettings, QEvent, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QIcon, QColor, QPalette, QScreen, QCursor, QPainter, QFont
from time_manager import TimeManager
from course_manager import CourseManager
from notification_manager import NotificationManager
from ui_config import UIConfig
from config import Config
from plugin_manager import PluginManager
import logging

class CourseCapsuleWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._windowOpacity = 0.9
        self.setFixedSize(160, 48)
        
        # 课程状态显示
        self.course_status_label = QLabel("当前暂无课程", self)
        self.course_status_label.setStyleSheet("font-size: 14px; color: white; font-weight: bold;")
        self.course_status_label.setAlignment(Qt.AlignCenter)
        self.course_status_label.setGeometry(0, 0, 160, 48)
        
    def opacity(self):
        return self._windowOpacity
        
    def setOpacity(self, value):
        self._windowOpacity = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制灵动岛风格背景
        painter.setBrush(QColor(30, 30, 30, 200))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 24, 24)

    def windowOpacity(self):
        return self._windowOpacity

    def setWindowOpacity(self, value):
        self._windowOpacity = value
        self.update()

class SCSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # 加载配置
        Config.load_from_file()
        
        # 设置日志
        self.setup_logging()
        
        # 初始化管理器
        self.time_manager = TimeManager()
        self.course_manager = CourseManager()
        self.notification_manager = NotificationManager(self.course_manager)
        self.ui_config = UIConfig()
        self.plugin_manager = PluginManager()
        self.settings = QSettings('SCS', 'Preferences')
        
        # 连接信号
        self.notification_manager.weather_updated.connect(self.update_weather_display)
        self.notification_manager.notification_triggered.connect(self.show_notification)
        self.ui_config.theme_updated.connect(self.apply_theme)
        self.plugin_manager.plugin_loaded.connect(self.on_plugin_loaded)
        self.plugin_manager.plugin_error.connect(self.on_plugin_error)
        
        # 初始化界面
        self.initUI()
        
        # 初始化界面状态
        self.simplified_mode = False
        self.mouse_hover = False
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.on_hover_timeout)
        
        # 加载插件
        self.plugin_manager.load_plugins()
        
        # 应用壁纸适配
        try:
            self.apply_wallpaper_theme()
        except Exception as e:
            logging.warning(f"壁纸适配失败: {str(e)}")
    
    def setup_logging(self):
        """设置日志"""
        log_level = getattr(logging, Config.LOG_LEVEL)
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # 设置根日志记录器
        logging.basicConfig(level=log_level, format=log_format)
        
        # 如果需要记录到文件
        if Config.LOG_TO_FILE:
            file_handler = logging.FileHandler(Config.LOG_FILE_PATH, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(log_format))
            logging.getLogger().addHandler(file_handler)
    
    def position_window(self, position):
        """根据配置定位窗口位置"""
        screen = QApplication.desktop().availableGeometry(self)
        window_size = self.size()
        
        # 计算窗口位置时考虑多显示器情况
        target_screen = QApplication.desktop().screenNumber(QCursor.pos())
        screen_geo = QApplication.desktop().screenGeometry(target_screen)
        
        window_width = min(window_size.width(), screen_geo.width())
        window_height = min(window_size.height(), screen_geo.height())
        
        if position == 'top':
            new_x = screen_geo.x() + screen_geo.width() - window_width
            new_y = screen_geo.y()
        elif position == 'bottom':
            new_x = screen_geo.x() + screen_geo.width() - window_width
            new_y = screen_geo.y() + screen_geo.height() - window_height
        elif position == 'left':
            new_x = screen_geo.x()
            new_y = screen_geo.y() + (screen_geo.height() - window_height) // 2
        elif position == 'right':
            new_x = screen_geo.x() + screen_geo.width() - window_width
            new_y = screen_geo.y() + (screen_geo.height() - window_height) // 2
        else:  # center
            new_x = screen_geo.x() + (screen_geo.width() - window_width) // 2
            new_y = screen_geo.y() + (screen_geo.height() - window_height) // 2
        
        # 强制窗口保持在屏幕可见区域
        new_x = max(screen_geo.x(), min(new_x, screen_geo.x() + screen_geo.width() - window_width))
        new_y = max(screen_geo.y(), min(new_y, screen_geo.y() + screen_geo.height() - window_height))
        
        self.move(new_x, new_y)
        self.force_inside_screen()
    
    def force_inside_screen(self):
        """强制窗口保持在当前屏幕可见区域内"""
        current_screen = QApplication.desktop().screenGeometry(self)
        geo = self.geometry()
        
        new_x = max(current_screen.x(), min(geo.x(), current_screen.x() + current_screen.width() - geo.width()))
        new_y = max(current_screen.y(), min(geo.y(), current_screen.y() + current_screen.height() - geo.height()))
        
        if new_x != geo.x() or new_y != geo.y():
            self.move(new_x, new_y)
    
    def on_screen_changed(self):
        """屏幕分辨率或布局变化时的处理"""
        self.force_inside_screen()
        self.updateGeometry()
    
    def resizeEvent(self, event):
        """窗口大小改变时保持边界"""
        super().resizeEvent(event)
        self.force_inside_screen()
    
    def moveEvent(self, event):
        """窗口移动时实时校验位置"""
        super().moveEvent(event)
        self.force_inside_screen()
                     
    def show_course_schedule(self):
        """显示今日课程表"""
        from PyQt5.QtWidgets import QMessageBox
        
        courses = self.course_manager.get_today_schedule()
        if not courses:
            QMessageBox.information(self, "课程表", "今日无课程安排")
            return
            
        message = "今日课程:\n"
        for course in courses:
            message += f"{course['start_time']}-{course['end_time']}: {course['name']}\n"
            
        QMessageBox.information(self, "课程表", message)
        
    def show_add_course_dialog(self):
        """显示添加课程对话框"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "添加课程", "添加课程功能待实现")
        
    def show_edit_course_dialog(self):
        """显示编辑课程对话框"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "编辑课程", "编辑课程功能待实现")
        
    def create_tray_icon(self):
        """创建系统托盘图标"""
        self.tray_icon = QSystemTrayIcon(self)
        try:
            # 尝试多种方式加载图标
            icon_paths = [
                os.path.join(os.path.dirname(__file__), "img", "icon.svg"),  # 相对路径
                os.path.join(os.path.abspath("."), "img", "icon.svg"),       # 绝对路径
                "icon.svg"                                                    # 直接文件名
            ]
            
            icon_loaded = False
            for path in icon_paths:
                logging.info(f"尝试加载托盘图标路径: {path}")
                if os.path.exists(path):
                    self.tray_icon.setIcon(QIcon(path))
                    logging.info(f"托盘图标加载成功: {path}")
                    icon_loaded = True
                    break
            
            if not icon_loaded:
                logging.error("所有尝试的图标路径均无效，使用默认图标")
                self.tray_icon.setIcon(QIcon.fromTheme("applications-other"))
        except Exception as e:
            logging.error(f"加载托盘图标失败: {str(e)}", exc_info=True)
            self.tray_icon.setIcon(QIcon.fromTheme("applications-other"))
        self.tray_icon.setToolTip("SCS智慧电子课程表")
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        # 课程相关操作
        course_menu = tray_menu.addMenu("课程")
        course_menu.addAction("查看今日课程").triggered.connect(self.show_course_schedule)
        course_menu.addAction("添加课程").triggered.connect(self.show_add_course_dialog)
        course_menu.addAction("编辑课程").triggered.connect(self.show_edit_course_dialog)
        
        # 课表管理
        timetable_menu = tray_menu.addMenu("课表管理")
        timetable_menu.addAction("导入课表").triggered.connect(self.show_timetable_import)
        timetable_menu.addAction("编辑课表").triggered.connect(self.show_timetable_editor)
        
    def show_timetable_import(self):
        """显示课表导入对话框"""
        from timetable_editor import TimetableEditor
        editor = TimetableEditor(self.course_manager)
        editor.import_from_excel()
        
    def show_timetable_editor(self):
        """显示课表编辑器"""
        from timetable_editor import TimetableEditor
        editor = TimetableEditor(self.course_manager)
        editor.show()
        
        # 设置相关
        settings_menu = tray_menu.addMenu("设置")
        settings_menu.addAction("界面主题").triggered.connect(self.show_theme_settings)
        settings_menu.addAction("课程管理").triggered.connect(self.show_course_schedule)
        settings_menu.addAction("通知设置").triggered.connect(self.show_notification_settings)
        
        # 确保托盘菜单正确关联
        self.tray_icon.setContextMenu(tray_menu)
        
        # 窗口控制
        tray_menu.addSeparator()
        tray_menu.addAction("显示窗口").triggered.connect(self.show)
        tray_menu.addAction("隐藏窗口").triggered.connect(self.hide)
        tray_menu.addAction("切换模式").triggered.connect(self.toggle_simplified_mode)
        
        # 系统操作
        tray_menu.addSeparator()
        tray_menu.addAction("退出").triggered.connect(QApplication.quit)
        
        # 设置托盘菜单并显示
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
    def show_theme_settings(self):
        """显示主题设置对话框"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "主题设置", "主题设置功能待实现")
    
    def initUI(self):
        self.setWindowTitle("SCS智慧电子课程表")
        
        # 获取屏幕尺寸并计算初始位置
        screen = QApplication.primaryScreen().availableGeometry()
        window_width = 800
        window_height = 600
        
        # 设置窗口初始位置和尺寸
        # 确保窗口尺寸不超过屏幕可用区域
        window_width = min(window_width, screen.width())
        window_height = min(window_height, screen.height())
        
        # 计算并确保窗口位置在屏幕范围内
        # 确保窗口尺寸不超过屏幕可用区域
        window_width = min(window_width, screen.width())
        window_height = min(window_height, screen.height())

        # 精确计算初始位置（右上角）
        x_pos = max(0, screen.width() - window_width)
        y_pos = 0

        # 设置窗口几何尺寸并添加边界校验
        self.setGeometry(
            max(0, min(x_pos, screen.width() - window_width)),
            max(0, min(y_pos, screen.height() - window_height)),
            window_width,
            window_height
        )
        
        # 设置窗口标志
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        
        # 添加窗口移动事件处理
        self.oldPos = self.pos()
        self.dragging = False
        
        # 添加Mica效果
        if self.ui_config.theme['mica_enabled']:
            try:
                import ctypes
                from ctypes import wintypes
                DWMWA_USE_HOSTBACKDROPBRUSH = 18
                DWMWA_SYSTEMBACKDROP_TYPE = 38
                DWM_SYSTEMBACKDROP_TYPE_MICA = 2
                
                hwnd = self.winId()
                value = ctypes.c_int(DWM_SYSTEMBACKDROP_TYPE_MICA)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_SYSTEMBACKDROP_TYPE,
                    ctypes.byref(value),
                    ctypes.sizeof(value)
                )
            except Exception as e:
                logging.warning(f"Mica效果不可用: {str(e)}")
        
        # 设置背景透明
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_AlwaysStackOnTop)
        self.setStyleSheet("""
            background: transparent;
            border: none;
            border-radius: 10px;
            QWidget {
                background: transparent;
            }
        """)
        
        # 安装事件过滤器以处理鼠标事件
        if Config.HOVER_SHOW_FULL:
            self.installEventFilter(self)
        
        # 应用主题设置
        theme = self.ui_config.get_theme()
        opacity_value = theme['opacity'] / 100.0  # 将0-100的值转换为0.0-1.0
        self.setWindowOpacity(opacity_value)
        logging.info(f"应用窗口不透明度: {opacity_value}")
        
        # 设置窗口初始位置并强制刷新
        self.position_window(theme['position'])
        self.adjustSize()
        self.updateGeometry()
        
        # 屏幕缩放变化处理
        QApplication.instance().primaryScreen().virtualGeometryChanged.connect(self.on_screen_changed)
        
        # 创建系统托盘图标
        self.create_tray_icon()
        
        # 主窗口布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout()
        main_widget.setLayout(self.main_layout)
        
        # 顶部工具栏
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(5, 5, 5, 5)
        
        # 周次指示器
        from PyQt5.QtSvg import QSvgWidget
        self.week_indicator = QSvgWidget("img/course/week_indicator.svg")
        self.week_indicator.setFixedSize(100, 30)
        top_bar_layout.addWidget(self.week_indicator)
        
        # 时间显示
        self.time_label = QLabel("当前时间: ")
        self.time_label.setAlignment(Qt.AlignCenter)
        top_bar_layout.addWidget(self.time_label, 1)
        
        # 设置按钮
        self.settings_button = QPushButton("设置")
        self.settings_button.clicked.connect(self.show_settings_dialog)
        self.settings_button.setFixedSize(60, 30)
        top_bar_layout.addWidget(self.settings_button)
        
        self.main_layout.addWidget(top_bar)
        
        # 主内容区域
        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)
        
        # 左侧课程列表区域
        course_list_widget = QWidget()
        course_list_layout = QVBoxLayout(course_list_widget)
        
        # 课程展示区域
        # 动态胶囊课程显示
        self.course_capsule = CourseCapsuleWidget()
        course_list_layout.addWidget(self.course_capsule)

        # 呼吸灯动画
        self.breath_animation = QPropertyAnimation(self.course_capsule, b"opacity")
        self.breath_animation.setDuration(3000)
        self.breath_animation.setLoopCount(-1)
        self.breath_animation.setStartValue(0.7)
        self.breath_animation.setEndValue(0.95)
        self.breath_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.breath_animation.start()
        
        content_layout.addWidget(course_list_widget, 2)
        
        # 右侧当前课程详情区域
        course_detail_widget = QWidget()
        course_detail_layout = QVBoxLayout(course_detail_widget)
        
        # 当前课程信息
        current_course_info = QWidget()
        current_course_layout = QVBoxLayout(current_course_info)
        
        self.current_course_label = QLabel("当前课程: 无")
        self.current_course_label.setAlignment(Qt.AlignCenter)
        self.current_course_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        current_course_layout.addWidget(self.current_course_label)
        
        # 课程进度指示器
        self.progress_indicator = QSvgWidget("img/course/progress_indicator.svg")
        self.progress_indicator.setFixedSize(100, 100)
        current_course_layout.addWidget(self.progress_indicator, 0, Qt.AlignCenter)
        
        # 进度条
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(10, 0, 10, 0)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("QProgressBar {border: 1px solid #cccccc; border-radius: 5px; text-align: center;} QProgressBar::chunk {background-color: #4a86e8;}")
        progress_layout.addWidget(self.progress_bar)
        
        current_course_layout.addWidget(progress_widget)
        
        # 下节课信息
        self.next_course_label = QLabel("下节课: 无")
        self.next_course_label.setAlignment(Qt.AlignCenter)
        self.next_course_label.setStyleSheet("font-size: 12pt;")
        current_course_layout.addWidget(self.next_course_label)
        
        course_detail_layout.addWidget(current_course_info)
        
        # 天气信息显示
        weather_widget = QWidget()
        weather_layout = QHBoxLayout(weather_widget)
        
        self.weather_icon = QSvgWidget("img/weather/weather_display.svg")
        self.weather_icon.setFixedSize(60, 60)
        weather_layout.addWidget(self.weather_icon)
        
        self.weather_label = QLabel("天气信息加载中...")
        self.weather_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.weather_label.setWordWrap(True)
        weather_layout.addWidget(self.weather_label)
        
        course_detail_layout.addWidget(weather_widget)
        
        content_layout.addWidget(course_detail_widget, 1)
        
        self.main_layout.addWidget(content_area, 1)
        
        # 底部控制区域
        control_area = QWidget()
        control_layout = QHBoxLayout(control_area)
        

        
        # 课程提醒设置
        
        self.main_layout.addWidget(control_area)
        
        # 创建简化界面
        self.simplified_layout = QVBoxLayout()
        self.simplified_widget = QWidget()
        
        # 简化界面顶部栏
        simplified_top = QWidget()
        simplified_top_layout = QHBoxLayout(simplified_top)
        simplified_top_layout.setContentsMargins(5, 5, 5, 5)
        
        # 简化界面当前课程标签
        self.simplified_course_label = QLabel("当前课程: 无")
        self.simplified_course_label.setAlignment(Qt.AlignCenter)
        self.simplified_course_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        simplified_top_layout.addWidget(self.simplified_course_label, 1)
        
        self.simplified_layout.addWidget(simplified_top)
        
        # 简化界面进度条
        simplified_progress = QWidget()
        simplified_progress_layout = QHBoxLayout(simplified_progress)
        simplified_progress_layout.setContentsMargins(5, 0, 5, 0)
        
        self.simplified_progress = QProgressBar()
        self.simplified_progress.setRange(0, 100)
        self.simplified_progress.setTextVisible(True)
        self.simplified_progress.setFormat("%p%")
        self.simplified_progress.setStyleSheet("QProgressBar {border: 1px solid #cccccc; border-radius: 5px; text-align: center;} QProgressBar::chunk {background-color: #4a86e8;}")
        simplified_progress_layout.addWidget(self.simplified_progress)
        
        self.simplified_layout.addWidget(simplified_progress)
        
        # 简化界面下节课信息
        self.simplified_next_label = QLabel("下节课: 无")
        self.simplified_next_label.setAlignment(Qt.AlignCenter)
        self.simplified_layout.addWidget(self.simplified_next_label)
        
        # 创建简化界面
        self.simplified_widget = QWidget()
        self.simplified_widget.setLayout(self.simplified_layout)
        self.simplified_widget.setVisible(False)
        
        # 将简化界面添加到主布局
        self.main_layout.addWidget(self.simplified_widget)
        
        main_widget.setLayout(self.main_layout)
        
        # 连接信号
        self.time_manager.time_updated.connect(self.update_time_display)
        self.course_manager.course_updated.connect(self.update_course_display)
    
    def update_time_display(self):
        current_time = self.time_manager.get_current_time().strftime('%Y-%m-%d %H:%M:%S')
        self.time_label.setText(f"当前时间: {current_time}")
    
    def update_course_display(self):
        from datetime import datetime
        import re
        from PyQt5.QtSvg import QSvgRenderer
        from PyQt5.QtCore import QByteArray
        
        # 获取当前周次类型
        week_type = self.course_manager.get_current_week_type()
        
        # 更新周次指示器
        week_svg = """
        <svg width="100" height="50" viewBox="0 0 100 50" xmlns="http://www.w3.org/2000/svg">
          <rect x="5" y="5" width="90" height="40" rx="5" ry="5" fill="#f5f5f5" stroke="#cccccc" stroke-width="1" />
          <g id="oddWeek">
            <circle cx="30" cy="25" r="15" fill="{odd_color}" />
            <text x="30" y="30" font-family="Arial" font-size="14" fill="{odd_text_color}" text-anchor="middle">单</text>
          </g>
          <g id="evenWeek">
            <circle cx="70" cy="25" r="15" fill="{even_color}" />
            <text x="70" y="30" font-family="Arial" font-size="14" fill="{even_text_color}" text-anchor="middle">双</text>
          </g>
        </svg>
        """
        
        if week_type == 'odd':
            week_svg = week_svg.format(
                odd_color="#4a86e8", odd_text_color="white",
                even_color="#f5f5f5", even_text_color="#666666"
            )
        else:  # even
            week_svg = week_svg.format(
                odd_color="#f5f5f5", odd_text_color="#666666",
                even_color="#4a86e8", even_text_color="white"
            )
        
        self.week_indicator.renderer().load(QByteArray(week_svg.encode()))
        
        # 获取今日课程
        courses = self.course_manager.get_today_schedule()
        current_course = None
        next_course = None
        
        if courses:
            course_text = "<h3>今日课程:</h3>"
            current_course_found = False
            
            for course in courses:
                # 设置课程颜色和状态
                course_color = course.get('color', '#4a86e8')
                status = "<span style='color:#ff9900; font-weight:bold;'>[进行中]</span>" if course.get('is_current', False) else ""
                progress = course.get('progress', 0)
                
                # 构建课程信息HTML
                course_text += f"<div style='margin-bottom:10px; padding:5px; border-left:3px solid {course_color};'>"
                course_text += f"<b style='color:{course_color};'>{course['name']}</b> - {course['teacher']} {status}<br>"
                course_text += f"时间: {course['start_time']}-{course['end_time']}<br>"
                
                if course.get('is_current', False):
                    current_course = course
                    current_course_found = True
                    self.progress_bar.setValue(progress)
                    self.simplified_progress.setValue(progress)
                    
                    # 更新进度指示器SVG
                    progress_svg = """
                    <svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                      <defs>
                        <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stop-color="{color}" />
                          <stop offset="100%" stop-color="{accent_color}" />
                        </linearGradient>
                      </defs>
                      <circle cx="50" cy="50" r="45" fill="none" stroke="#e0e0e0" stroke-width="8" />
                      <path d="{arc_path}" fill="none" stroke="url(#progressGradient)" stroke-width="8" stroke-linecap="round" />
                      <text x="50" y="55" font-family="Arial" font-size="20" fill="#333333" text-anchor="middle">{progress}%</text>
                    </svg>
                    """
                    
                    # 计算圆弧路径
                    if progress > 0:
                        angle = 3.6 * progress  # 360度 * progress / 100
                        # 转换为SVG路径
                        if progress >= 100:
                            arc_path = "M50,5 A45,45 0 1,1 49.9,5"  # 完整圆
                        else:
                            rad = angle * (3.14159 / 180)  # 角度转弧度
                            x = 50 + 45 * math.sin(rad)
                            y = 50 - 45 * math.cos(rad)
                            large_arc = 1 if angle > 180 else 0
                            arc_path = f"M50,5 A45,45 0 {large_arc},1 {x},{y}"
                    else:
                        arc_path = "M50,5 A45,45 0 0,1 50,5"  # 0进度
                    
                    # 使用课程颜色
                    progress_svg = progress_svg.format(
                        color=course_color,
                        accent_color=self.ui_config.theme['accent_color'],
                        arc_path=arc_path,
                        progress=progress
                    )
                    
                    self.progress_indicator.renderer().load(QByteArray(progress_svg.encode()))
                    
                    # 添加课程详细信息
                    if 'notes' in course and course['notes']:
                        course_text += f"备注: {course['notes']}<br>"
                    if 'classroom' in course and course['classroom']:
                        course_text += f"教室: {course['classroom']}<br>"
                        if 'distance' in course and course['distance'] > 0:
                            course_text += f"距离: 约{course['distance']}米<br>"
                elif course.get('coming_soon', False) and not next_course:
                    next_course = course
                
                course_text += "</div>"
            
            if not current_course_found:
                self.progress_bar.setValue(0)
                self.simplified_progress.setValue(0)
                
                # 重置进度指示器
                progress_svg = """
                <svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="50" cy="50" r="45" fill="none" stroke="#e0e0e0" stroke-width="8" />
                  <text x="50" y="55" font-family="Arial" font-size="20" fill="#333333" text-anchor="middle">0%</text>
                </svg>
                """
                self.progress_indicator.renderer().load(QByteArray(progress_svg.encode()))
                
                # 显示最近的下一节课
                if not next_course:
                    next_course = self.notification_manager.get_next_course(None, courses)
                
                if next_course:
                    time_until_start = self.time_manager.get_time_until_next_event(
                        datetime.strptime(next_course['start_time'], '%H:%M').replace(
                            year=datetime.now().year, month=datetime.now().month, day=datetime.now().day
                        )
                    )
                    minutes_until = int(time_until_start.total_seconds() / 60)
                    course_text += f"<div style='margin-top:15px; padding:10px; background-color:rgba(74, 134, 232, 0.1); border-radius:5px;'>"
                    course_text += f"<h3>下节课预告:</h3>"
                    course_text += f"<b style='color:{next_course.get('color', '#4a86e8')};'>{next_course['name']}</b> - {next_course['teacher']}<br>"
                    course_text += f"时间: {next_course['start_time']}-{next_course['end_time']}<br>"
                    course_text += f"<b>距离开始还有: {minutes_until}分钟</b><br>"
                    if 'classroom' in next_course and next_course['classroom']:
                        course_text += f"教室: {next_course['classroom']}<br>"
                        if 'distance' in next_course and next_course['distance'] > 0:
                            course_text += f"距离: 约{next_course['distance']}米<br>"
                    course_text += "</div>"
        else:
            course_text = "<h3>今日无课程安排</h3>"
            self.progress_bar.setValue(0)
            self.simplified_progress.setValue(0)
            
            # 重置进度指示器
            progress_svg = """
            <svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
              <circle cx="50" cy="50" r="45" fill="none" stroke="#e0e0e0" stroke-width="8" />
              <text x="50" y="55" font-family="Arial" font-size="20" fill="#333333" text-anchor="middle">0%</text>
            </svg>
            """
            self.progress_indicator.renderer().load(QByteArray(progress_svg.encode()))
        
        # 更新完整界面
        self.course_display.setText(course_text)
        
        # 更新当前课程信息
        if current_course:
            self.current_course_label.setText(f"当前课程: {current_course['name']}")
            self.simplified_course_label.setText(f"当前课程: {current_course['name']}")
        else:
            self.current_course_label.setText("当前无课程")
            self.simplified_course_label.setText("当前无课程")
            
        # 更新下节课信息
        if next_course:
            time_until = ""
            if not current_course:
                time_until_start = self.time_manager.get_time_until_next_event(
                    datetime.strptime(next_course['start_time'], '%H:%M').replace(
                        year=datetime.now().year, month=datetime.now().month, day=datetime.now().day
                    )
                )
                minutes_until = int(time_until_start.total_seconds() / 60)
                time_until = f" ({minutes_until}分钟后)"
            
            self.next_course_label.setText(f"下节课: {next_course['name']}{time_until}")
        else:
            self.next_course_label.setText("今日无更多课程")
        
    def set_reminder_time(self, minutes):
        self.notification_manager.set_reminder_time(minutes)
        
    def eventFilter(self, obj, event):
        """事件过滤器，用于处理鼠标悬停事件"""
        if Config.HOVER_SHOW_FULL:
            if event.type() == QEvent.Enter:
                self.mouse_hover = True
                self.hover_timer.stop()
                if self.simplified_mode:
                    self.toggle_simplified_mode()
                return True
            elif event.type() == QEvent.Leave:
                self.mouse_hover = False
                self.hover_timer.start(Config.HOVER_TIMEOUT)
                return True
        return super().eventFilter(obj, event)
    
    def on_hover_timeout(self):
        """鼠标离开后的超时处理"""
        if not self.mouse_hover and not self.simplified_mode:
            self.toggle_simplified_mode()
            
    def toggle_simplified_mode(self, enabled=True):
        """切换简化模式"""
        self.simplified_mode = enabled
        self.ui_config.toggle_simplified_mode(enabled)
        
    def apply_wallpaper_theme(self):
        """应用壁纸适配主题"""
        if not Config.WALLPAPER_ADAPT:
            return
            
        try:
            import ctypes
            from win32con import SPI_GETDESKWALLPAPER
            from win32api import GetSystemMetrics
            from win32gui import SystemParametersInfo
            
            # 获取系统壁纸路径
            wallpaper_path = Config.WALLPAPER_PATH
            if not wallpaper_path:
                # 如果未指定壁纸路径，获取系统壁纸
                buffer_size = 260  # MAX_PATH
                wallpaper_path = ctypes.create_unicode_buffer(buffer_size)
                SystemParametersInfo(SPI_GETDESKWALLPAPER, buffer_size, wallpaper_path, 0)
                wallpaper_path = wallpaper_path.value
            
            # 应用壁纸适配
            if wallpaper_path and os.path.exists(wallpaper_path):
                self.ui_config.adapt_to_wallpaper(wallpaper_path)
                logging.info(f"已适配壁纸: {wallpaper_path}")
            else:
                logging.warning(f"壁纸路径无效: {wallpaper_path}")
        except Exception as e:
            logging.error(f"壁纸适配失败: {str(e)}")
            
    def on_plugin_loaded(self, plugin_name):
        """插件加载成功回调"""
        logging.info(f"插件 {plugin_name} 已加载")
        
    def on_plugin_error(self, plugin_name, error_msg):
        """插件错误回调"""
        logging.error(f"插件 {plugin_name} 错误: {error_msg}")
        
        # 如果配置了显示实时日志，则在界面上显示错误信息
        if Config.SHOW_REALTIME_LOG:
            self.show_log_message(f"插件错误: {plugin_name}\n{error_msg}")
            
    def show_log_message(self, message):
        """显示日志消息"""
        if hasattr(self, 'log_display'):
            self.log_display.append(message)
        else:
            # 创建日志显示区域
            self.log_display = QTextEdit()
            self.log_display.setReadOnly(True)
            self.log_display.setMaximumHeight(100)
            self.main_layout.addWidget(self.log_display)
            self.log_display.append(message)
        
    def update_weather_display(self, weather_info):
        if weather_info:
            self.weather_label.setText(self.notification_manager.format_weather_info())
            
            # 更新天气图标
            if 'icon' in weather_info:
                icon_code = weather_info['icon']
                icon_path = f"img/weather/{icon_code}.svg"
                
                # 检查图标文件是否存在，如果不存在则使用默认图标
                import os
                if not os.path.exists(icon_path):
                    icon_path = "img/weather/weather_display.svg"
                    
                self.weather_icon.load(icon_path)
                
                # 根据天气状况调整图标大小和显示效果
                if '雨' in weather_info.get('description', ''):
                    self.weather_icon.setFixedSize(70, 70)  # 雨天图标稍大
                elif '雪' in weather_info.get('description', ''):
                    self.weather_icon.setFixedSize(75, 75)  # 雪天图标更大
                elif '雷' in weather_info.get('description', ''):
                    self.weather_icon.setFixedSize(80, 80)  # 雷雨图标最大
                else:
                    self.weather_icon.setFixedSize(60, 60)  # 默认大小
        else:
            self.weather_label.setText("天气信息未获取")
        
    def set_window_opacity(self, value):
        self.setWindowOpacity(value / 100)
        # 设置窗口可拖动
        self.dragPos = None
        
    def set_window_scale(self, value):
        """设置窗口缩放比例"""
        scale_factor = value / 100
        self.resize(int(800 * scale_factor), int(600 * scale_factor))
        self.ui_config.set_scale(value)
        
    def enterEvent(self, event):
        # 鼠标悬停时平滑过渡到完全不透明
        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(200)  # 200毫秒的动画时长
        self.opacity_animation.setStartValue(self.windowOpacity())
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.InCubic)
        self.opacity_animation.start()
        
        # 鼠标悬停时取消窗口穿透
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        # 显示完整界面元素
        self.show_full_interface()
        
    def leaveEvent(self, event):
        # 鼠标离开时平滑过渡到设定的透明度
        # 使用动画效果使透明度变化更加平滑
        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(300)  # 300毫秒的动画时长
        self.opacity_animation.setStartValue(self.windowOpacity())
        self.opacity_animation.setEndValue(self.ui_config.theme['opacity'] / 100)
        self.opacity_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.opacity_animation.start()
        
        # 检查是否启用了窗口穿透
        if self.settings.value('enable_click_through', True, type=bool):
            # 鼠标离开时设置窗口穿透
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        # 显示简化界面
        self.show_simplified_interface()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPos = event.globalPos()
        elif event.button() == Qt.RightButton:
            # 右键点击时设置窗口穿透
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.dragPos:
            self.move(self.pos() + event.globalPos() - self.dragPos)
            self.dragPos = event.globalPos()
            
    def mouseReleaseEvent(self, event):
        self.dragPos = None
        if event.button() == Qt.RightButton:
            # 右键释放时取消窗口穿透
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        
    def show_notification(self, message, sound_file):
        from PyQt5.QtMultimedia import QSound
        from PyQt5.QtWidgets import QMessageBox, QSystemTrayIcon
        
        # 显示系统托盘通知
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.showMessage("课程提醒", message, QSystemTrayIcon.Information, 5000)
        
        # 显示消息框
        notification_box = QMessageBox(self)
        notification_box.setWindowTitle("课程提醒")
        notification_box.setText(message)
        notification_box.setIcon(QMessageBox.Information)
        notification_box.setStandardButtons(QMessageBox.Ok)
        
        # 播放提醒音效
        if sound_file and os.path.exists(sound_file):
            QSound.play(sound_file)
        else:
            # 使用默认提醒音效
            default_sound = self.settings.value('default_sound', 'sounds/default_notification.wav')
            if os.path.exists(default_sound):
                QSound.play(default_sound)
        
        notification_box.exec_()
        
    def show_settings_dialog(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QComboBox, QCheckBox, QFileDialog, QPushButton, QTabWidget, QSpinBox, QColorDialog
        
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        dialog.setMinimumWidth(500)
        
        tabs = QTabWidget()
        
        # 基本设置选项卡
        basic_tab = QWidget()
        basic_layout = QVBoxLayout()
        
        # 透明度设置
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("窗口透明度:"))
        opacity_slider = QSlider(Qt.Horizontal)
        opacity_slider.setRange(20, 100)
        opacity_slider.setValue(self.ui_config.theme['opacity'])
        opacity_value_label = QLabel(f"{opacity_slider.value()}%")
        opacity_slider.valueChanged.connect(lambda v: (self.ui_config.set_opacity(v), opacity_value_label.setText(f"{v}%")))
        opacity_layout.addWidget(opacity_slider)
        opacity_layout.addWidget(opacity_value_label)
        basic_layout.addLayout(opacity_layout)
        
        # 缩放比例设置
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("缩放比例:"))
        scale_slider = QSlider(Qt.Horizontal)
        scale_slider.setRange(80, 150)
        scale_slider.setValue(self.ui_config.theme['scale'])
        scale_value_label = QLabel(f"{scale_slider.value()}%")
        scale_slider.valueChanged.connect(lambda v: (self.ui_config.set_scale(v), scale_value_label.setText(f"{v}%")))
        scale_layout.addWidget(scale_slider)
        scale_layout.addWidget(scale_value_label)
        basic_layout.addLayout(scale_layout)
        
        # 停靠位置设置
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("停靠位置:"))
        position_combo = QComboBox()
        position_combo.addItems(["顶部", "底部", "左侧", "右侧", "自由拖动"])
        position_map = {"顶部": "top", "底部": "bottom", "左侧": "left", "右侧": "right", "自由拖动": "free"}
        reverse_map = {v: k for k, v in position_map.items()}
        position_combo.setCurrentText(reverse_map.get(self.ui_config.theme['position'], "顶部"))
        position_combo.currentTextChanged.connect(lambda t: self.ui_config.set_position(position_map[t]))
        position_layout.addWidget(position_combo)
        basic_layout.addLayout(position_layout)
        
        # 窗口穿透设置
        transparent_layout = QHBoxLayout()
        transparent_layout.addWidget(QLabel("窗口穿透:"))
        transparent_check = QCheckBox("启用鼠标离开时窗口穿透")
        transparent_check.setChecked(self.settings.value('enable_click_through', True, type=bool))
        transparent_check.stateChanged.connect(lambda state: self.settings.setValue('enable_click_through', state == Qt.Checked))
        transparent_layout.addWidget(transparent_check)
        basic_layout.addLayout(transparent_layout)
        
        # 简化界面设置
        simplified_layout = QHBoxLayout()
        simplified_layout.addWidget(QLabel("简化界面:"))
        simplified_check = QCheckBox("鼠标离开时显示简化界面")
        simplified_check.setChecked(self.settings.value('simplified_interface', True, type=bool))
        simplified_check.stateChanged.connect(lambda state: self.settings.setValue('simplified_interface', state == Qt.Checked))
        simplified_layout.addWidget(simplified_check)
        basic_layout.addLayout(simplified_layout)
        
        basic_tab.setLayout(basic_layout)
        
        # 外观设置选项卡
        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout()
        
        # 壁纸适配设置
        wallpaper_layout = QHBoxLayout()
        wallpaper_check = QCheckBox("根据桌面壁纸自动调整界面配色")
        wallpaper_check.setChecked(bool(self.ui_config.theme['wallpaper_adapt']))
        wallpaper_check.stateChanged.connect(lambda s: self.ui_config.toggle_wallpaper_adapt(s == Qt.Checked))
        wallpaper_layout.addWidget(wallpaper_check)
        appearance_layout.addLayout(wallpaper_layout)
        
        # 选择壁纸按钮
        wallpaper_button_layout = QHBoxLayout()
        wallpaper_button = QPushButton("选择壁纸")
        wallpaper_button.clicked.connect(self.select_wallpaper)
        wallpaper_button_layout.addWidget(wallpaper_button)
        appearance_layout.addLayout(wallpaper_button_layout)
        
        # Mica效果设置
        mica_layout = QHBoxLayout()
        mica_checkbox = QCheckBox('启用Windows 11 Mica效果')
        mica_checkbox.setChecked(self.ui_config.theme['mica_enabled'])
        mica_checkbox.stateChanged.connect(lambda state: self.ui_config.toggle_mica(state == Qt.Checked))
        
        # 系统兼容性检查
        if sys.getwindowsversion().build < 22000:
            mica_checkbox.setEnabled(False)
            mica_checkbox.setToolTip('需要Windows 11 21H2或更高版本')
        
        mica_layout.addWidget(mica_checkbox)
        appearance_layout.addLayout(mica_layout)

        appearance_tab.setLayout(appearance_layout)
        
        # 提醒设置选项卡
        reminder_tab = QWidget()
        reminder_layout = QVBoxLayout()
        
        # 课前提醒时间设置
        reminder_time_layout = QHBoxLayout()
        reminder_time_layout.addWidget(QLabel("课前提醒时间:"))
        
        reminder_time_spin = QSpinBox()
        reminder_time_spin.setRange(1, 60)
        reminder_time_spin.setValue(self.settings.value('reminder_time', 5, type=int))
        reminder_time_spin.setSuffix(" 分钟")
        reminder_time_spin.valueChanged.connect(lambda v: self.settings.setValue('reminder_time', v))
        reminder_time_layout.addWidget(reminder_time_spin)
        reminder_layout.addLayout(reminder_time_layout)
        
        # 远距离教室额外提醒时间
        extra_time_layout = QHBoxLayout()
        extra_time_layout.addWidget(QLabel("远距离教室额外提醒:"))
        
        extra_time_check = QCheckBox("启用")
        extra_time_check.setChecked(self.settings.value('enable_extra_time', True, type=bool))
        extra_time_check.stateChanged.connect(lambda s: self.settings.setValue('enable_extra_time', s == Qt.Checked))
        extra_time_layout.addWidget(extra_time_check)
        reminder_layout.addLayout(extra_time_layout)
        
        # 提醒音效设置
        sound_layout = QHBoxLayout()
        sound_layout.addWidget(QLabel("提醒音效:"))
        
        sound_combo = QComboBox()
        sound_combo.addItems(["默认", "轻柔", "紧急", "自定义"])
        current_sound = self.settings.value('notification_sound_type', "默认")
        sound_combo.setCurrentText(current_sound)
        sound_combo.currentTextChanged.connect(lambda t: self.settings.setValue('notification_sound_type', t))
        sound_layout.addWidget(sound_combo)
        
        # 自定义音效选择按钮
        custom_sound_button = QPushButton("选择音效文件")
        custom_sound_button.clicked.connect(self.select_sound_file)
        sound_layout.addWidget(custom_sound_button)
        reminder_layout.addLayout(sound_layout)
        
        # 提醒音量设置
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("提醒音量:"))
        
        volume_slider = QSlider(Qt.Horizontal)
        volume_slider.setRange(0, 100)
        volume_slider.setValue(self.settings.value('notification_volume', 80, type=int))
        volume_slider.valueChanged.connect(lambda v: self.settings.setValue('notification_volume', v))
        volume_layout.addWidget(volume_slider)
        
        volume_value = QLabel(f"{volume_slider.value()}%")
        volume_slider.valueChanged.connect(lambda v: volume_value.setText(f"{v}%"))
        volume_layout.addWidget(volume_value)
        reminder_layout.addLayout(volume_layout)
        
        # 测试提醒按钮
        test_button = QPushButton("测试提醒")
        test_button.clicked.connect(lambda: self.show_notification("这是一条测试提醒消息\n用于测试提醒功能是否正常工作", 
                                                              self.settings.value('custom_sound_file', '')))
        reminder_layout.addWidget(test_button)
        
        reminder_tab.setLayout(reminder_layout)
        
        # 添加选项卡
        tabs.addTab(basic_tab, "基本")
        tabs.addTab(appearance_tab, "外观")
        tabs.addTab(reminder_tab, "提醒")
        
        # 对话框布局
        dialog_layout = QVBoxLayout()
        dialog_layout.addWidget(tabs)
        
        # 确定按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(dialog.accept)
        button_layout.addStretch(1)
        button_layout.addWidget(ok_button)
        dialog_layout.addLayout(button_layout)
        
        dialog.setLayout(dialog_layout)
        dialog.exec_()
    
    def select_wallpaper(self):
        file_dialog = QFileDialog()
        wallpaper_path, _ = file_dialog.getOpenFileName(self, "选择壁纸", "", "图片文件 (*.jpg *.jpeg *.png *.bmp)")
        if wallpaper_path and os.path.exists(wallpaper_path):
            self.ui_config.adapt_to_wallpaper(wallpaper_path)
            
    def select_sound_file(self):
        from PyQt5.QtWidgets import QFileDialog
        file_dialog = QFileDialog()
        sound_path, _ = file_dialog.getOpenFileName(self, "选择音效文件", "", "音频文件 (*.wav *.mp3)")
        if sound_path:
            self.settings.setValue('custom_sound_file', sound_path)
            self.settings.setValue('notification_sound_type', "自定义")
            # 播放所选音效作为预览
            from PyQt5.QtMultimedia import QSound
            if sound_path.endswith('.wav'):
                QSound.play(sound_path)
    
    def apply_theme(self, theme):
        # 应用主题设置
        self.setWindowOpacity(0.7)  # 默认调整为更适合动态岛的透明度
        
        # 应用缩放比例
        scale_factor = theme['scale'] / 100
        self.resize(int(800 * scale_factor), int(600 * scale_factor))
        
        # 应用停靠位置
        self.position_window(theme['position'])
        
        # 应用颜色主题
        self.setStyleSheet(f"""
            QWidget {{ background-color: {theme['background_color']}; color: {theme['text_color']}; }}
            QPushButton {{ background-color: {theme['primary_color']}; color: {theme['text_color']}; 
                         border-radius: 4px; padding: 4px 8px; }}
            QPushButton:hover {{ background-color: {theme['accent_color']}; }}
            QProgressBar {{ border: 1px solid {theme['primary_color']}; border-radius: 5px; }}
            QProgressBar::chunk {{ background-color: {theme['accent_color']}; }}
        """)
        
        # 应用颜色主题
        self.setStyleSheet(f"""
            QWidget {{ background-color: {theme['background_color']}; color: {theme['text_color']}; }}
            QPushButton {{ background-color: {theme['primary_color']}; color: {theme['text_color']}; 
                         border-radius: 4px; padding: 4px 8px; }}
            QPushButton:hover {{ background-color: {theme['accent_color']}; }}
            QProgressBar {{ border: 1px solid {theme['primary_color']}; border-radius: 5px; }}
            QProgressBar::chunk {{ background-color: {theme['accent_color']}; }}
        """)
        
    def show_simplified_interface(self):
        # 只有在设置中启用了简化界面时才执行
        if not self.settings.value('simplified_interface', True, type=bool):
            return
            
        self.simplified_mode = True
        
        # 隐藏完整界面元素
        self.settings_button.setVisible(False)
        self.time_label.setVisible(False)
        self.course_display.setVisible(False)
        self.progress_bar.setVisible(False)
        self.opacity_label.setVisible(False)
        self.opacity_slider.setVisible(False)
        self.reminder_label.setVisible(False)
        self.reminder_slider.setVisible(False)
        self.weather_label.setVisible(False)
        
        # 显示简化界面元素
        self.simplified_widget.setVisible(True)
        
        # 调整窗口大小为简化模式
        theme = self.ui_config.get_theme()
        scale_factor = theme['scale'] / 100
        self.resize(int(300 * scale_factor), int(150 * scale_factor))
        
    def show_full_interface(self):
        self.simplified_mode = False
        
        # 显示完整界面元素
        self.settings_button.setVisible(True)
        self.time_label.setVisible(True)
        self.course_display.setVisible(True)
        self.progress_bar.setVisible(True)
        self.opacity_label.setVisible(True)
        self.opacity_slider.setVisible(True)
        self.reminder_label.setVisible(True)
        self.reminder_slider.setVisible(True)
        self.weather_label.setVisible(True)
        
        # 隐藏简化界面元素
        self.simplified_widget.setVisible(False)
        
        # 恢复窗口大小为完整模式
        theme = self.ui_config.get_theme()
        scale_factor = theme['scale'] / 100
        self.resize(int(800 * scale_factor), int(600 * scale_factor))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SCSApp()
    window.show()
    sys.exit(app.exec_())