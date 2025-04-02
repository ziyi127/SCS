from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from datetime import datetime, timedelta
import json

class TimeManager(QObject):
    time_updated = pyqtSignal()
    reminder_triggered = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(60000)  # 每分钟更新一次
        self.current_time = datetime.now()
        self.reminders = []
        self.load_reminders()
    
    def load_reminders(self):
        try:
            with open('reminders.json', 'r') as f:
                self.reminders = json.load(f)
        except FileNotFoundError:
            self.save_reminders()
    
    def save_reminders(self):
        with open('reminders.json', 'w') as f:
            json.dump(self.reminders, f, indent=4)
    
    def update_time(self):
        self.current_time = datetime.now()
        self.check_reminders()
        self.time_updated.emit()
    
    def check_reminders(self):
        for reminder in self.reminders:
            if self.current_time >= datetime.strptime(reminder['time'], '%Y-%m-%d %H:%M:%S'):
                self.reminder_triggered.emit(reminder['message'])
                self.reminders.remove(reminder)
                self.save_reminders()
    
    def add_reminder(self, time, message):
        self.reminders.append({
            'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': message
        })
        self.save_reminders()
    
    def get_current_time(self):
        return self.current_time
    
    def get_time_until_next_event(self, event_time):
        return event_time - self.current_time