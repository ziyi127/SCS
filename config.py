class Config:
    # 基本配置
    VERSION = "1.0.0"
    APP_NAME = "SCS智慧电子课程表"
    
    # 界面配置
    CLICK_THROUGH = True  # 窗口穿透功能
    HOVER_SHOW_FULL = True  # 鼠标悬停时显示完整界面
    HOVER_TIMEOUT = 2000  # 鼠标离开后隐藏完整界面的延迟(毫秒)
    
    # 日志配置
    LOG_LEVEL = "INFO"  # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_TO_FILE = True  # 是否记录日志到文件
    LOG_FILE_PATH = "scs.log"  # 日志文件路径
    IGNORE_ERROR = False  # 是否忽略错误
    SHOW_REALTIME_LOG = False  # 是否显示实时日志
    
    # 插件配置
    PLUGINS_ENABLED = True  # 是否启用插件
    PLUGINS_DIR = "plugins"  # 插件目录
    
    # 壁纸适配配置
    WALLPAPER_ADAPT = True  # 是否启用壁纸适配
    WALLPAPER_PATH = ""  # 壁纸路径，为空则使用系统壁纸
    
    @classmethod
    def load_from_file(cls):
        """从配置文件加载配置"""
        import os
        import json
        
        config_path = "config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                
                # 更新配置
                for key, value in config_data.items():
                    if hasattr(cls, key):
                        setattr(cls, key, value)
                        
                print(f"配置已从 {config_path} 加载")
            except Exception as e:
                print(f"加载配置文件失败: {str(e)}")
        else:
            # 创建默认配置文件
            cls.save_to_file()
    
    @classmethod
    def save_to_file(cls):
        """保存当前配置到文件"""
        import json
        
        config_data = {}
        for attr in dir(cls):
            if not attr.startswith('__') and not callable(getattr(cls, attr)):
                config_data[attr] = getattr(cls, attr)
        
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        
        print("配置已保存到 config.json")