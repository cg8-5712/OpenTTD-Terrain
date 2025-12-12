"""
地形参数类
"""
from dataclasses import dataclass, asdict
from typing import Tuple, Optional, Any
import json


@dataclass
class TerrainParams:
    """地形生成参数类"""
    
    # 基本参数
    size: Tuple[int, int] = (1024, 1024)
    seed: Optional[int] = None
    
    # 构造参数
    tectonic_uplift: float = 0.7          # 构造抬升强度 [0-1]
    tectonic_pattern: str = "convergent"  # convergent/divergent/transform/stable
    rock_hardness: float = 0.5            # 岩石硬度 [0-1]
    terrain_age: float = 0.7              # 地形年龄 [0-1], 0=古老, 1=年轻
    
    # 气候参数
    precipitation: float = 0.6            # 降水量 [0-1]
    temperature: float = 0.4              # 温度 [0-1], 0=寒冷, 1=炎热
    wind_intensity: float = 0.3           # 风力强度 [0-1]
    distance_to_coast: float = 0.5        # 距海岸距离 [0-1], 0=沿海, 1=内陆
    
    # 分区参数
    num_regions: int = 4                  # 分区数量
    region_contrast: float = 0.6          # 区域对比度 [0-1]
    
    # 侵蚀参数
    erosion_iterations: int = 10          # 侵蚀迭代次数
    river_intensity: float = 0.8          # 河流侵蚀强度
    glacial_intensity: float = 0.3        # 冰川侵蚀强度
    
    def __post_init__(self):
        """参数验证和初始化"""
        # 确保size是元组
        if isinstance(self.size, list):
            self.size = tuple(self.size)
        
        # 如果没有设置seed，使用None（将在生成器中随机生成）
        if self.seed == 0:
            self.seed = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=2, default=str)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TerrainParams':
        """从字典创建"""
        # 处理size参数
        if 'size' in data and isinstance(data['size'], list):
            data['size'] = tuple(data['size'])
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TerrainParams':
        """从JSON字符串创建"""
        data = json.loads(json_str)
        return cls.from_dict(data)