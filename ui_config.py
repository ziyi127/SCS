from PyQt5.QtCore import QObject, pyqtSignal, QSettings
from PyQt5.QtGui import QColor, QPixmap, QImage
import colorsys

class UIConfig(QObject):
    theme_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings('SCS', 'UI_Preferences')
        self.theme = {
            'opacity': int(self.settings.value('opacity', 80)),
            'scale': int(self.settings.value('scale', 100)),
            'position': str(self.settings.value('position', 'top')),
            'primary_color': str(self.settings.value('primary_color', '#4a86e8')),
            'text_color': str(self.settings.value('text_color', '#ffffff')),
            'background_color': str(self.settings.value('background_color', '#333333')),
            'accent_color': str(self.settings.value('accent_color', '#ff9900')),
            'wallpaper_adapt': bool(self.settings.value('wallpaper_adapt', True)),
            'mica_enabled': bool(self.settings.value('mica_enabled', True)),
            'blur_effect': int(self.settings.value('blur_effect', 30)),
            'blur_color': str(self.settings.value('blur_color', '#3333337f'))
        }
    
    def save_settings(self):
        for key, value in self.theme.items():
            self.settings.setValue(key, value)
        self.theme_updated.emit(self.theme)
    
    def set_opacity(self, value):
        self.theme['opacity'] = value
        self.save_settings()
    
    def set_scale(self, value):
        self.theme['scale'] = value
        self.save_settings()
    
    def set_position(self, position):
        self.theme['position'] = position
        self.save_settings()
    
    def set_colors(self, primary, text, background, accent):
        self.theme['primary_color'] = primary
        self.theme['text_color'] = text
        self.theme['background_color'] = background
        self.theme['accent_color'] = accent
        self.save_settings()
    
    def toggle_mica(self, enabled):
        self.theme['mica_enabled'] = enabled
        self.save_settings()

    def toggle_simplified_mode(self, enabled=True):
        self.theme['simplified_mode'] = enabled
        self.save_settings()

    def toggle_wallpaper_adapt(self, enabled):
        self.theme['wallpaper_adapt'] = enabled
        self.save_settings()
        
    def set_blur_effect(self, value):
        self.theme['blur_effect'] = value
        self.save_settings()
        
    def set_blur_color(self, color):
        self.theme['blur_color'] = color
        self.save_settings()
    
    def adapt_to_wallpaper(self, wallpaper_path):
        """根据壁纸自动调整界面配色"""
        if not self.theme['wallpaper_adapt']:
            return
            
        try:
            # 加载壁纸图像
            pixmap = QPixmap(wallpaper_path)
            if pixmap.isNull():
                return
                
            image = pixmap.toImage()
            width, height = image.width(), image.height()
            width, height = image.width(), image.height()
            
            # 采样点数量
            sample_count = 100
            colors = []
            
            # 采样图像颜色
            for x in range(0, width, width // 10):
                for y in range(0, height, height // 10):
                    if len(colors) >= sample_count:
                        break
                    pixel = image.pixel(x, y)
                    colors.append(QColor(pixel))
            
            # 计算主色调
            r_sum, g_sum, b_sum = 0, 0, 0
            for color in colors:
                r_sum += color.red()
                g_sum += color.green()
                b_sum += color.blue()
            
            r_avg = r_sum // len(colors)
            g_avg = g_sum // len(colors)
            b_avg = b_sum // len(colors)
            
            # 转换为HSV以便调整亮度和饱和度
            h, s, v = colorsys.rgb_to_hsv(r_avg/255, g_avg/255, b_avg/255)
            
            # 生成配色方案
            primary_color = self.hsv_to_hex(h, min(s + 0.2, 1.0), min(v + 0.1, 1.0))
            accent_color = self.hsv_to_hex((h + 0.5) % 1.0, min(s + 0.3, 1.0), min(v + 0.2, 1.0))
            
            # 根据主色调亮度决定文本颜色
            text_color = '#ffffff' if v < 0.6 else '#333333'
            
            # 设置背景色为主色调的暗色版本
            background_color = self.hsv_to_hex(h, min(s + 0.1, 1.0), max(v - 0.4, 0.1))
            
            # 更新主题
            self.theme['primary_color'] = primary_color
            self.theme['text_color'] = text_color
            self.theme['background_color'] = background_color
            self.theme['accent_color'] = accent_color
            self.save_settings()
            
        except Exception as e:
            print(f"壁纸适配失败: {str(e)}")
    
    def hsv_to_hex(self, h, s, v):
        """将HSV颜色转换为十六进制颜色代码"""
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'
    
    def get_theme(self):
        return self.theme