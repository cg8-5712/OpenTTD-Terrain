"""
预设管理模块 - 简化版本
"""
import json
from pathlib import Path
from typing import List

from core.terrain_params import TerrainParams


class PresetManager:
    """预设管理器"""
    
    def __init__(self, presets_dir="./presets"):
        self.presets_dir = Path(presets_dir)
        self.presets_dir.mkdir(exist_ok=True)
    
    def list_presets(self) -> List[str]:
        """列出所有预设"""
        presets = []
        for file_path in self.presets_dir.glob("*.json"):
            presets.append(file_path.stem)
        return sorted(presets)
    
    def load_preset(self, preset_name: str) -> TerrainParams:
        """加载预设"""
        preset_path = self.presets_dir / f"{preset_name}.json"
        
        if not preset_path.exists():
            # 返回默认参数
            return TerrainParams()
        
        with open(preset_path, 'r', encoding='utf-8') as f:
            params_dict = json.load(f)
        
        # 创建参数对象
        params = TerrainParams()
        for key, value in params_dict.items():
            if hasattr(params, key):
                setattr(params, key, value)
        
        return params
    
    def save_preset(self, preset_name: str, params: TerrainParams):
        """保存预设"""
        preset_path = self.presets_dir / f"{preset_name}.json"
        
        with open(preset_path, 'w', encoding='utf-8') as f:
            json.dump(params.__dict__, f, indent=2, default=str)
    
    def delete_preset(self, preset_name: str):
        """删除预设"""
        preset_path = self.presets_dir / f"{preset_name}.json"
        
        if preset_path.exists():
            preset_path.unlink()
    
    def create_default_presets(self):
        """创建默认预设"""
        default_presets = {
            "喜马拉雅山脉": {
                'size': (1024, 1024),
                'tectonic_pattern': 'convergent',
                'tectonic_uplift': 0.9,
                'rock_hardness': 0.7,
                'precipitation': 0.8,
                'temperature': 0.3,
                'terrain_age': 0.9,
                'num_regions': 3,
                'river_intensity': 0.9
            },
            "安第斯山脉": {
                'size': (1024, 1024),
                'tectonic_pattern': 'convergent',
                'tectonic_uplift': 0.8,
                'rock_hardness': 0.6,
                'precipitation': 0.6,
                'temperature': 0.4,
                'distance_to_coast': 0.2,
                'terrain_age': 0.8,
                'num_regions': 2
            },
            "青藏高原": {
                'size': (1024, 1024),
                'tectonic_pattern': 'convergent',
                'tectonic_uplift': 0.7,
                'rock_hardness': 0.8,
                'precipitation': 0.3,
                'temperature': 0.2,
                'distance_to_coast': 0.8,
                'terrain_age': 0.6,
                'wind_intensity': 0.6,
                'num_regions': 4
            }
        }
        
        for name, params_dict in default_presets.items():
            params = TerrainParams()
            for key, value in params_dict.items():
                if hasattr(params, key):
                    setattr(params, key, value)
            self.save_preset(name, params)
        
        return list(default_presets.keys())