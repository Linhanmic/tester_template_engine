#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的 PyQt GUI，用于选择模板、多个 CSV 数据文件并生成 Tester 脚本
运行: python gui.py
"""
import sys
import os
import traceback
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QListWidget, QTextEdit, QMessageBox
)
from PyQt5.QtCore import Qt

# 从库中导入生成器
from tester_template_engine import TesterScriptGenerator

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tester 模板生成器")
        self.resize(800, 500)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        central.setLayout(layout)

        # 模板选择
        t_layout = QHBoxLayout()
        t_layout.addWidget(QLabel("模板文件:"))
        self.template_edit = QLineEdit()
        t_layout.addWidget(self.template_edit)
        t_btn = QPushButton("浏览")
        t_btn.clicked.connect(self.browse_template)
        t_layout.addWidget(t_btn)
        layout.addLayout(t_layout)

        # 数据文件（多个）
        d_layout = QHBoxLayout()
        left_v = QVBoxLayout()
        left_v.addWidget(QLabel("数据文件 (CSV，可多个):"))
        self.data_list = QListWidget()
        left_v.addWidget(self.data_list)
        d_btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add_data_files)
        remove_btn = QPushButton("移除")
        remove_btn.clicked.connect(self.remove_selected_data)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear_data_list)
        d_btn_layout.addWidget(add_btn)
        d_btn_layout.addWidget(remove_btn)
        d_btn_layout.addWidget(clear_btn)
        left_v.addLayout(d_btn_layout)
        d_layout.addLayout(left_v)

        # 输出文件
        right_v = QVBoxLayout()
        right_v.addWidget(QLabel("输出文件:"))
        of_layout = QHBoxLayout()
        self.output_edit = QLineEdit()
        of_layout.addWidget(self.output_edit)
        of_btn = QPushButton("浏览")
        of_btn.clicked.connect(self.browse_output)
        of_layout.addWidget(of_btn)
        right_v.addLayout(of_layout)

        # 生成按钮
        gen_btn = QPushButton("生成脚本")
        gen_btn.clicked.connect(self.generate_script)
        right_v.addWidget(gen_btn)

        d_layout.addLayout(right_v)
        layout.addLayout(d_layout)

        # 日志输出
        layout.addWidget(QLabel("日志: "))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

    def browse_template(self):
        fname, _ = QFileDialog.getOpenFileName(self, "选择模板文件", os.getcwd(), "模板 (*.txt *.tmpl *.j2);;All Files (*)")
        if fname:
            self.template_edit.setText(fname)

    def add_data_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择数据文件", os.getcwd(), "CSV 文件 (*.csv);;All Files (*)")
        for f in files:
            if f and not self.is_in_data_list(f):
                self.data_list.addItem(f)

    def is_in_data_list(self, path):
        for i in range(self.data_list.count()):
            if self.data_list.item(i).text() == path:
                return True
        return False

    def remove_selected_data(self):
        for item in self.data_list.selectedItems():
            self.data_list.takeItem(self.data_list.row(item))

    def clear_data_list(self):
        self.data_list.clear()

    def browse_output(self):
        fname, _ = QFileDialog.getSaveFileName(self, "选择输出文件", os.path.join(os.getcwd(), "output.tester"), "Tester 脚本 (*.tester);;All Files (*)")
        if fname:
            self.output_edit.setText(fname)

    def append_log(self, text: str):
        self.log_text.append(text)
        # 自动滚动到末尾
        self.log_text.moveCursor(self.log_text.textCursor().End)

    def generate_script(self):
        template_path = self.template_edit.text().strip()
        output_path = self.output_edit.text().strip()
        data_files = [self.data_list.item(i).text() for i in range(self.data_list.count())]

        if not template_path or not os.path.exists(template_path):
            QMessageBox.warning(self, "错误", "请选择有效的模板文件")
            return
        if not output_path:
            QMessageBox.warning(self, "错误", "请选择输出文件路径")
            return
        if not data_files:
            QMessageBox.warning(self, "错误", "请至少添加一个 CSV 数据文件")
            return

        self.append_log("开始生成...")
        try:
            gen = TesterScriptGenerator()
            # 加载所有数据文件
            for f in data_files:
                var_name = os.path.splitext(os.path.basename(f))[0]
                self.append_log(f"加载数据: {f} -> 变量名: {var_name}")
                gen.load_data_from_csv(f, var_name)

            # 加载模板
            gen.load_template(template_path)
            template_name = os.path.splitext(os.path.basename(template_path))[0]
            self.append_log(f"加载模板: {template_path} -> 模板名: {template_name}")

            # 生成
            gen.generate_script(template_name, output_path)
            self.append_log(f"生成成功: {output_path}")
            QMessageBox.information(self, "完成", f"生成成功: {output_path}")

        except Exception as e:
            tb = traceback.format_exc()
            self.append_log(f"生成失败: {e}\n{tb}")
            QMessageBox.critical(self, "错误", f"生成时发生错误: {e}")


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
