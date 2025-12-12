"""
控制面板模块 - 参数输入和控制界面
"""
import json
from pathlib import Path

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

# 从core导入TerrainParams
try:
    from core.terrain_params import TerrainParams
except ImportError:
    # 如果导入失败，使用本地定义
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
        
        def to_dict(self):
            return self.__dict__.copy()


class ParameterSlider(QWidget):
    """带标签和数值显示的滑块控件"""
    
    value_changed = pyqtSignal(float)
    
    def __init__(self, label, min_val, max_val, default_val, step=0.01, decimals=2, parent=None):
        super().__init__(parent)
        
        self.label = label
        self.min_val = min_val
        self.max_val = max_val
        self.decimals = decimals
        
        # 布局
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标签
        self.name_label = QLabel(label)
        self.name_label.setMinimumWidth(100)
        layout.addWidget(self.name_label)
        
        # 滑块
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider, 1)
        
        # 数值显示
        self.value_spinbox = QDoubleSpinBox()
        self.value_spinbox.setRange(min_val, max_val)
        self.value_spinbox.setSingleStep(step)
        self.value_spinbox.setDecimals(decimals)
        self.value_spinbox.valueChanged.connect(self._on_spinbox_changed)
        self.value_spinbox.setMaximumWidth(80)
        layout.addWidget(self.value_spinbox)
        
        self.setLayout(layout)
        
        # 设置初始值
        self.set_value(default_val)
    
    def set_value(self, value):
        """设置值"""
        self.value_spinbox.setValue(value)
        slider_value = int((value - self.min_val) / (self.max_val - self.min_val) * 100)
        self.slider.setValue(slider_value)
    
    def get_value(self):
        """获取当前值"""
        return self.value_spinbox.value()
    
    def _on_slider_changed(self, value):
        """滑块变化时更新数值显示"""
        real_value = self.min_val + (value / 100.0) * (self.max_val - self.min_val)
        self.value_spinbox.setValue(round(real_value, self.decimals))
    
    def _on_spinbox_changed(self, value):
        """数值显示变化时更新滑块"""
        slider_value = int((value - self.min_val) / (self.max_val - self.min_val) * 100)
        self.slider.setValue(slider_value)
        self.value_changed.emit(value)


