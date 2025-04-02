from PyQt5.QtCore import QObject, pyqtSignal, QSettings
import json
from datetime import datetime

class CourseManager(QObject):
    course_updated = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.courses = []
        self.schedule = {}
        self.settings = QSettings('SCS', 'Course_Preferences')
        self.load_data()
    
    def load_data(self):
        try:
            with open('config/course_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.courses = data.get('courses', [])
                self.schedule = data.get('schedule', {})
        except FileNotFoundError:
            self.save_data()
    
    def save_data(self):
        with open('config/course_data.json', 'w', encoding='utf-8') as f:
            json.dump({
                'courses': self.courses,
                'schedule': self.schedule,
                'subject_library': self.subject_library
            }, f, ensure_ascii=False, indent=4)
        self.course_updated.emit()
        
    def add_subject(self, name, color, teacher=None, notes=None, equipment=None):
        """添加科目到科目库"""
        if not hasattr(self, 'subject_library'):
            self.subject_library = {}
            
        self.subject_library[name] = {
            'color': color,
            'teacher': teacher,
            'notes': notes,
            'equipment': equipment
        }
        self.save_data()
        
    def remove_subject(self, name):
        """从科目库移除科目"""
        if hasattr(self, 'subject_library') and name in self.subject_library:
            del self.subject_library[name]
            self.save_data()
            
    def get_subject_info(self, name):
        """获取科目信息"""
        if hasattr(self, 'subject_library') and name in self.subject_library:
            return self.subject_library[name]
        return None
    
    def add_course(self, name, color, teacher, notes, start_time, end_time, day, week_type, equipment=None):
        # 时间冲突检测
        new_course = {
            'name': name,
            'color': color,
            'teacher': teacher,
            'notes': notes,
            'start_time': start_time,
            'end_time': end_time,
            'day': day,
            'week_type': week_type,
            'equipment': equipment
        }
        
        if self.check_time_conflict(new_course):
            raise ValueError("课程时间与已有课程冲突")
        
        self.courses.append(new_course)
        self.save_data()

    def check_time_conflict(self, new_course):
        for existing in self.courses:
            if existing['day'] == new_course['day'] and \
               existing['week_type'] == new_course['week_type']:
                
                new_start = datetime.strptime(new_course['start_time'], '%H:%M')
                new_end = datetime.strptime(new_course['end_time'], '%H:%M')
                exist_start = datetime.strptime(existing['start_time'], '%H:%M')
                exist_end = datetime.strptime(existing['end_time'], '%H:%M')
                
                if (new_start < exist_end) and (new_end > exist_start):
                    return True
        return False
    
    def get_current_week_type(self):
        """根据学期起始日期计算单双周
        返回值:
            'odd': 单周
            'even': 双周
            'both': 单双周都有
        """
        # 检查是否有临时周次覆盖
        today_str = datetime.now().strftime('%Y-%m-%d')
        temp_week_types = self.settings.value('temp_week_types', {})
        if today_str in temp_week_types:
            return temp_week_types[today_str]
            
        # 检查是否有特殊日期覆盖
        special_dates = self.settings.value('special_dates', {})
        if today_str in special_dates:
            return special_dates[today_str]
        
        # 根据学期起始日期计算单双周
        semester_start = self.settings.value('semester_start_date', None)
        if not semester_start:
            # 如果未设置学期起始日期，使用简单的单双周判断
            today = datetime.now()
            return 'odd' if today.isocalendar()[1] % 2 == 1 else 'even'
        
        try:
            # 将字符串转换为日期对象
            semester_start = datetime.strptime(semester_start, '%Y-%m-%d')
            today = datetime.now()
            
            # 计算从学期开始到现在的天数
            days_diff = (today - semester_start).days
            if days_diff < 0:
                # 如果当前日期在学期开始前，返回默认值
                return 'odd'
                
            week_number = days_diff // 7 + 1  # 第几周，从1开始
            
            # 记录当前周次到日志
            import logging
            logging.info(f"当前是第{week_number}周，{'单' if week_number % 2 == 1 else '双'}周")
            
            return 'odd' if week_number % 2 == 1 else 'even'
        except Exception as e:
            import logging
            logging.error(f"计算周次失败: {str(e)}")
            # 出错时使用简单的单双周判断
            today = datetime.now()
            return 'odd' if today.isocalendar()[1] % 2 == 1 else 'even'
    
    def get_course_progress(self, course):
        # 计算课程进度百分比
        now = datetime.now()
        start_time = datetime.strptime(course['start_time'], '%H:%M')
        end_time = datetime.strptime(course['end_time'], '%H:%M')
        
        if now < start_time:
            return 0
        elif now > end_time:
            return 100
        else:
            total_minutes = (end_time - start_time).total_seconds() / 60
            elapsed_minutes = (now - start_time).total_seconds() / 60
            return int((elapsed_minutes / total_minutes) * 100)
    
    def get_today_schedule(self):
        # 检查是否有临时课表覆盖
        today_str = datetime.now().strftime('%Y-%m-%d')
        temp_schedule = self.settings.value('temp_schedule', {})
        if today_str in temp_schedule:
            return temp_schedule[today_str]
        
        week_type = self.get_current_week_type()
        weekday = datetime.now().strftime('%A')
        courses = self.schedule.get(weekday, {}).get(week_type, [])
        
        # 标记当前正在进行的课程
        now = datetime.now()
        current_time = now.time()
        today = now.date()
        
        for course in courses:
            # 解析课程时间
            start_time = datetime.strptime(course['start_time'], '%H:%M').time()
            end_time = datetime.strptime(course['end_time'], '%H:%M').time()
            
            # 创建完整的日期时间对象用于计算
            course_start = datetime.combine(today, start_time)
            course_end = datetime.combine(today, end_time)
            
            # 标记课程状态
            if start_time <= current_time <= end_time:
                course['is_current'] = True
                course['progress'] = self.get_course_progress(course)
            else:
                course['is_current'] = False
                course['progress'] = 0
                
            # 标记即将开始的课程（15分钟内）
            if current_time < start_time and (course_start - now).total_seconds() <= 900:
                course['coming_soon'] = True
            else:
                course['coming_soon'] = False
                
            # 添加教室距离信息（如果有）
            if 'classroom' in course and course['classroom']:
                from notification_manager import NotificationManager
                nm = NotificationManager(self)
                course['distance'] = nm.calculate_distance(course['classroom'])
        
        # 按时间排序
        courses.sort(key=lambda x: datetime.strptime(x['start_time'], '%H:%M'))
        
        return courses
        
    def set_semester_start_date(self, date_str):
        """设置学期起始日期"""
        self.settings.setValue('semester_start_date', date_str)
        self.course_updated.emit()
    
    def set_special_date_override(self, date_str, week_type):
        """设置特定日期的周次覆盖"""
        special_dates = self.settings.value('special_dates', {})
        special_dates[date_str] = week_type
        self.settings.setValue('special_dates', special_dates)
        self.course_updated.emit()
    
    def set_temp_schedule(self, date_str, courses):
        """设置临时课表覆盖"""
        temp_schedule = self.settings.value('temp_schedule', {})
        temp_schedule[date_str] = courses
        self.settings.setValue('temp_schedule', temp_schedule)
        self.course_updated.emit()
    
    def clear_temp_schedule(self, date_str=None):
        """清除临时课表覆盖"""
        if date_str:
            temp_schedule = self.settings.value('temp_schedule', {})
            if date_str in temp_schedule:
                del temp_schedule[date_str]
                self.settings.setValue('temp_schedule', temp_schedule)
        else:
            self.settings.remove('temp_schedule')
        self.course_updated.emit()
        
    def import_from_excel(self, file_path):
        """从Excel文件导入课表"""
        try:
            import pandas as pd
            df = pd.read_excel(file_path)
            
            # 清空现有数据
            self.courses = []
            self.schedule = {}
            
            # 解析Excel数据
            for _, row in df.iterrows():
                course = {
                    'name': row['课程名称'],
                    'color': row.get('颜色', '#4a86e8'),
                    'teacher': row.get('教师', ''),
                    'notes': row.get('备注', ''),
                    'start_time': row['开始时间'],
                    'end_time': row['结束时间'],
                    'day': row['星期'],
                    'week_type': row.get('周类型', 'both'),
                    'equipment': row.get('器材', '')
                }
                self.add_course(**course)
            
            self.save_data()
            return True
        except Exception as e:
            import logging
            logging.error(f"导入Excel失败: {str(e)}")
            return False
            
    def export_to_json(self, file_path):
        """导出课表为JSON文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'courses': self.courses,
                    'schedule': self.schedule,
                    'subject_library': getattr(self, 'subject_library', {})
                }, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            import logging
            logging.error(f"导出JSON失败: {str(e)}")
            return False
            
    def export_to_csv(self, file_path):
        """导出课表为CSV文件"""
        try:
            import pandas as pd
            data = []
            for day, day_schedule in self.schedule.items():
                for week_type, courses in day_schedule.items():
                    for course in courses:
                        data.append({
                            '课程名称': course['name'],
                            '颜色': course['color'],
                            '教师': course.get('teacher', ''),
                            '备注': course.get('notes', ''),
                            '开始时间': course['start_time'],
                            '结束时间': course['end_time'],
                            '星期': day,
                            '周类型': week_type,
                            '器材': course.get('equipment', '')
                        })
            
            df = pd.DataFrame(data)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            return True
        except Exception as e:
            import logging
            logging.error(f"导出CSV失败: {str(e)}")
            return False
    
    def swap_courses(self, course1, course2, permanent=False):
        """交换两节课程"""
        if permanent:
            # 永久修改课表
            day1, week_type1 = course1['day'], course1['week_type']
            day2, week_type2 = course2['day'], course2['week_type']
            
            courses1 = self.schedule.get(day1, {}).get(week_type1, [])
            courses2 = self.schedule.get(day2, {}).get(week_type2, [])
            
            # 找到课程在列表中的位置
            idx1 = next((i for i, c in enumerate(courses1) if c['name'] == course1['name'] and 
                        c['start_time'] == course1['start_time']), -1)
            idx2 = next((i for i, c in enumerate(courses2) if c['name'] == course2['name'] and 
                        c['start_time'] == course2['start_time']), -1)
            
            if idx1 != -1 and idx2 != -1:
                # 交换课程
                temp = courses1[idx1].copy()
                courses1[idx1] = courses2[idx2].copy()
                courses2[idx2] = temp
                
                # 更新时间信息
                courses1[idx1]['day'] = day1
                courses1[idx1]['week_type'] = week_type1
                courses2[idx2]['day'] = day2
                courses2[idx2]['week_type'] = week_type2
                
                # 保存更改
                self.save_data()
        else:
            # 仅今日生效，使用临时课表覆盖
            today = datetime.now().strftime('%Y-%m-%d')
            today_schedule = self.get_today_schedule()
            
            # 找到课程在今日课表中的位置
            idx1 = next((i for i, c in enumerate(today_schedule) if c['name'] == course1['name'] and 
                        c['start_time'] == course1['start_time']), -1)
            idx2 = next((i for i, c in enumerate(today_schedule) if c['name'] == course2['name'] and 
                        c['start_time'] == course2['start_time']), -1)
            
            if idx1 != -1 and idx2 != -1:
                # 交换课程
                temp = today_schedule[idx1].copy()
                today_schedule[idx1] = today_schedule[idx2].copy()
                today_schedule[idx2] = temp
                
                # 设置临时课表
                self.set_temp_schedule(today, today_schedule)