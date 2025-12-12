"""
预览画布模块 - 地形预览和交互
"""
import numpy as np
from PyQt5.QtWidgets import QWidget, QOpenGLWidget
from PyQt5.QtGui import QPainter, QImage, QColor, QFont, QPen, QPixmap
from PyQt5.QtCore import Qt, QPoint, QRect, QTimer
from PyQt5.QtOpenGL import QGLFormat, QGL


class PreviewCanvas(QWidget):
    """预览画布 - 支持2D和简单3D预览"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 显示选项
        self.show_heightmap = True
        self.show_slope = False
        self.show_rivers = False
        self.show_grid = False
        self.show_axes = True
        self.show_stats = True
        
        # 视图状态
        self.view_mode = "2D"  # "2D" 或 "3D"
        self.zoom_level = 1.0
        self.pan_offset = QPoint(0, 0)
        self.rotation_x = 30.0
        self.rotation_y = 45.0
        
        # 数据
        self.heightmap = None
        self.heightmap_image = None
        
        # 鼠标交互
        self.last_mouse_pos = None
        self.is_dragging = False
        
        # 初始化UI
        self._init_ui()
        
        # 设置鼠标跟踪
        self.setMouseTracking(True)
        
    def _init_ui(self):
        """初始化UI"""
        self.setMinimumSize(400, 400)
        
        # 设置背景色
        self.setStyleSheet("background-color: #2b2b2b;")
        
        # 设置焦点策略，以便接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
    
    # ====================== 数据设置 ======================
    
    def set_heightmap(self, heightmap):
        """设置高度图数据"""
        if heightmap is None:
            return
        
        self.heightmap = heightmap
        
        # 创建预览图像
        self._create_heightmap_image()
        
        # 更新显示
        self.update()
    
    def clear(self):
        """清除数据"""
        self.heightmap = None
        self.heightmap_image = None
        self.update()
    
    def _create_heightmap_image(self):
        """从高度图创建预览图像"""
        if self.heightmap is None:
            return
        
        # 归一化高度数据到0-255
        height_normalized = (self.heightmap - np.min(self.heightmap)) / (np.max(self.heightmap) - np.min(self.heightmap) + 1e-8)
        height_uint8 = (height_normalized * 255).astype(np.uint8)
        
        # 创建QImage
        h, w = height_uint8.shape[:2]
        bytes_per_line = w
        self.heightmap_image = QImage(height_uint8.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        # 保持对数据的引用，避免被垃圾回收
        self.heightmap_image._array_ref = height_uint8
    
    # ====================== 绘图函数 ======================
    
    def paintEvent(self, event):
        """绘图事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), QColor(43, 43, 43))
        
        if self.heightmap is None:
            self._draw_no_data(painter)
            return
        
        if self.view_mode == "2D":
            self._draw_2d_view(painter)
        else:
            self._draw_3d_fallback(painter)
        
        # 绘制叠加信息
        if self.show_stats:
            self._draw_statistics(painter)
        
        if self.show_axes:
            self._draw_axes(painter)
    
    def _draw_no_data(self, painter):
        """绘制无数据提示"""
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Arial", 16))
        
        text = "点击'生成地形'开始"
        text_rect = painter.fontMetrics().boundingRect(text)
        text_pos = QPoint(
            self.width() // 2 - text_rect.width() // 2,
            self.height() // 2 - text_rect.height() // 2
        )
        
        painter.drawText(text_pos, text)
        
        # 绘制提示
        painter.setFont(QFont("Arial", 10))
        hint = "调整左侧参数并点击生成按钮"
        hint_rect = painter.fontMetrics().boundingRect(hint)
        hint_pos = QPoint(
            self.width() // 2 - hint_rect.width() // 2,
            self.height() // 2 + text_rect.height()
        )
        painter.drawText(hint_pos, hint)
    
    def _draw_2d_view(self, painter):
        """绘制2D视图"""
        if self.heightmap_image is None:
            return
        
        # 计算绘制区域
        img_width = self.heightmap_image.width()
        img_height = self.heightmap_image.height()
        
        # 保持宽高比
        view_width = self.width() - 40
        view_height = self.height() - 40
        
        scale = min(view_width / img_width, view_height / img_height) * self.zoom_level
        draw_width = int(img_width * scale)
        draw_height = int(img_height * scale)
        
        # 居中显示
        draw_x = (self.width() - draw_width) // 2 + self.pan_offset.x()
        draw_y = (self.height() - draw_height) // 2 + self.pan_offset.y()
        draw_rect = QRect(draw_x, draw_y, draw_width, draw_height)
        
        # 绘制高度图
        painter.drawImage(draw_rect, self.heightmap_image)
        
        # 绘制边框
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRect(draw_rect)
        
        # 绘制网格
        if self.show_grid:
            self._draw_grid(painter, draw_rect, img_width, img_height)
    
    def _draw_3d_fallback(self, painter):
        """绘制3D视图（简易版）"""
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Arial", 14))
        
        text = "3D视图 (OpenGL版本)"
        text_rect = painter.fontMetrics().boundingRect(text)
        text_pos = QPoint(
            self.width() // 2 - text_rect.width() // 2,
            self.height() // 2 - text_rect.height() // 2
        )
        
        painter.drawText(text_pos, text)
        
        # 绘制简单的高度图预览
        if self.heightmap_image:
            # 在右下角绘制小预览
            preview_size = 200
            preview_rect = QRect(
                self.width() - preview_size - 20,
                self.height() - preview_size - 20,
                preview_size, preview_size
            )
            painter.drawImage(preview_rect, self.heightmap_image)
            
            # 绘制边框
            painter.setPen(QPen(QColor(100, 100, 100), 2))
            painter.drawRect(preview_rect)
    
    def _draw_grid(self, painter, draw_rect, img_width, img_height):
        """绘制网格"""
        grid_size = 50  # 网格间距（像素）
        
        painter.setPen(QPen(QColor(100, 100, 100, 100), 1))
        
        # 计算网格线数量和间距
        num_grid_x = img_width // grid_size + 1
        num_grid_y = img_height // grid_size + 1
        
        # 绘制垂直线
        for i in range(num_grid_x):
            x = draw_rect.left() + i * grid_size * draw_rect.width() / img_width
            painter.drawLine(int(x), draw_rect.top(), int(x), draw_rect.bottom())
        
        # 绘制水平线
        for i in range(num_grid_y):
            y = draw_rect.top() + i * grid_size * draw_rect.height() / img_height
            painter.drawLine(draw_rect.left(), int(y), draw_rect.right(), int(y))
    
    def _draw_statistics(self, painter):
        """绘制统计信息"""
        if self.heightmap is None:
            return
        
        stats_text = [
            f"尺寸: {self.heightmap.shape[1]}×{self.heightmap.shape[0]}",
            f"最大高度: {np.max(self.heightmap):.3f}",
            f"最小高度: {np.min(self.heightmap):.3f}",
            f"平均高度: {np.mean(self.heightmap):.3f}",
            f"标准差: {np.std(self.heightmap):.3f}"
        ]
        
        painter.setPen(QColor(220, 220, 220))
        painter.setFont(QFont("Arial", 9))
        
        # 在左上角绘制
        y_offset = 10
        for text in stats_text:
            painter.drawText(10, y_offset, text)
            y_offset += 20
    
    def _draw_axes(self, painter):
        """绘制坐标轴"""
        if self.view_mode == "2D":
            # 绘制2D坐标轴
            axis_length = 50
            origin_x = 60
            origin_y = self.height() - 60
            
            painter.setPen(QPen(QColor(255, 100, 100), 2))
            painter.drawLine(origin_x, origin_y, origin_x + axis_length, origin_y)  # X轴
            
            painter.setPen(QPen(QColor(100, 255, 100), 2))
            painter.drawLine(origin_x, origin_y, origin_x, origin_y - axis_length)  # Y轴
            
            # 轴标签
            painter.setPen(QColor(200, 200, 200))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(origin_x + axis_length + 5, origin_y + 5, "X")
            painter.drawText(origin_x - 15, origin_y - axis_length - 5, "Y")
    
    # ====================== 鼠标交互 ======================
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.last_mouse_pos = event.pos()
            self.is_dragging = True
            
        elif event.button() == Qt.RightButton:
            # 右键可以快速切换视图模式
            self.view_mode = "3D" if self.view_mode == "2D" else "2D"
            self.update()
        
        event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.is_dragging and self.last_mouse_pos:
            delta = event.pos() - self.last_mouse_pos
            
            if self.view_mode == "2D":
                # 2D视图：平移
                self.pan_offset += delta
            elif self.view_mode == "3D":
                # 3D视图：旋转
                self.rotation_y += delta.x() * 0.5
                self.rotation_x += delta.y() * 0.5
                self.rotation_x = max(-90, min(90, self.rotation_x))
            
            self.last_mouse_pos = event.pos()
            self.update()
        
        event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.last_mouse_pos = None
        
        event.accept()
    
    def wheelEvent(self, event):
        """鼠标滚轮事件 - 缩放"""
        delta = event.angleDelta().y()
        
        if self.view_mode == "2D":
            # 2D视图：缩放
            zoom_factor = 1.1 if delta > 0 else 0.9
            self.zoom_level *= zoom_factor
            self.zoom_level = max(0.1, min(10.0, self.zoom_level))
        
        self.update()
        event.accept()
    
    # ====================== 键盘交互 ======================
    
    def keyPressEvent(self, event):
        """键盘按下事件"""
        if event.key() == Qt.Key_Space:
            # 空格键切换视图模式
            self.view_mode = "3D" if self.view_mode == "2D" else "2D"
            self.update()
            
        elif event.key() == Qt.Key_G:
            # G键切换网格显示
            self.show_grid = not self.show_grid
            self.update()
            
        elif event.key() == Qt.Key_A:
            # A键切换坐标轴显示
            self.show_axes = not self.show_axes
            self.update()
            
        elif event.key() == Qt.Key_R:
            # R键重置视图
            self.zoom_level = 1.0
            self.pan_offset = QPoint(0, 0)
            self.rotation_x = 30.0
            self.rotation_y = 45.0
            self.update()
            
        elif event.key() == Qt.Key_Equal or event.key() == Qt.Key_Plus:
            # +键放大
            self.zoom_level *= 1.1
            self.update()
            
        elif event.key() == Qt.Key_Minus or event.key() == Qt.Key_Underscore:
            # -键缩小
            self.zoom_level *= 0.9
            self.update()
        
        event.accept()
    
    # ====================== 工具方法 ======================
    
    def set_view_mode(self, mode):
        """设置视图模式"""
        if mode in ["2D", "3D"]:
            self.view_mode = mode
            self.update()
    
    def get_current_image(self):
        """获取当前显示的图像"""
        return self.heightmap_image
    
    def cleanup(self):
        """清理资源"""
        self.heightmap = None
        self.heightmap_image = None


# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    import numpy as np
    
    app = QApplication(sys.argv)
    
    # 创建测试数据
    test_data = np.random.rand(256, 256)
    
    canvas = PreviewCanvas()
    canvas.set_heightmap(test_data)
    canvas.show()
    
    sys.exit(app.exec_())