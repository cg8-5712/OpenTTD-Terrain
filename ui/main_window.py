"""
主窗口模块 - 地形生成器主界面
"""
import sys
import os
from datetime import datetime
from pathlib import Path

import numpy as np
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSplitter, QStatusBar, QMenuBar, QMenu, QAction, 
                             QFileDialog, QMessageBox, QProgressBar, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QKeySequence

# ==================== 修复导入部分 ====================
# 添加项目路径到sys.path以便正确导入
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入自定义模块（添加错误处理）
try:
    from ui.control_panel import ControlPanel
    print("✓ ControlPanel 导入成功")
except ImportError as e:
    print(f"✗ ControlPanel 导入失败: {e}")
    # 创建虚拟类作为回退
    class ControlPanel(QWidget):
        parameters_changed = pyqtSignal(object)
        generate_requested = pyqtSignal()
        export_requested = pyqtSignal()
        def __init__(self): super().__init__()
        def get_parameters(self): return None
        def set_enabled(self, enabled): pass
        def update_statistics(self, stats): pass
        def reset_to_defaults(self): pass

try:
    from ui.preview_canvas import PreviewCanvas
    print("✓ PreviewCanvas 导入成功")
except ImportError as e:
    print(f"✗ PreviewCanvas 导入失败: {e}")
    # 创建虚拟类作为回退
    class PreviewCanvas(QWidget):
        def __init__(self): super().__init__()
        def set_heightmap(self, hm): pass
        def clear(self): pass
        def update(self): pass
        def cleanup(self): pass

try:
    from core.terrain_generator import TerrainGenerator
    print("✓ TerrainGenerator 导入成功")
except ImportError as e:
    print(f"✗ TerrainGenerator 导入失败: {e}")
    # 创建虚拟类作为回退
    class TerrainGenerator:
        def __init__(self): pass
        def generate_tectonic_base(self, params): return np.zeros((params.size[1], params.size[0]))
        def generate_regions(self, params): return None
        def generate_climate(self, params, regions): return None
        def simulate_erosion(self, heightmap, params, climate, regions): return heightmap
        def post_process(self, heightmap, params): return heightmap

try:
    from core.terrain_params import TerrainParams
    print("✓ TerrainParams 导入成功")
except ImportError as e:
    print(f"✗ TerrainParams 导入失败: {e}")
    # 创建虚拟类作为回退
    class TerrainParams:
        def __init__(self):
            self.size = (1024, 1024)
            self.seed = None
            self.tectonic_uplift = 0.7
            self.tectonic_pattern = "convergent"
            self.rock_hardness = 0.5
            self.terrain_age = 0.7
            self.precipitation = 0.6
            self.temperature = 0.4
            self.wind_intensity = 0.3
            self.distance_to_coast = 0.5
            self.num_regions = 4
            self.region_contrast = 0.6
            self.erosion_iterations = 10
            self.river_intensity = 0.8
            self.glacial_intensity = 0.3
        
        def __dict__(self):
            return self.__dict__.copy()

try:
    from utils.file_io import save_heightmap, save_mesh, save_parameters, load_parameters
    print("✓ file_io 模块导入成功")
except ImportError as e:
    print(f"✗ file_io 模块导入失败: {e}")
    # 创建虚拟函数作为回退
    def save_heightmap(heightmap, filepath): print(f"虚拟保存高度图: {filepath}")
    def save_mesh(heightmap, filepath): print(f"虚拟保存网格: {filepath}")
    def save_parameters(params, filepath): print(f"虚拟保存参数: {filepath}")
    def load_parameters(filepath):
        print(f"虚拟加载参数: {filepath}")
        return TerrainParams()

try:
    from utils.image_utils import array_to_qimage, generate_texture
    print("✓ image_utils 模块导入成功")
