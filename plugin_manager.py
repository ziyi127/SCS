from PyQt5.QtCore import QObject, pyqtSignal
import importlib
import os
import logging
from config import Config

class PluginManager(QObject):
    plugin_loaded = pyqtSignal(str)
    plugin_error = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        self.plugins = {}
    
    def load_plugins(self):
        """加载所有插件"""
        if not hasattr(Config, 'PLUGINS_ENABLED') or not Config.PLUGINS_ENABLED:
            return
            
        plugins_dir = getattr(Config, 'PLUGINS_DIR', 'plugins')
        if not os.path.exists(plugins_dir):
            os.makedirs(plugins_dir)
            return
            
        for filename in os.listdir(plugins_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                plugin_name = filename[:-3]
                try:
                    module = importlib.import_module(f'{plugins_dir}.{plugin_name}')
                    plugin_class = getattr(module, f'{plugin_name.capitalize()}Plugin', None)
                    if plugin_class:
                        self.plugins[plugin_name] = plugin_class()
                        self.plugin_loaded.emit(plugin_name)
                except Exception as e:
                    self.plugin_error.emit(plugin_name, str(e))
                    logging.error(f"加载插件 {plugin_name} 失败: {str(e)}")