class ControlPanel(QWidget):
    """主控制面板"""
    
    # 信号定义
    parameters_changed = pyqtSignal(object)  # 参数变化信号
    generate_requested = pyqtSignal()        # 生成请求信号
    export_requested = pyqtSignal()          # 导出请求信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 当前预设名称
        self.current_preset = "自定义"
        
        # 标志：是否正在加载预设（避免触发参数变化）
        self._loading_preset = False
        
        # 初始化UI
        self._init_ui()
        
        # 设置默认参数
        self.default_params = TerrainParams()
        self.reset_to_defaults()
    
    def _init_ui(self):
        """初始化UI"""
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 添加滚动区域（如果参数太多）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # 1. 预设选择区域
        preset_group = self._create_preset_group()
        content_layout.addWidget(preset_group)
        
        # 2. 选项卡控件
        self.tab_widget = QTabWidget()
        
        # 基本参数选项卡
        basic_tab = self._create_basic_tab()
        self.tab_widget.addTab(basic_tab, "基本参数")
        
        # 构造参数选项卡
        tectonic_tab = self._create_tectonic_tab()
        self.tab_widget.addTab(tectonic_tab, "构造参数")
        
        # 气候参数选项卡
        climate_tab = self._create_climate_tab()
        self.tab_widget.addTab(climate_tab, "气候参数")
        
        # 侵蚀参数选项卡
        erosion_tab = self._create_erosion_tab()
        self.tab_widget.addTab(erosion_tab, "侵蚀参数")
        
        content_layout.addWidget(self.tab_widget)
        
        # 3. 统计信息区域
        stats_group = self._create_statistics_group()
        content_layout.addWidget(stats_group)
        
        # 4. 按钮区域
        button_group = self._create_button_group()
        content_layout.addWidget(button_group)
        
        content_layout.addStretch()
        
        # 设置滚动区域内容
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)
        
        # 设置样式
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel {
                font-size: 11px;
            }
            QPushButton {
                font-weight: bold;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton#generate_button {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
            }
            QPushButton#export_button {
                background-color: #2196F3;
                color: white;
            }
        """)
    
    def _create_preset_group(self):
        """创建预设选择组"""
        group = QGroupBox("预设")
        layout = QHBoxLayout()
        
        # 预设选择下拉框
        self.preset_combo = QComboBox()
        self._load_presets_to_combo()
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        
        # 刷新预设按钮
        refresh_btn = QPushButton("🔄")
        refresh_btn.setMaximumWidth(40)
        refresh_btn.setToolTip("刷新预设列表")
        refresh_btn.clicked.connect(self._refresh_presets)
        
        # 保存预设按钮
        save_preset_btn = QPushButton("保存")
        save_preset_btn.setToolTip("保存当前参数为新预设")
        save_preset_btn.clicked.connect(self._save_as_preset)
        
        # 删除预设按钮
        delete_preset_btn = QPushButton("删除")
        delete_preset_btn.setToolTip("删除当前选中的预设")
        delete_preset_btn.clicked.connect(self._delete_preset)
        
        layout.addWidget(QLabel("选择预设:"))
        layout.addWidget(self.preset_combo, 1)
        layout.addWidget(refresh_btn)
        layout.addWidget(save_preset_btn)
        layout.addWidget(delete_preset_btn)
        
        group.setLayout(layout)
        return group
    
    def _load_presets_to_combo(self):
        """加载预设到下拉框"""
        # 清空现有项
        self.preset_combo.clear()
        
        # 添加固定选项
        self.preset_combo.addItem("自定义")
        self.preset_combo.addItem("默认")
        
        # 从文件夹读取其他预设
        presets_dir = Path("./presets")
        if presets_dir.exists():
            preset_files = sorted(presets_dir.glob("*.json"))
            for preset_file in preset_files:
                preset_name = preset_file.stem
                # 跳过default.json,因为已经作为"默认"添加
                if preset_name.lower() != "default":
                    self.preset_combo.addItem(preset_name)
        
        print(f"加载了 {self.preset_combo.count()} 个预设")
    
    def _refresh_presets(self):
        """刷新预设列表"""
        current = self.preset_combo.currentText()
        self._load_presets_to_combo()
        
        # 尝试恢复之前的选择
        index = self.preset_combo.findText(current)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
        else:
            self.preset_combo.setCurrentIndex(0)  # 默认选择"自定义"
    
    def _create_basic_tab(self):
        """创建基本参数选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 尺寸设置组
        size_group = QGroupBox("地形尺寸")
        size_layout = QGridLayout()
        
        size_layout.addWidget(QLabel("宽度:"), 0, 0)
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(256, 4096)
        self.width_spinbox.setValue(1024)
        self.width_spinbox.setSingleStep(64)
        self.width_spinbox.valueChanged.connect(self._on_parameter_changed)
        size_layout.addWidget(self.width_spinbox, 0, 1)
        
        size_layout.addWidget(QLabel("高度:"), 0, 2)
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(256, 4096)
        self.height_spinbox.setValue(1024)
        self.height_spinbox.setSingleStep(64)
        self.height_spinbox.valueChanged.connect(self._on_parameter_changed)
        size_layout.addWidget(self.height_spinbox, 0, 3)
        
        size_layout.addWidget(QLabel("种子:"), 1, 0)
        self.seed_spinbox = QSpinBox()
        self.seed_spinbox.setRange(0, 999999)
        self.seed_spinbox.setSpecialValueText("随机")
        self.seed_spinbox.valueChanged.connect(self._on_parameter_changed)
        size_layout.addWidget(self.seed_spinbox, 1, 1, 1, 3)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        # 分区设置组
        region_group = QGroupBox("分区设置")
        region_layout = QGridLayout()
        
        region_layout.addWidget(QLabel("分区数量:"), 0, 0)
        self.num_regions_spinbox = QSpinBox()
        self.num_regions_spinbox.setRange(1, 8)
        self.num_regions_spinbox.setValue(4)
        self.num_regions_spinbox.valueChanged.connect(self._on_parameter_changed)
        region_layout.addWidget(self.num_regions_spinbox, 0, 1)
        
        region_layout.addWidget(QLabel("区域对比度:"), 0, 2)
        self.region_contrast_slider = ParameterSlider("", 0.0, 1.0, 0.6, 0.05)
        self.region_contrast_slider.value_changed.connect(self._on_parameter_changed)
        region_layout.addWidget(self.region_contrast_slider, 0, 3)
        
        region_group.setLayout(region_layout)
        layout.addWidget(region_group)
        
        widget.setLayout(layout)
        return widget
    
    def _create_tectonic_tab(self):
        """创建构造参数选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 构造模式选择
        mode_group = QGroupBox("构造模式")
        mode_layout = QHBoxLayout()
        
        self.tectonic_mode_combo = QComboBox()
        self.tectonic_mode_combo.addItems([
            "碰撞造山 (convergent)",
            "张裂伸展 (divergent)", 
            "走滑剪切 (transform)",
            "稳定克拉通 (stable)"
        ])
        self.tectonic_mode_combo.currentIndexChanged.connect(self._on_parameter_changed)
        mode_layout.addWidget(self.tectonic_mode_combo)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 构造参数滑块
        params_group = QGroupBox("构造参数")
        params_layout = QVBoxLayout()
        
        # 构造抬升强度
        self.tectonic_uplift_slider = ParameterSlider(
            "构造抬升强度", 0.0, 1.0, 0.7, 0.05
        )
        self.tectonic_uplift_slider.value_changed.connect(self._on_parameter_changed)
        params_layout.addWidget(self.tectonic_uplift_slider)
        
        # 岩石硬度
        self.rock_hardness_slider = ParameterSlider(
            "岩石硬度", 0.0, 1.0, 0.5, 0.05
        )
        self.rock_hardness_slider.value_changed.connect(self._on_parameter_changed)
        params_layout.addWidget(self.rock_hardness_slider)
        
        # 地形年龄
        self.terrain_age_slider = ParameterSlider(
            "地形年龄", 0.0, 1.0, 0.7, 0.05
        )
        self.terrain_age_slider.value_changed.connect(self._on_parameter_changed)
        params_layout.addWidget(self.terrain_age_slider)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        widget.setLayout(layout)
        return widget
    
    def _create_climate_tab(self):
        """创建气候参数选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 气候参数组
        climate_group = QGroupBox("气候参数")
        climate_layout = QVBoxLayout()
        
        # 降水量
        self.precipitation_slider = ParameterSlider(
            "降水量", 0.0, 1.0, 0.6, 0.05
        )
        self.precipitation_slider.value_changed.connect(self._on_parameter_changed)
        climate_layout.addWidget(self.precipitation_slider)
        
        # 温度
        self.temperature_slider = ParameterSlider(
            "温度", 0.0, 1.0, 0.4, 0.05
        )
        self.temperature_slider.value_changed.connect(self._on_parameter_changed)
        climate_layout.addWidget(self.temperature_slider)
        
        # 风力强度
        self.wind_intensity_slider = ParameterSlider(
            "风力强度", 0.0, 1.0, 0.3, 0.05
        )
        self.wind_intensity_slider.value_changed.connect(self._on_parameter_changed)
        climate_layout.addWidget(self.wind_intensity_slider)
        
        # 距海岸距离
        self.distance_to_coast_slider = ParameterSlider(
            "距海岸距离", 0.0, 1.0, 0.5, 0.05
        )
        self.distance_to_coast_slider.value_changed.connect(self._on_parameter_changed)
        climate_layout.addWidget(self.distance_to_coast_slider)
        
        climate_group.setLayout(climate_layout)
        layout.addWidget(climate_group)
        
        widget.setLayout(layout)
        return widget
    
    def _create_erosion_tab(self):
        """创建侵蚀参数选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 侵蚀参数组
        erosion_group = QGroupBox("侵蚀参数")
        erosion_layout = QVBoxLayout()
        
        # 侵蚀迭代次数
        erosion_layout.addWidget(QLabel("侵蚀迭代次数:"))
        self.erosion_iterations_spinbox = QSpinBox()
        self.erosion_iterations_spinbox.setRange(1, 50)
        self.erosion_iterations_spinbox.setValue(10)
        self.erosion_iterations_spinbox.valueChanged.connect(self._on_parameter_changed)
        erosion_layout.addWidget(self.erosion_iterations_spinbox)
        
        # 河流侵蚀强度
        self.river_intensity_slider = ParameterSlider(
            "河流侵蚀强度", 0.0, 1.0, 0.8, 0.05
        )
        self.river_intensity_slider.value_changed.connect(self._on_parameter_changed)
        erosion_layout.addWidget(self.river_intensity_slider)
        
        # 冰川侵蚀强度
        self.glacial_intensity_slider = ParameterSlider(
            "冰川侵蚀强度", 0.0, 1.0, 0.3, 0.05
        )
        self.glacial_intensity_slider.value_changed.connect(self._on_parameter_changed)
        erosion_layout.addWidget(self.glacial_intensity_slider)
        
        erosion_group.setLayout(erosion_layout)
        layout.addWidget(erosion_group)
        
        widget.setLayout(layout)
        return widget
    
    def _create_statistics_group(self):
        """创建统计信息组"""
        group = QGroupBox("统计信息")
        layout = QGridLayout()
        
        # 统计标签
        self.stats_labels = {}
        stats_names = [
            ("最大高程:", "max_elev"),
            ("最小高程:", "min_elev"), 
            ("平均高程:", "mean_elev"),
            ("标准差:", "std_elev"),
            ("尺寸:", "size")
        ]
        
        for i, (label_text, key) in enumerate(stats_names):
            row = i // 2
            col = (i % 2) * 2
            
            layout.addWidget(QLabel(label_text), row, col)
            value_label = QLabel("--")
            value_label.setAlignment(Qt.AlignRight)
            self.stats_labels[key] = value_label
            layout.addWidget(value_label, row, col + 1)
        
        group.setLayout(layout)
        return group
    
    def _create_button_group(self):
        """创建按钮组"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 0)
        
        # 生成按钮
        self.generate_button = QPushButton("生成地形")
        self.generate_button.setObjectName("generate_button")
        self.generate_button.clicked.connect(self.generate_requested.emit)
        layout.addWidget(self.generate_button)
        
        # 导出按钮
        self.export_button = QPushButton("导出")
        self.export_button.setObjectName("export_button")
        self.export_button.clicked.connect(self.export_requested.emit)
        layout.addWidget(self.export_button)
        
        # 重置按钮
        reset_button = QPushButton("重置")
        reset_button.clicked.connect(self.reset_to_defaults)
        layout.addWidget(reset_button)
        
        widget.setLayout(layout)
        return widget
    
    # ====================== 事件处理 ======================
    
    def _on_preset_changed(self, preset_name):
        """预设变化处理"""
        if preset_name == "自定义":
            self.current_preset = preset_name
            return
        
        # 加载预设
        try:
            presets_dir = Path("./presets")
            presets_dir.mkdir(exist_ok=True)
            
            # 处理"默认"预设
            if preset_name == "默认":
                preset_path = presets_dir / "default.json"
                # 如果默认预设不存在,创建它
                if not preset_path.exists():
                    print("创建默认预设文件...")
                    self._create_default_preset()
            else:
                preset_path = presets_dir / f"{preset_name}.json"
            
            if preset_path.exists():
                print(f"加载预设: {preset_name}")
                with open(preset_path, 'r', encoding='utf-8') as f:
                    params_dict = json.load(f)
                
                # 创建参数对象并设置UI
                params = TerrainParams()
                for key, value in params_dict.items():
                    if hasattr(params, key):
                        setattr(params, key, value)
                
                # 设置标志,避免在set_parameters时切回"自定义"
                self._loading_preset = True
                self.current_preset = preset_name
                self.set_parameters(params)
                self._loading_preset = False
                
                # 触发参数变化信号
                self.parameters_changed.emit(params)
                print(f"预设 '{preset_name}' 加载完成")
            else:
                print(f"预设文件不存在: {preset_path}")
                QMessageBox.warning(self, "预设不存在", f"预设文件 '{preset_name}' 不存在！")
                self.preset_combo.setCurrentText("自定义")
                
        except Exception as e:
            print(f"加载预设失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "加载失败", f"加载预设失败: {str(e)}")
    
    def _create_default_preset(self):
        """创建默认预设文件"""
        presets_dir = Path("./presets")
        presets_dir.mkdir(exist_ok=True)
        
        # 使用当前默认参数
        default_preset_path = presets_dir / "default.json"
        
        try:
            with open(default_preset_path, 'w', encoding='utf-8') as f:
                json.dump(self.default_params.to_dict(), f, indent=2, default=str)
            print(f"默认预设已创建: {default_preset_path}")
        except Exception as e:
            print(f"创建默认预设失败: {e}")
    
    def _on_parameter_changed(self):
        """参数变化处理"""
        params = self.get_parameters()
        self.parameters_changed.emit(params)
        
        # 如果不是正在加载预设，且当前不是自定义，则切换到自定义
        if not self._loading_preset and self.current_preset != "自定义":
            self.preset_combo.blockSignals(True)  # 阻止信号触发
            self.preset_combo.setCurrentText("自定义")
            self.preset_combo.blockSignals(False)
            self.current_preset = "自定义"
    
    def _save_as_preset(self):
        """保存为预设"""
        # 获取预设名称
        name, ok = QInputDialog.getText(
            self, "保存预设", "请输入预设名称:"
        )
        
        if ok and name:
            # 检查是否尝试覆盖固定预设
            if name in ["自定义", "默认", "default", "Default"]:
                QMessageBox.warning(self, "无效名称", "不能使用保留名称！")
                return
            # 确保预设目录存在
            presets_dir = Path("./presets")
            presets_dir.mkdir(exist_ok=True)
            
            # 保存参数
            params = self.get_parameters()
            preset_path = presets_dir / f"{name}.json"
            
            try:
                with open(preset_path, 'w', encoding='utf-8') as f:
                    json.dump(params.to_dict(), f, indent=2, default=str)
                
                print(f"预设已保存: {name}")
                QMessageBox.information(self, "保存成功", f"预设 '{name}' 已保存！")
                
                # 刷新预设列表
                self._refresh_presets()
                
                # 切换到新保存的预设
                index = self.preset_combo.findText(name)
                if index >= 0:
                    self.preset_combo.setCurrentIndex(index)
                
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存预设失败: {str(e)}")
    
    def _delete_preset(self):
        """删除预设"""
        current_preset = self.preset_combo.currentText()
        
        # 检查是否是保护的预设
        if current_preset in ["自定义", "默认"]:
            QMessageBox.information(self, "提示", f"无法删除 '{current_preset}' 预设")
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除预设 '{current_preset}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                preset_path = Path("./presets") / f"{current_preset}.json"
                if preset_path.exists():
                    preset_path.unlink()
                
                print(f"预设已删除: {current_preset}")
                QMessageBox.information(self, "删除成功", f"预设 '{current_preset}' 已删除！")
                
                # 刷新预设列表
                self._refresh_presets()
                
                # 切换到自定义
                self.preset_combo.setCurrentText("自定义")
                
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除预设失败: {str(e)}")
    
    # ====================== 公共方法 ======================
    
    def get_parameters(self):
        """获取当前参数"""
        params = TerrainParams()
        
        # 基本参数
        params.size = (self.width_spinbox.value(), self.height_spinbox.value())
        seed_value = self.seed_spinbox.value()
        params.seed = seed_value if seed_value > 0 else None
        
        # 分区参数
        params.num_regions = self.num_regions_spinbox.value()
        params.region_contrast = self.region_contrast_slider.get_value()
        
        # 构造参数
        mode_text = self.tectonic_mode_combo.currentText()
        if "碰撞" in mode_text:
            params.tectonic_pattern = "convergent"
        elif "张裂" in mode_text:
            params.tectonic_pattern = "divergent"
        elif "走滑" in mode_text:
            params.tectonic_pattern = "transform"
        else:
            params.tectonic_pattern = "stable"
        
        params.tectonic_uplift = self.tectonic_uplift_slider.get_value()
        params.rock_hardness = self.rock_hardness_slider.get_value()
        params.terrain_age = self.terrain_age_slider.get_value()
        
        # 气候参数
        params.precipitation = self.precipitation_slider.get_value()
        params.temperature = self.temperature_slider.get_value()
        params.wind_intensity = self.wind_intensity_slider.get_value()
        params.distance_to_coast = self.distance_to_coast_slider.get_value()
        
        # 侵蚀参数
        params.erosion_iterations = self.erosion_iterations_spinbox.value()
        params.river_intensity = self.river_intensity_slider.get_value()
        params.glacial_intensity = self.glacial_intensity_slider.get_value()
        
        return params
        
    def set_parameters(self, params):
        """设置参数"""
        # 基本参数
        self.width_spinbox.setValue(params.size[0])
        self.height_spinbox.setValue(params.size[1])
        self.seed_spinbox.setValue(params.seed if params.seed else 0)
        
        # 分区参数
        self.num_regions_spinbox.setValue(params.num_regions)
        self.region_contrast_slider.set_value(params.region_contrast)
        
        # 构造参数
        if params.tectonic_pattern == "convergent":
            self.tectonic_mode_combo.setCurrentText("碰撞造山 (convergent)")
        elif params.tectonic_pattern == "divergent":
            self.tectonic_mode_combo.setCurrentText("张裂伸展 (divergent)")
        elif params.tectonic_pattern == "transform":
            self.tectonic_mode_combo.setCurrentText("走滑剪切 (transform)")
        else:
            self.tectonic_mode_combo.setCurrentText("稳定克拉通 (stable)")
        
        self.tectonic_uplift_slider.set_value(params.tectonic_uplift)
        self.rock_hardness_slider.set_value(params.rock_hardness)
        self.terrain_age_slider.set_value(params.terrain_age)
        
        # 气候参数
        self.precipitation_slider.set_value(params.precipitation)
        self.temperature_slider.set_value(params.temperature)
        self.wind_intensity_slider.set_value(params.wind_intensity)
        self.distance_to_coast_slider.set_value(params.distance_to_coast)
        
        # 侵蚀参数
        self.erosion_iterations_spinbox.setValue(params.erosion_iterations)
        self.river_intensity_slider.set_value(params.river_intensity)
        self.glacial_intensity_slider.set_value(params.glacial_intensity)
        
        # 只在不是加载预设时触发参数变化信号
        if not self._loading_preset:
            self._on_parameter_changed()
        # 触发参数变化信号
        self._on_parameter_changed()
    
    def reset_to_defaults(self):
        """重置为默认参数"""
        self.set_parameters(self.default_params)
    
    def update_statistics(self, stats):
        """更新统计信息"""
        for key, value in stats.items():
            if key in self.stats_labels:
                self.stats_labels[key].setText(str(value))
    
    def set_enabled(self, enabled):
        """启用/禁用所有控件"""
        self.setEnabled(enabled)


# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    panel = ControlPanel()
    panel.show()
    sys.exit(app.exec_())