except ImportError as e:
    print(f"✗ image_utils 模块导入失败: {e}")
    # 创建虚拟函数作为回退
    def array_to_qimage(array): 
        from PyQt5.QtGui import QImage
        if array is None:
            return QImage()
        return QImage(array.shape[1], array.shape[0], QImage.Format_Grayscale8)
    
    def generate_texture(heightmap):
        from PIL import Image
        if heightmap is None:
            return Image.new('RGB', (100, 100))
        return Image.new('RGB', (heightmap.shape[1], heightmap.shape[0]))

try:
    from presets.preset_manager import PresetManager
    print("✓ PresetManager 导入成功")
except ImportError as e:
    print(f"✗ PresetManager 导入失败: {e}")
    # 创建虚拟类作为回退
    class PresetManager:
        def __init__(self, presets_dir="./presets"): pass
        def list_presets(self): return []
        def load_preset(self, name): return TerrainParams()
        def save_preset(self, name, params): pass
        def delete_preset(self, name): pass
        def create_default_presets(self): return []

print("=" * 50)
print("所有模块导入检查完成")
print("=" * 50)
# ==================== 导入部分结束 ====================



class GenerationThread(QThread):
    """地形生成线程（避免界面卡顿）"""
    
    # 信号定义
    generation_started = pyqtSignal()
    generation_progress = pyqtSignal(int, str)  # 进度百分比, 状态消息
    generation_finished = pyqtSignal(np.ndarray, dict)  # 高度图数据, 元数据
    generation_error = pyqtSignal(str)
    
    def __init__(self, params):
        super().__init__()
        self.params = params
        self.generator = TerrainGenerator()
        self.is_running = True
        
    def run(self):
        """线程主函数"""
        try:
            self.generation_started.emit()
            
            # 生成地形（分步报告进度）
            self.generation_progress.emit(10, "初始化构造层...")
            tectonic_layer = self.generator.generate_tectonic_base(self.params)
            
            self.generation_progress.emit(30, "分区处理...")
            regions = self.generator.generate_regions(self.params)
            
            self.generation_progress.emit(50, "气候模拟...")
            climate = self.generator.generate_climate(self.params, regions)
            
            self.generation_progress.emit(70, "侵蚀模拟...")
            heightmap = self.generator.simulate_erosion(
                tectonic_layer, self.params, climate, regions
            )
            
            self.generation_progress.emit(90, "后处理...")
            heightmap = self.generator.post_process(heightmap, self.params)
            
            # 准备元数据
            metadata = {
                'params': self.params.__dict__,
                'generation_time': datetime.now().isoformat(),
                'size': self.params.size,
                'seed': self.params.seed,
                'max_elevation': float(np.max(heightmap)),
                'min_elevation': float(np.min(heightmap)),
                'mean_elevation': float(np.mean(heightmap))
            }
            
            self.generation_progress.emit(100, "生成完成!")
            self.generation_finished.emit(heightmap, metadata)
            
        except Exception as e:
            self.generation_error.emit(str(e))
    
    def stop(self):
        """停止生成"""
        self.is_running = False


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化变量
        self.current_heightmap = None
        self.current_params = None
        self.current_metadata = None
        self.export_dir = Path("./exports")
        self.export_dir.mkdir(exist_ok=True)
        
        # 设置窗口属性
        self.setWindowTitle("地形生成器 v1.0")
        self.setGeometry(100, 100, 1400, 800)
        
        # 创建UI组件
        self._create_menu_bar()
        self._create_status_bar()
        self._create_main_layout()
        
        # 初始化生成器
        self.generator_thread = None
        
        # 设置定时器（用于更新预览）
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_preview)
        self.update_timer.start(100)  # 每100ms更新一次
        
    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件(&F)')
        
        # 新建
        new_action = QAction('新建地形(&N)', self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._new_terrain)
        file_menu.addAction(new_action)
        
        # 打开参数
        open_action = QAction('打开参数(&O)...', self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._open_parameters)
        file_menu.addAction(open_action)
        
        # 保存参数
        save_action = QAction('保存参数(&S)...', self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save_parameters)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        # 导出子菜单
        export_menu = file_menu.addMenu('导出(&E)')
        
        # 导出高度图
        export_heightmap_action = QAction('导出高度图(&H)...', self)
        export_heightmap_action.triggered.connect(lambda: self._export_heightmap())
        export_menu.addAction(export_heightmap_action)
        
        # 导出纹理
        export_texture_action = QAction('导出纹理(&T)...', self)
        export_texture_action.triggered.connect(lambda: self._export_texture())
        export_menu.addAction(export_texture_action)
        
        # 导出3D模型
        export_mesh_action = QAction('导出3D模型(&M)...', self)
        export_mesh_action.triggered.connect(lambda: self._export_mesh())
        export_menu.addAction(export_mesh_action)
        
        # 导出全部
        export_all_action = QAction('导出全部(&A)...', self)
        export_all_action.triggered.connect(self._export_all)
        export_menu.addAction(export_all_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction('退出(&Q)', self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu('编辑(&E)')
        
        # 复制参数
        copy_params_action = QAction('复制参数(&C)', self)
        copy_params_action.setShortcut(QKeySequence.Copy)
        copy_params_action.triggered.connect(self._copy_parameters)
        edit_menu.addAction(copy_params_action)
        
        # 粘贴参数
        paste_params_action = QAction('粘贴参数(&V)', self)
        paste_params_action.setShortcut(QKeySequence.Paste)
        paste_params_action.triggered.connect(self._paste_parameters)
        edit_menu.addAction(paste_params_action)
        
        # 重置参数
        reset_action = QAction('重置参数(&R)', self)
        reset_action.setShortcut('Ctrl+R')
        reset_action.triggered.connect(self._reset_parameters)
        edit_menu.addAction(reset_action)
        
        edit_menu.addSeparator()
        
        # 偏好设置
        preferences_action = QAction('偏好设置(&P)...', self)
        preferences_action.triggered.connect(self._open_preferences)
        edit_menu.addAction(preferences_action)
        
        # 生成菜单
        generate_menu = menubar.addMenu('生成(&G)')
        
        # 生成地形
        generate_action = QAction('生成地形(&G)', self)
        generate_action.setShortcut('Ctrl+G')
        generate_action.triggered.connect(self._generate_terrain)
        generate_menu.addAction(generate_action)
        
        # 重新生成
        regenerate_action = QAction('重新生成(&R)', self)
        regenerate_action.setShortcut('F5')
        regenerate_action.triggered.connect(self._regenerate_terrain)
        generate_menu.addAction(regenerate_action)
        
        # 批量生成
        batch_action = QAction('批量生成(&B)...', self)
        batch_action.triggered.connect(self._batch_generate)
        generate_menu.addAction(batch_action)
        
        generate_menu.addSeparator()
        
        # 预设子菜单
        preset_menu = generate_menu.addMenu('预设(&P)')
        self._load_presets_to_menu(preset_menu)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图(&V)')
        
        # 显示图层
        view_menu.addAction('显示高度图', self._toggle_heightmap_view).setCheckable(True)
        view_menu.addAction('显示坡度图', self._toggle_slope_view).setCheckable(True)
        view_menu.addAction('显示河流网络', self._toggle_river_view).setCheckable(True)
        view_menu.addSeparator()
        
        # 显示选项
        view_menu.addAction('显示网格', self._toggle_grid).setCheckable(True)
        view_menu.addAction('显示坐标轴', self._toggle_axes).setCheckable(True)
        view_menu.addAction('显示统计信息', self._toggle_stats).setCheckable(True)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助(&H)')
        
        # 帮助文档
        help_action = QAction('使用帮助(&H)', self)
        help_action.setShortcut(QKeySequence.HelpContents)
        help_action.triggered.connect(self._show_help)
        help_menu.addAction(help_action)
        
        # 关于
        about_action = QAction('关于(&A)...', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # 状态标签
        self.status_bar.showMessage("就绪")
        
    def _create_main_layout(self):
        """创建主布局"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：控制面板
        self.control_panel = ControlPanel()
        self.control_panel.generate_button.clicked.connect(self._generate_terrain)
        self.control_panel.export_button.clicked.connect(self._export_all)
        self.control_panel.parameters_changed.connect(self._on_parameters_changed)
        
        # 右侧：预览画布
        self.preview_canvas = PreviewCanvas()
        
        # 添加到分割器
        splitter.addWidget(self.control_panel)
        splitter.addWidget(self.preview_canvas)
        
        # 设置分割器初始比例
        splitter.setSizes([300, 1100])
        
        # 添加到主布局
        main_layout.addWidget(splitter)
        
    def _load_presets_to_menu(self, preset_menu):
        """加载预设到菜单"""
        try:
            preset_manager = PresetManager()
            presets = preset_manager.list_presets()
            
            for preset_name in presets:
                action = QAction(preset_name, self)
                action.triggered.connect(
                    lambda checked, name=preset_name: self._load_preset(name)
                )
                preset_menu.addAction(action)
                
        except Exception as e:
            QMessageBox.warning(self, "警告", f"加载预设失败: {str(e)}")
    
    # ====================== 事件处理函数 ======================
    
    def _on_parameters_changed(self, params):
        """参数变化时的处理"""
        self.current_params = params
        self.status_bar.showMessage("参数已更新")
        
    def _new_terrain(self):
        """新建地形"""
        if self.current_heightmap is not None:
            reply = QMessageBox.question(
                self, "新建地形",
                "当前地形未保存，是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        self.control_panel.reset_to_defaults()
        self.current_heightmap = None
        self.current_metadata = None
        self.preview_canvas.clear()
        self.status_bar.showMessage("已重置")
        
    def _generate_terrain(self):
        """生成地形"""
        # 获取参数
        params = self.control_panel.get_parameters()
        
        # 检查是否有正在进行的生成任务
        if self.generator_thread and self.generator_thread.isRunning():
            reply = QMessageBox.question(
                self, "正在生成",
                "当前有地形正在生成，是否中断并开始新的生成？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
            else:
                self.generator_thread.stop()
                self.generator_thread.wait()
        
        # 创建并启动生成线程
        self.generator_thread = GenerationThread(params)
        self.generator_thread.generation_started.connect(self._on_generation_started)
        self.generator_thread.generation_progress.connect(self._on_generation_progress)
        self.generator_thread.generation_finished.connect(self._on_generation_finished)
        self.generator_thread.generation_error.connect(self._on_generation_error)
        
        self.generator_thread.start()
        
    def _regenerate_terrain(self):
        """重新生成地形（使用相同参数）"""
        if self.current_params:
            self.control_panel.set_parameters(self.current_params)
            self._generate_terrain()
        else:
            QMessageBox.information(self, "提示", "没有可重新生成的地形参数")
            
    def _batch_generate(self):
        """批量生成"""
        # TODO: 实现批量生成功能
        QMessageBox.information(self, "功能开发中", "批量生成功能正在开发中")
        
    def _load_preset(self, preset_name):
        """加载预设"""
        try:
            preset_manager = PresetManager()
            params = preset_manager.load_preset(preset_name)
            self.control_panel.set_parameters(params)
            self.status_bar.showMessage(f"已加载预设: {preset_name}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载预设失败: {str(e)}")
            
    # ====================== 文件操作 ======================
    
    def _open_parameters(self):
        """打开参数文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开参数文件", str(self.export_dir),
            "JSON文件 (*.json);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                from utils.file_io import load_parameters
                params = load_parameters(file_path)
                self.control_panel.set_parameters(params)
                self.status_bar.showMessage(f"已加载参数: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载参数失败: {str(e)}")
                
    def _save_parameters(self):
        """保存参数文件"""
        if not self.current_params:
            QMessageBox.warning(self, "警告", "没有可保存的参数")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存参数文件", str(self.export_dir / "terrain_params.json"),
            "JSON文件 (*.json)"
        )
        
        if file_path:
            try:
                save_parameters(self.current_params, file_path)
                self.status_bar.showMessage(f"参数已保存: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存参数失败: {str(e)}")
                
    def _copy_parameters(self):
        """复制参数到剪贴板"""
        if self.current_params:
            import json
            import pyperclip
            
            try:
                params_dict = self.current_params.__dict__
                params_json = json.dumps(params_dict, indent=2)
                pyperclip.copy(params_json)
                self.status_bar.showMessage("参数已复制到剪贴板")
            except Exception as e:
                QMessageBox.warning(self, "警告", f"复制失败: {str(e)}")
                
    def _paste_parameters(self):
        """从剪贴板粘贴参数"""
        import json
        import pyperclip
        
        try:
            params_json = pyperclip.paste()
            params_dict = json.loads(params_json)
            
            from core import TerrainParams
            params = TerrainParams(**params_dict)
            self.control_panel.set_parameters(params)
            self.status_bar.showMessage("参数已从剪贴板粘贴")
        except Exception as e:
            QMessageBox.warning(self, "警告", f"粘贴失败: {str(e)}")
            
    def _reset_parameters(self):
        """重置参数"""
        self.control_panel.reset_to_defaults()
        self.status_bar.showMessage("参数已重置")
        
    # ====================== 导出功能 ======================
    
    def _export_heightmap(self):
        """导出高度图"""
        if self.current_heightmap is None:
            QMessageBox.warning(self, "警告", "没有可导出的地形")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出高度图", 
            str(self.export_dir / f"heightmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"),
            "PNG图像 (*.png);;TIFF图像 (*.tif);;RAW数据 (*.raw);;NumPy数组 (*.npy)"
        )
        
        if file_path:
            try:
                save_heightmap(self.current_heightmap, file_path)
                self.status_bar.showMessage(f"高度图已导出: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
                
    def _export_texture(self):
        """导出纹理"""
        if self.current_heightmap is None:
            QMessageBox.warning(self, "警告", "没有可导出的地形")
            return
            
        # 生成纹理
        from utils.image_utils import generate_texture
        texture = generate_texture(self.current_heightmap)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出纹理",
            str(self.export_dir / f"texture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"),
            "PNG图像 (*.png);;JPEG图像 (*.jpg)"
        )
        
        if file_path:
            try:
                texture.save(file_path)
                self.status_bar.showMessage(f"纹理已导出: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
                
    def _export_mesh(self):
        """导出3D模型"""
        if self.current_heightmap is None:
            QMessageBox.warning(self, "警告", "没有可导出的地形")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出3D模型",
            str(self.export_dir / f"mesh_{datetime.now().strftime('%Y%m%d_%H%M%S')}.obj"),
            "OBJ文件 (*.obj);;STL文件 (*.stl);;PLY文件 (*.ply)"
        )
        
        if file_path:
            try:
                save_mesh(self.current_heightmap, file_path)
                self.status_bar.showMessage(f"3D模型已导出: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
                
    def _export_all(self):
        """导出所有内容"""
        if self.current_heightmap is None:
            QMessageBox.warning(self, "警告", "没有可导出的地形")
            return
            
        # 创建导出目录
        export_name = f"terrain_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        export_path = self.export_dir / export_name
        export_path.mkdir(exist_ok=True)
        
        try:
            # 导出高度图
            heightmap_path = export_path / "heightmap.png"
            save_heightmap(self.current_heightmap, str(heightmap_path))
            
            # 导出纹理
            from utils.image_utils import generate_texture
            texture = generate_texture(self.current_heightmap)
            texture_path = export_path / "texture.png"
            texture.save(str(texture_path))
            
            # 导出3D模型
            mesh_path = export_path / "terrain.obj"
            save_mesh(self.current_heightmap, str(mesh_path))
            
            # 导出参数
            if self.current_params:
                params_path = export_path / "parameters.json"
                save_parameters(self.current_params, str(params_path))
            
            # 导出元数据
            if self.current_metadata:
                import json
                metadata_path = export_path / "metadata.json"
                with open(metadata_path, 'w') as f:
                    json.dump(self.current_metadata, f, indent=2)
            
            self.status_bar.showMessage(f"全部内容已导出到: {export_path.name}")
            
            # 询问是否打开文件夹
            reply = QMessageBox.question(
                self, "导出完成",
                f"内容已导出到: {export_path}\n\n是否打开文件夹？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                import subprocess
                subprocess.Popen(f'explorer "{export_path}"')
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
            
    # ====================== 生成线程回调 ======================
    
    def _on_generation_started(self):
        """生成开始时的处理"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("正在生成地形...")
        self.control_panel.set_enabled(False)  # 禁用控制面板
        
    def _on_generation_progress(self, progress, message):
        """生成进度更新时的处理"""
        self.progress_bar.setValue(progress)
        self.status_bar.showMessage(f"正在生成地形: {message}")
        
    def _on_generation_finished(self, heightmap, metadata):
        """生成完成时的处理"""
        self.current_heightmap = heightmap
        self.current_metadata = metadata
        self.current_params = self.control_panel.get_parameters()
        
        # 更新预览
        self.preview_canvas.set_heightmap(heightmap)
        
        # 更新统计信息
        self._update_statistics(heightmap)
        
        # 清理线程
        self.generator_thread = None
        
        # 恢复UI状态
        self.progress_bar.setVisible(False)
        self.control_panel.set_enabled(True)
        self.status_bar.showMessage("地形生成完成!")
        
        # 播放完成音效（可选）
        try:
            import winsound
            winsound.Beep(1000, 200)
        except:
            pass
            
    def _on_generation_error(self, error_message):
        """生成错误时的处理"""
        self.progress_bar.setVisible(False)
        self.control_panel.set_enabled(True)
        
        QMessageBox.critical(self, "生成错误", f"地形生成失败:\n\n{error_message}")
        self.status_bar.showMessage("生成失败")
        
        # 清理线程
        self.generator_thread = None
        
    # ====================== 视图功能 ======================
    
    def _update_preview(self):
        """更新预览"""
        # 如果有新的高度图数据，更新预览
        if self.current_heightmap is not None:
            self.preview_canvas.update()
            
    def _update_statistics(self, heightmap):
        """更新统计信息"""
        if heightmap is not None:
            stats = {
                'max_elev': f"{np.max(heightmap):.3f}",
                'min_elev': f"{np.min(heightmap):.3f}",
                'mean_elev': f"{np.mean(heightmap):.3f}",
                'std_elev': f"{np.std(heightmap):.3f}",
                'size': f"{heightmap.shape[1]}×{heightmap.shape[0]}"
            }
            
            # 更新控制面板的统计信息显示
            self.control_panel.update_statistics(stats)
            
    def _toggle_heightmap_view(self, checked):
        """切换高度图显示"""
        self.preview_canvas.show_heightmap = checked
        self.preview_canvas.update()
        
    def _toggle_slope_view(self, checked):
        """切换坡度图显示"""
        self.preview_canvas.show_slope = checked
        self.preview_canvas.update()
        
    def _toggle_river_view(self, checked):
        """切换河流网络显示"""
        self.preview_canvas.show_rivers = checked
        self.preview_canvas.update()
        
    def _toggle_grid(self, checked):
        """切换网格显示"""
        self.preview_canvas.show_grid = checked
        self.preview_canvas.update()
        
    def _toggle_axes(self, checked):
        """切换坐标轴显示"""
        self.preview_canvas.show_axes = checked
        self.preview_canvas.update()
        
    def _toggle_stats(self, checked):
        """切换统计信息显示"""
        self.preview_canvas.show_stats = checked
        self.preview_canvas.update()
        
    # ====================== 其他功能 ======================
    
    def _open_preferences(self):
        """打开偏好设置"""
        # TODO: 实现偏好设置对话框
        QMessageBox.information(self, "功能开发中", "偏好设置功能正在开发中")
        
    def _show_help(self):
        """显示帮助"""
        help_text = """
        <h2>地形生成器使用帮助</h2>
        
        <h3>基本操作：</h3>
        <ul>
        <li>调整左侧面板的参数</li>
        <li>点击"生成"按钮创建地形</li>
        <li>使用鼠标拖拽旋转3D视图</li>
        <li>使用滚轮缩放视图</li>
        </ul>
        
        <h3>参数说明：</h3>
        <ul>
        <li><b>构造抬升</b>：控制山脉的高度和陡峭度</li>
        <li><b>降水量</b>：影响河流侵蚀和植被</li>
        <li><b>地形年龄</b>：年轻地形更崎岖，古老地形更平缓</li>
        <li><b>分区数量</b>：创建不同特征的地形区域</li>
        </ul>
        
        <h3>快捷键：</h3>
        <ul>
        <li>Ctrl+G：生成新地形</li>
        <li>Ctrl+S：保存参数</li>
        <li>Ctrl+R：重置参数</li>
        <li>F5：重新生成</li>
        <li>ESC：退出程序</li>
        </ul>
        """
        
        QMessageBox.information(self, "使用帮助", help_text)
        
    def _show_about(self):
        """显示关于对话框"""
        about_text = """
        <h2>地形生成器 v1.0</h2>
        
        <p>基于地质过程的参数化地形生成工具</p>
        
        <p><b>核心功能：</b></p>
        <ul>
        <li>构造运动模拟</li>
        <li>侵蚀作用模拟</li>
        <li>气候分区系统</li>
        <li>多区域地形生成</li>
        </ul>
        
        <p><b>技术支持：</b></p>
        <ul>
        <li>Python + NumPy + SciPy</li>
        <li>PyQt5 图形界面</li>
        <li>OpenGL 3D渲染</li>
        </ul>
        
        <p>© 2024 地形生成器项目</p>
        <p>仅供学习和研究使用</p>
        """
        
        QMessageBox.about(self, "关于地形生成器", about_text)
        
    # ====================== 窗口事件 ======================
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 检查是否有正在进行的生成任务
        if self.generator_thread and self.generator_thread.isRunning():
            reply = QMessageBox.question(
                self, "正在生成",
                "有地形正在生成，是否强制退出？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
            else:
                self.generator_thread.stop()
                self.generator_thread.wait()
        
        # 清理资源
        self.preview_canvas.cleanup()
        
        # 保存配置
        self._save_config()
        
        event.accept()
        
    def _save_config(self):
        """保存配置"""
        try:
            import yaml
            config = {
                'window_geometry': {
                    'x': self.x(),
                    'y': self.y(),
                    'width': self.width(),
                    'height': self.height()
                },
                'export_dir': str(self.export_dir),
                'last_preset': self.control_panel.current_preset if hasattr(self.control_panel, 'current_preset') else None
            }
            
            config_path = Path("./config.yaml")
            with open(config_path, 'w') as f:
                yaml.dump(config, f)
                
        except Exception as e:
            print(f"保存配置失败: {e}")
            
    def keyPressEvent(self, event):
        """键盘事件处理"""
        # ESC键退出
        if event.key() == Qt.Key_Escape:
            self.close()
            
        # F5重新生成
        elif event.key() == Qt.Key_F5:
            self._regenerate_terrain()
            
        # Ctrl+G生成
        elif event.key() == Qt.Key_G and event.modifiers() == Qt.ControlModifier:
            self._generate_terrain()
            
        # Ctrl+S保存
        elif event.key() == Qt.Key_S and event.modifiers() == Qt.ControlModifier:
            self._save_parameters()
            
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    # 测试运行
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())