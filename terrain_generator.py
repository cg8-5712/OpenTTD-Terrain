#!/usr/bin/env python3
"""
地形生成器 - 主程序入口
"""
import sys
import os

# 确保PyQt5正确导入
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

def main():
    """程序主入口"""
    # 设置高DPI支持
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("地形生成器")
    
    # 导入主窗口（确保在QApplication之后）
    from ui.main_window import MainWindow
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()