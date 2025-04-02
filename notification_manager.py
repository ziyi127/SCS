from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import datetime
import requests
from PyQt5.QtCore import QSettings

class NotificationManager(QObject):
    weather_updated = pyqtSignal(dict)
    notification_triggered = pyqtSignal(str, str)  # message, sound_file

    def __init__(self, course_manager):
        super().__init__()
        self.course_manager = course_manager
        self.settings = QSettings('SCS', 'Preferences')
        self.weather_api_key = self.settings.value('weather_api_key', '')
        self.location = self.settings.value('location', '北京')
        
        # 初始化定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_schedule)
        self.timer.start(60000)  # 每分钟检查一次
        
        # 天气更新定时器
        self.weather_timer = QTimer()
        self.weather_timer.timeout.connect(self.update_weather)
        self.weather_timer.start(1800000)  # 每30分钟更新一次天气
        
        # 初始化天气信息
        self.current_weather = self.get_weather_info()
    

    
    def check_schedule(self):
        now = datetime.datetime.now()
        weekday = now.strftime('%A')
        week_type = self.course_manager.get_current_week_type()
        
        # 获取当天课程
        today_courses = self.course_manager.get_today_schedule()
        
        for course in today_courses:
            start_time = datetime.datetime.strptime(course['start_time'], '%H:%M').replace(
                year=now.year, month=now.month, day=now.day)
            end_time = datetime.datetime.strptime(course['end_time'], '%H:%M').replace(
                year=now.year, month=now.month, day=now.day)
            
            # 上课提醒（根据用户设置的提前时间）
            reminder_time = self.settings.value('reminder_time', 5, type=int)
            time_until_start = (start_time - now).total_seconds() / 60
            
            # 检查是否需要提前更多时间（如果教室距离较远）
            extra_time = 0
            if 'classroom' in course and course['classroom']:
                distance = self.calculate_distance(course['classroom'])
                if distance > 500 and self.settings.value('enable_extra_time', True, type=bool):  # 如果距离超过500米
                    extra_time = int(distance / 100)  # 每100米需要1分钟
                    adjusted_reminder_time = reminder_time + extra_time
                else:
                    adjusted_reminder_time = reminder_time
            else:
                adjusted_reminder_time = reminder_time
            
            # 上课前提醒
            if 0 < time_until_start <= adjusted_reminder_time:
                distance = self.calculate_distance(course.get('classroom', ''))
                message = f"即将上课: {course['name']}\n"
                message += f"时间: {course['start_time']}-{course['end_time']}\n"
                
                if 'teacher' in course and course['teacher']:
                    message += f"教师: {course['teacher']}\n"
                    
                if 'classroom' in course and course['classroom']:
                    message += f"教室: {course['classroom']}\n"
                
                # 如果有课程备注，添加到提醒中
                if 'notes' in course and course['notes']:
                    message += f"备注: {course['notes']}\n"
                
                # 如果距离较远，添加路程提醒
                if distance > 500:
                    extra_time = int(distance / 100)  # 假设每100米需要1分钟
                    message += f"⚠️ 距离较远，约{distance}米，建议提前{extra_time}分钟出发\n"
                
                # 添加天气信息
                if hasattr(self, 'current_weather'):
                    # 根据天气情况添加特殊提醒
                    weather_desc = self.current_weather.get('description', '')
                    temp = self.current_weather.get('temp', '')
                    
                    message += f"当前天气: {weather_desc} {temp}℃\n"
                    
                    # 根据天气情况添加特殊提醒
                    if '雨' in weather_desc:
                        message += "☔ 记得带伞\n"
                    elif '雪' in weather_desc:
                        message += "❄️ 注意保暖，路面可能湿滑\n"
                    elif temp and int(temp) > 30:
                        message += "🔥 天气炎热，注意防暑\n"
                    elif temp and int(temp) < 5:
                        message += "❄️ 天气寒冷，注意保暖\n"
                
                # 选择合适的提醒音效
                sound_type = self.settings.value('notification_sound_type', "默认")
                if sound_type == "默认":
                    sound_file = "sounds/default_notification.wav"
                elif sound_type == "轻柔":
                    sound_file = "sounds/gentle_notification.wav"
                elif sound_type == "紧急":
                    sound_file = "sounds/urgent_notification.wav"
                else:  # 自定义
                    sound_file = self.settings.value('custom_sound_file', "sounds/default_notification.wav")
                
                self.notification_triggered.emit(message, sound_file)
            
            # 下课提醒
            time_until_end = (end_time - now).total_seconds() / 60
            if 0 < time_until_end <= 1:
                next_course = self.get_next_course(course, today_courses)
                message = f"即将下课: {course['name']}\n"
                
                if next_course:
                    time_until_next = (datetime.datetime.strptime(next_course['start_time'], '%H:%M').replace(
                        year=now.year, month=now.month, day=now.day) - end_time).total_seconds() / 60
                    
                    message += f"下节课: {next_course['name']} ({next_course['start_time']})\n"
                    
                    if 'classroom' in next_course and next_course['classroom']:
                        message += f"教室: {next_course['classroom']}\n"
                        
                        # 如果教室发生变化，特别提醒
                        if course.get('classroom') != next_course.get('classroom'):
                            distance = self.calculate_distance(next_course.get('classroom', ''))
                            if distance > 200:
                                message += f"⚠️ 需要换教室! 距离约{distance}米，"
                                
                                # 计算需要的时间
                                needed_time = int(distance / 100)  # 假设每100米需要1分钟
                                if time_until_next < needed_time + 2:  # 如果时间紧张
                                    message += f"时间紧张，请立即前往!\n"
                                else:
                                    message += f"预计需要{needed_time}分钟\n"
                    
                    # 如果下节课有特殊备注，也提醒
                    if 'notes' in next_course and next_course['notes']:
                        message += f"备注: {next_course['notes']}\n"
                else:
                    message += "今日无更多课程安排\n"
                
                # 使用下课提醒音效
                sound_file = "sounds/class_end.wav"
                if not os.path.exists(sound_file):
                    sound_file = "sounds/default_notification.wav"
                
                self.notification_triggered.emit(message, sound_file)
                
            # 课程进行中提醒（如果课程超过90分钟，在中间提醒休息）
            course_duration = (end_time - start_time).total_seconds() / 60
            if course_duration > 90:
                mid_point = start_time + (end_time - start_time) / 2
                time_until_mid = abs((mid_point - now).total_seconds() / 60)
                
                if time_until_mid <= 1:  # 接近课程中点
                    message = f"课程提醒: {course['name']}\n"
                    message += "已经上了一半的课程，建议适当休息一下眼睛\n"
                    
                    # 使用温和的提醒音效
                    sound_file = "sounds/gentle_notification.wav"
                    if not os.path.exists(sound_file):
                        sound_file = "sounds/default_notification.wav"
                    
                    self.notification_triggered.emit(message, sound_file)
    
    def get_next_course(self, current_course, today_courses):
        current_end = datetime.datetime.strptime(current_course['end_time'], '%H:%M')
        next_course = None
        min_time_diff = float('inf')
        
        for course in today_courses:
            if course == current_course:
                continue
            
            course_start = datetime.datetime.strptime(course['start_time'], '%H:%M')
            if course_start > current_end:
                time_diff = (course_start - current_end).total_seconds()
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    next_course = course
        
        return next_course

    def get_weather_info(self):
        if not self.weather_api_key:
            print('未配置天气API密钥')
            # 尝试使用免费API获取天气信息
            try:
                response = requests.get(
                    f'https://wttr.in/{self.location}?format=j1',
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                weather_info = {
                    'temp': int(data['current_condition'][0]['temp_C']),
                    'description': data['current_condition'][0]['weatherDesc'][0]['value'],
                    'humidity': data['current_condition'][0]['humidity'],
                    'icon': self.map_wttr_icon(data['current_condition'][0]['weatherCode']),
                    'wind_speed': data['current_condition'][0]['windspeedKmph'],
                    'last_update': datetime.datetime.now().strftime('%H:%M'),
                    'feels_like': int(data['current_condition'][0]['FeelsLikeC']),
                    'pressure': data['current_condition'][0]['pressure'],
                    'visibility': data['current_condition'][0]['visibility']
                }
                
                # 缓存天气数据
                self.settings.setValue('last_weather', weather_info)
                self.settings.setValue('last_weather_update', datetime.datetime.now().isoformat())
                
                return weather_info
            except Exception as e:
                print(f'免费天气API请求失败: {str(e)}')
                return self.get_cached_or_default_weather()

        try:
            response = requests.get(
                f'http://api.openweathermap.org/data/2.5/weather?q={self.location}&appid={self.weather_api_key}&units=metric&lang=zh_cn',
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            weather_info = {
                'temp': round(data['main']['temp']),
                'description': data['weather'][0]['description'],
                'humidity': data['main']['humidity'],
                'icon': data['weather'][0]['icon'],
                'wind_speed': data['wind']['speed'],
                'last_update': datetime.datetime.now().strftime('%H:%M'),
                'feels_like': round(data['main']['feels_like']),
                'pressure': data['main']['pressure'],
                'visibility': data.get('visibility', 'N/A')
            }
            
            # 缓存天气数据
            self.settings.setValue('last_weather', weather_info)
            self.settings.setValue('last_weather_update', datetime.datetime.now().isoformat())
            
            return weather_info
            
        except requests.RequestException as e:
            print(f'天气API请求失败: {str(e)}')
            # 尝试使用缓存的天气数据
            last_weather = self.settings.value('last_weather', None)
            if last_weather:
                return last_weather
            return self.get_default_weather()
            
        except (KeyError, ValueError) as e:
            print(f'天气数据解析失败: {str(e)}')
            return self.get_default_weather()
            
    def get_default_weather(self):
        return {
            'temp': 'N/A',
            'description': '获取天气失败',
            'humidity': 'N/A',
            'icon': '01d',
            'wind_speed': 'N/A',
            'last_update': 'N/A',
            'feels_like': 'N/A',
            'pressure': 'N/A',
            'visibility': 'N/A'
        }
        
    def get_cached_or_default_weather(self):
        # 尝试使用缓存的天气数据
        last_weather = self.settings.value('last_weather', None)
        if last_weather:
            return last_weather
        return self.get_default_weather()
        
    def map_wttr_icon(self, code):
        # 将wttr.in的天气代码映射到OpenWeatherMap的图标代码
        # 简化映射，实际可以更详细
        code_map = {
            '113': '01d',  # 晴天
            '116': '02d',  # 少云
            '119': '03d',  # 多云
            '122': '04d',  # 阴天
            '143': '50d',  # 雾
            '176': '09d',  # 小雨
            '200': '11d',  # 雷阵雨
            '248': '50d',  # 雾
            '260': '50d',  # 冻雾
            '263': '09d',  # 小雨
            '266': '09d',  # 小雨
            '281': '13d',  # 冻雨
            '284': '13d',  # 大冻雨
            '293': '09d',  # 小雨
            '296': '09d',  # 中雨
            '299': '09d',  # 中雨
            '302': '10d',  # 大雨
            '305': '10d',  # 大雨
            '308': '10d',  # 暴雨
            '311': '13d',  # 冻雨
            '314': '13d',  # 冻雨
            '317': '13d',  # 雨夹雪
            '320': '13d',  # 雨夹雪
            '323': '13d',  # 小雪
            '326': '13d',  # 小雪
            '329': '13d',  # 中雪
            '332': '13d',  # 中雪
            '335': '13d',  # 大雪
            '338': '13d',  # 大雪
            '350': '13d',  # 冰雹
            '353': '09d',  # 小雨
            '356': '10d',  # 中雨
            '359': '10d',  # 大雨
            '362': '13d',  # 小雨夹雪
            '365': '13d',  # 雨夹雪
            '368': '13d',  # 小雪
            '371': '13d',  # 中雪
            '374': '13d',  # 小冰雹
            '377': '13d',  # 冰雹
            '386': '11d',  # 雷阵雨
            '389': '11d',  # 雷阵雨
            '392': '11d',  # 雷阵雪
            '395': '13d'   # 大雪
        }
        return code_map.get(str(code), '01d')  # 默认返回晴天图标
        
    def update_weather(self):
        # 检查上次更新时间
        last_update = self.settings.value('last_weather_update', None)
        if last_update:
            last_update = datetime.datetime.fromisoformat(last_update)
            now = datetime.datetime.now()
            # 如果距离上次更新不到30分钟，使用缓存数据
            if (now - last_update).total_seconds() < 1800:
                cached_weather = self.settings.value('last_weather', None)
                if cached_weather:
                    self.current_weather = cached_weather
                    self.weather_updated.emit(cached_weather)
                    return
        
        weather_info = self.get_weather_info()
        self.current_weather = weather_info
        self.weather_updated.emit(weather_info)

    def calculate_distance(self, classroom):
        # 简单的教室距离计算逻辑
        classroom_distances = {
            '实验楼203': 800,
            '教学楼A101': 200,
            '教学楼B201': 300,
            '图书馆301': 600,
            '体育馆': 1000
        }
        
        # 如果教室不在预设列表中，返回一个默认距离
        if not classroom or classroom not in classroom_distances:
            return 0
            
        return classroom_distances[classroom]
    
    def set_reminder_time(self, minutes_before):
        self.reminder_time = minutes_before
        self.settings.setValue('reminder_time', minutes_before)
    
    def set_alert_sound(self, sound_file):
        self.sound_file = sound_file
        self.settings.setValue('alert_sound', sound_file)
    
    def format_weather_info(self):
        if not self.current_weather:
            return "天气信息未获取"
            
        weather = self.current_weather
        
        # 添加天气预警信息（如果有）
        warning_info = ""
        if 'warning' in weather and weather['warning']:
            warning_info = f"\n⚠️ 预警: {weather['warning']}"
            
        # 添加空气质量信息（如果有）
        air_quality = ""
        if 'air_quality' in weather and weather['air_quality']:
            air_quality = f"\n空气质量: {weather['air_quality']}"
            
        # 添加降水概率信息（如果有）
        precipitation = ""
        if 'precipitation' in weather and weather['precipitation']:
            precipitation = f"\n降水概率: {weather['precipitation']}%"
            
        return f"{self.location} {weather['temp']}°C {weather['description']}\n"\
               f"体感温度: {weather.get('feels_like', 'N/A')}°C 湿度: {weather['humidity']}%\n"\
               f"风速: {weather['wind_speed']}m/s 更新时间: {weather['last_update']}"\
               f"{warning_info}{air_quality}{precipitation}"