from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QComboBox, QColorDialog, QTableWidget, QTableWidgetItem, QSpinBox,
                             QTimeEdit, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QSettings, QTime
from PyQt5.QtGui import QColor
import json
import pandas as pd
from datetime import datetime, timedelta

class TimetableEditor(QWidget):
    def __init__(self, course_manager):
        super().__init__()
        self.course_manager = course_manager
        self.settings = QSettings('SCS', 'Timetable_Preferences')
        self.initUI()
        
    def initUI(self):
        # 主布局
        main_layout = QVBoxLayout()
        
        # 科目库管理区域
        subject_group = QGroupBox("科目库管理")
        subject_layout = QVBoxLayout()
        
        # 科目列表
        self.subject_table = QTableWidget()
        self.subject_table.setColumnCount(5)
        self.subject_table.setHorizontalHeaderLabels(["科目名称", "颜色", "教师", "备注", "器材"])
        subject_layout.addWidget(self.subject_table)
        
        # 科目操作按钮
        btn_layout = QHBoxLayout()
        self.add_subject_btn = QPushButton("添加科目")
        self.add_subject_btn.clicked.connect(self.add_subject)
        btn_layout.addWidget(self.add_subject_btn)
        
        self.remove_subject_btn = QPushButton("删除科目")
        self.remove_subject_btn.clicked.connect(self.remove_subject)
        btn_layout.addWidget(self.remove_subject_btn)
        
        subject_layout.addLayout(btn_layout)
        subject_group.setLayout(subject_layout)
        main_layout.addWidget(subject_group)
        
        # 时间表配置区域
        timetable_group = QGroupBox("时间表配置")
        timetable_layout = QVBoxLayout()
        
        # 时间表列表
        self.timetable_table = QTableWidget()
        self.timetable_table.setColumnCount(3)
        self.timetable_table.setHorizontalHeaderLabels(["时间点", "类型", "描述"])
        timetable_layout.addWidget(self.timetable_table)
        
        # 时间表操作按钮
        time_btn_layout = QHBoxLayout()
        self.add_timepoint_btn = QPushButton("添加时间点")
        self.add_timepoint_btn.clicked.connect(self.add_timepoint)
        time_btn_layout.addWidget(self.add_timepoint_btn)
        
        self.remove_timepoint_btn = QPushButton("删除时间点")
        self.remove_timepoint_btn.clicked.connect(self.remove_timepoint)
        time_btn_layout.addWidget(self.remove_timepoint_btn)
        
        timetable_layout.addLayout(time_btn_layout)
        timetable_group.setLayout(timetable_layout)
        main_layout.addWidget(timetable_group)
        
        # 导入导出按钮
        io_btn_layout = QHBoxLayout()
        self.import_btn = QPushButton("从Excel导入")
        self.import_btn.clicked.connect(self.import_from_excel)
        io_btn_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("导出为JSON")
        self.export_btn.clicked.connect(self.export_to_json)
        io_btn_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(io_btn_layout)
        
        self.setLayout(main_layout)
        self.load_data()
    
    def add_subject(self):
        # 实现添加科目功能
        pass
        
    def remove_subject(self):
        # 实现删除科目功能
        pass
        
    def add_timepoint(self):
        """添加新的时间点到时间表"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加时间点")
        
        layout = QVBoxLayout()
        
        # 时间点
        time_layout = QHBoxLayout()
        time_label = QLabel("时间:")
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        time_layout.addWidget(time_label)
        time_layout.addWidget(self.time_edit)
        layout.addLayout(time_layout)
        
        # 类型选择
        type_layout = QHBoxLayout()
        type_label = QLabel("类型:")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["上课", "休息", "分割线"])
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # 描述信息
        desc_layout = QHBoxLayout()
        desc_label = QLabel("描述:")
        self.desc_edit = QLineEdit()
        desc_layout.addWidget(desc_label)
        desc_layout.addWidget(self.desc_edit)
        layout.addLayout(desc_layout)
        
        # 确认按钮
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            row = self.timetable_table.rowCount()
            self.timetable_table.insertRow(row)
            
            time_item = QTableWidgetItem(self.time_edit.time().toString("HH:mm"))
            self.timetable_table.setItem(row, 0, time_item)
            
            type_item = QTableWidgetItem(self.type_combo.currentText())
            self.timetable_table.setItem(row, 1, type_item)
            
            desc_item = QTableWidgetItem(self.desc_edit.text())
            self.timetable_table.setItem(row, 2, desc_item)
        
    def remove_timepoint(self):
        """从时间表中删除选中的时间点"""
        selected = self.timetable_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择要删除的时间点")
            return
            
        reply = QMessageBox.question(self, "确认", "确定要删除选中的时间点吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            for item in selected:
                self.timetable_table.removeRow(item.row())
        
    def import_from_excel(self):
        """从Excel文件导入课表数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Excel文件", "", "Excel Files (*.xlsx *.xls)")
            
        if not file_path:
            return
            
        try:
            df = pd.read_excel(file_path)
            
            # 清空现有数据
            self.subject_table.setRowCount(0)
            self.timetable_table.setRowCount(0)
            
            # 导入科目数据
            if "科目名称" in df.columns:
                for _, row in df.iterrows():
                    if pd.notna(row["科目名称"]):
                        subject_row = self.subject_table.rowCount()
                        self.subject_table.insertRow(subject_row)
                        
                        self.subject_table.setItem(subject_row, 0, QTableWidgetItem(str(row["科目名称"])))
                        
                        if "颜色" in df.columns and pd.notna(row["颜色"]):
                            color_item = QTableWidgetItem()
                            color_item.setBackground(QColor(str(row["颜色"])))
                            self.subject_table.setItem(subject_row, 1, color_item)
                        
                        if "教师" in df.columns and pd.notna(row["教师"]):
                            self.subject_table.setItem(subject_row, 2, QTableWidgetItem(str(row["教师"])))
                        
                        if "备注" in df.columns and pd.notna(row["备注"]):
                            self.subject_table.setItem(subject_row, 3, QTableWidgetItem(str(row["备注"])))
                        
                        if "器材" in df.columns and pd.notna(row["器材"]):
                            self.subject_table.setItem(subject_row, 4, QTableWidgetItem(str(row["器材"])))
            
            # 导入时间表数据
            if "时间点" in df.columns:
                for _, row in df.iterrows():
                    if pd.notna(row["时间点"]):
                        time_row = self.timetable_table.rowCount()
                        self.timetable_table.insertRow(time_row)
                        
                        self.timetable_table.setItem(time_row, 0, QTableWidgetItem(str(row["时间点"])))
                        
                        if "类型" in df.columns and pd.notna(row["类型"]):
                            self.timetable_table.setItem(time_row, 1, QTableWidgetItem(str(row["类型"])))
                        
                        if "描述" in df.columns and pd.notna(row["描述"]):
                            self.timetable_table.setItem(time_row, 2, QTableWidgetItem(str(row["描述"])))
            
            QMessageBox.information(self, "成功", "导入完成！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
        
    def export_to_json(self):
        """将课表数据导出为JSON文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存为JSON", "", "JSON Files (*.json)")
            
        if not file_path:
            return
            
        try:
            data = {
                "subjects": [],
                "timetable": []
            }
            
            # 导出科目数据
            for row in range(self.subject_table.rowCount()):
                subject = {
                    "name": self.subject_table.item(row, 0).text() if self.subject_table.item(row, 0) else "",
                    "color": self.subject_table.item(row, 1).background().color().name() if self.subject_table.item(row, 1) else "",
                    "teacher": self.subject_table.item(row, 2).text() if self.subject_table.item(row, 2) else "",
                    "note": self.subject_table.item(row, 3).text() if self.subject_table.item(row, 3) else "",
                    "equipment": self.subject_table.item(row, 4).text() if self.subject_table.item(row, 4) else ""
                }
                data["subjects"].append(subject)
            
            # 导出时间表数据
            for row in range(self.timetable_table.rowCount()):
                timepoint = {
                    "time": self.timetable_table.item(row, 0).text() if self.timetable_table.item(row, 0) else "",
                    "type": self.timetable_table.item(row, 1).text() if self.timetable_table.item(row, 1) else "",
                    "description": self.timetable_table.item(row, 2).text() if self.timetable_table.item(row, 2) else ""
                }
                data["timetable"].append(timepoint)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                
            QMessageBox.information(self, "成功", "导出完成！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
        
    def load_data(self):
        """从配置文件加载保存的数据"""
        try:
            # 加载科目数据
            subjects = json.loads(self.settings.value("subjects", "[]"))
            self.subject_table.setRowCount(len(subjects))
            
            for i, subject in enumerate(subjects):
                self.subject_table.setItem(i, 0, QTableWidgetItem(subject.get("name", "")))
                
                color_item = QTableWidgetItem()
                color_item.setBackground(QColor(subject.get("color", "#4a86e8")))
                self.subject_table.setItem(i, 1, color_item)
                
                self.subject_table.setItem(i, 2, QTableWidgetItem(subject.get("teacher", "")))
                self.subject_table.setItem(i, 3, QTableWidgetItem(subject.get("note", "")))
                self.subject_table.setItem(i, 4, QTableWidgetItem(subject.get("equipment", "")))
            
            # 加载时间表数据
            timetable = json.loads(self.settings.value("timetable", "[]"))
            self.timetable_table.setRowCount(len(timetable))
            
            for i, timepoint in enumerate(timetable):
                self.timetable_table.setItem(i, 0, QTableWidgetItem(timepoint.get("time", "")))
                self.timetable_table.setItem(i, 1, QTableWidgetItem(timepoint.get("type", "")))
                self.timetable_table.setItem(i, 2, QTableWidgetItem(timepoint.get("description", "")))
        except Exception as e:
            logging.error(f"加载数据失败: {str(e)}")
        
    def save_data(self):
        """保存数据到配置文件"""
        try:
            # 保存科目数据
            subjects = []
            for row in range(self.subject_table.rowCount()):
                subject = {
                    "name": self.subject_table.item(row, 0).text() if self.subject_table.item(row, 0) else "",
                    "color": self.subject_table.item(row, 1).background().color().name() if self.subject_table.item(row, 1) else "",
                    "teacher": self.subject_table.item(row, 2).text() if self.subject_table.item(row, 2) else "",
                    "note": self.subject_table.item(row, 3).text() if self.subject_table.item(row, 3) else "",
                    "equipment": self.subject_table.item(row, 4).text() if self.subject_table.item(row, 4) else ""
                }
                subjects.append(subject)
            
            # 保存时间表数据
            timetable = []
            for row in range(self.timetable_table.rowCount()):
                timepoint = {
                    "time": self.timetable_table.item(row, 0).text() if self.timetable_table.item(row, 0) else "",
                    "type": self.timetable_table.item(row, 1).text() if self.timetable_table.item(row, 1) else "",
                    "description": self.timetable_table.item(row, 2).text() if self.timetable_table.item(row, 2) else ""
                }
                timetable.append(timepoint)
            
            self.settings.setValue("subjects", json.dumps(subjects))
            self.settings.setValue("timetable", json.dumps(timetable))
        except Exception as e:
            logging.error(f"保存数据失败: {str(e)}")
        
    def get_current_week_type(self, date):
        """
        根据学期开始日期计算单双周
        返回值:
            'odd': 单周
            'even': 双周
            'both': 单双周都有
        """
        # 实现单双周逻辑
        pass