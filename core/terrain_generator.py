"""
地形生成器核心类
简化版本，专注于基本功能
"""
import numpy as np
from typing import Tuple, Optional
import random
from scipy.ndimage import zoom, gaussian_filter

from .terrain_params import TerrainParams


class TerrainGenerator:
    """地形生成器核心类"""
    
    def __init__(self):
        """初始化生成器"""
        self.rng = None
    
    def _init_random(self, seed: Optional[int] = None):
        """初始化随机数生成器"""
        if seed is None:
            seed = random.randint(0, 2**31 - 1)
        
        self.rng = np.random.RandomState(seed)
        return seed
    
    def _perlin_noise_2d(self, shape: Tuple[int, int], scale: float, octaves: int = 1, persistence: float = 0.5):
        """生成Perlin噪声（优化版）"""
        height, width = shape
        
        # 如果RNG未初始化，初始化一个
        if self.rng is None:
            self._init_random()
        
        # 生成基础噪声
        noise = np.zeros(shape)
        
        for octave in range(octaves):
            freq = 2 ** octave
            amplitude = persistence ** octave
            
            # 使用更高效的方法：直接使用随机噪声并进行平滑
            # 计算该八度的网格大小
            octave_scale = scale / freq
            grid_size_x = max(4, int(width * octave_scale))
            grid_size_y = max(4, int(height * octave_scale))
            
            # 生成小尺寸随机噪声
            small_noise = self.rng.randn(grid_size_y, grid_size_x)
            
            # 使用双三次插值放大到目标大小
            from scipy.ndimage import zoom
            zoom_factor = (height / grid_size_y, width / grid_size_x)
            octave_noise = zoom(small_noise, zoom_factor, order=3)
            
            # 确保大小匹配
            octave_noise = octave_noise[:height, :width]
            
            # 归一化该八度
            if np.max(octave_noise) > np.min(octave_noise):
                octave_noise = (octave_noise - np.min(octave_noise)) / (np.max(octave_noise) - np.min(octave_noise))
                octave_noise = octave_noise * 2 - 1  # 映射到[-1, 1]
            
            # 添加到总噪声
            noise += octave_noise * amplitude
        
        # 归一化到[0, 1]
        if np.max(noise) > np.min(noise):
            noise = (noise - np.min(noise)) / (np.max(noise) - np.min(noise))
        
        return noise
    
    def _simplex_noise_2d(self, shape: Tuple[int, int], scale: float):
        """生成Simplex噪声（优化版）- 使用分形噪声代替"""
        # 使用多八度Perlin噪声作为Simplex的替代
        return self._perlin_noise_2d(shape, scale=scale, octaves=4, persistence=0.5)
    
    def generate_tectonic_base(self, params: TerrainParams) -> np.ndarray:
        """生成构造基底"""
        print(f"生成构造基底，尺寸: {params.size}")
        
        # 初始化随机数生成器
        actual_seed = self._init_random(params.seed)
        print(f"使用种子: {actual_seed}")
        
        height, width = params.size[1], params.size[0]
        
        # 根据构造模式生成不同的基底
        if params.tectonic_pattern == "convergent":
            # 碰撞造山：生成线性山脉
            print("生成碰撞造山模式...")
            base = self._generate_mountain_belt((height, width), params)
            
        elif params.tectonic_pattern == "divergent":
            # 张裂：生成裂谷
            print("生成张裂模式...")
            base = self._generate_rift_valley((height, width), params)
            
        elif params.tectonic_pattern == "transform":
            # 走滑：生成复杂地形
            print("生成走滑模式...")
            base = self._generate_transform_boundary((height, width), params)
            
        else:  # "stable"
            # 稳定：生成平缓地形
            print("生成稳定克拉通模式...")
            base = self._generate_stable_craton((height, width), params)
        
        # 先应用岩性差异（硬岩区更高更陡）
        hardness_map = self._generate_hardness_map((height, width), params.rock_hardness)
        base = base * (0.7 + hardness_map * 0.3)
        
        # 应用抬升强度 - 非线性增强
        base = base * (params.tectonic_uplift ** 0.8)
        
        print(f"构造基底范围: {np.min(base):.3f} - {np.max(base):.3f}")
        
        return base
    
    def _generate_mountain_belt(self, shape: Tuple[int, int], params: TerrainParams) -> np.ndarray:
        """生成山脉带"""
        height, width = shape
        
        # 创建山脉脊线（多条平行山脉）
        num_mountains = max(3, 3 + int(params.tectonic_uplift * 6))
        mountain_map = np.zeros(shape)
        
        print(f"  生成 {num_mountains} 条平行山脉（横向）...")
        
        # 山脉宽度 - 根据抬升强度和总数量调整
        base_width = height / (num_mountains * 3)  # 基于高度（Y轴）而不是宽度
        mountain_width = int(base_width * (0.8 + params.tectonic_uplift * 0.4))
        
        print(f"  山脉宽度: {mountain_width} 像素")
        
        for i in range(num_mountains):
            # 山脉位置（在**高度**方向上的位置 - Y轴）
            # 注意：喜马拉雅山脉是横向的，所以应该沿Y轴分布
            if num_mountains == 1:
                pos_y = height // 2
            else:
                pos_y = int(height * (i + 1) / (num_mountains + 1))
            
            print(f"  山脉 {i+1}: Y位置 = {pos_y}")
            
            # 生成山脉剖面（在Y方向上）
            y_coords = np.arange(height)
            distance_y = np.abs(y_coords - pos_y)
            
            # 高斯剖面 - 主山脉（垂直方向的宽度）
            vertical_profile = np.zeros(height)
            mask = distance_y < mountain_width * 4
            vertical_profile[mask] = np.exp(-(distance_y[mask] ** 2) / (2 * (mountain_width ** 2)))
            
            # 添加次级山峰（平行于主山脉）
            secondary_width = mountain_width * 1.2
            secondary_offset = int(mountain_width * 1.5)
            
            # 上侧次级山脉
            distance_top = np.abs(y_coords - (pos_y - secondary_offset))
            mask_top = distance_top < secondary_width * 3
            vertical_profile[mask_top] += 0.5 * np.exp(-(distance_top[mask_top] ** 2) / (2 * (secondary_width ** 2)))
            
            # 下侧次级山脉
            distance_bottom = np.abs(y_coords - (pos_y + secondary_offset))
            mask_bottom = distance_bottom < secondary_width * 3
            vertical_profile[mask_bottom] += 0.5 * np.exp(-(distance_bottom[mask_bottom] ** 2) / (2 * (secondary_width ** 2)))
            
            # 沿山脉长度方向的变化（X轴方向 - 横向延伸）
            x_coords = np.arange(width)
            # 使用多个频率创建更自然的山峰和山谷
            longitudinal_var = (
                np.sin(x_coords / width * np.pi * 3) * 0.15 +
                np.sin(x_coords / width * np.pi * 7 + i) * 0.10 +
                0.75
            )
            
            # 创建2D山脉：
            # vertical_profile[y] 表示在Y位置的高度
            # longitudinal_var[x] 表示沿X方向的变化
            # 我们需要 mountain[y,x] = vertical_profile[y] * longitudinal_var[x]
            # 这正是 outer 的定义！但要确保输出形状是 (height, width)
            mountain_profile_2d = vertical_profile[:, np.newaxis] * longitudinal_var[np.newaxis, :]
            mountain_map += mountain_profile_2d
        
        # 添加多尺度噪声细节
        # 大尺度噪声（山体起伏）
        large_noise = self._perlin_noise_2d(shape, scale=0.3, octaves=3, persistence=0.5)
        # 中尺度噪声（山峰细节）
        medium_noise = self._perlin_noise_2d(shape, scale=0.1, octaves=4, persistence=0.5)
        # 小尺度噪声（表面纹理）
        small_noise = self._perlin_noise_2d(shape, scale=0.03, octaves=2, persistence=0.5)
        
        # 组合：主体结构为主，细节为辅
        mountain_map = mountain_map * 0.7 + large_noise * 0.15 + medium_noise * 0.1 + small_noise * 0.05
        
        # 增强对比度 - 使山峰更突出
        mountain_map = mountain_map ** 1.8
        
        # 归一化
        mountain_map = (mountain_map - np.min(mountain_map)) / (np.max(mountain_map) - np.min(mountain_map) + 1e-8)
        
        return mountain_map
    
    def _generate_rift_valley(self, shape: Tuple[int, int], params: TerrainParams) -> np.ndarray:
        """生成裂谷"""
        height, width = shape
        
        # 创建裂谷
        rift_map = np.zeros(shape)
        
        # 裂谷中心线
        rift_center = width // 2
        rift_width = int(width * 0.1)
        
        for x in range(width):
            distance_to_center = abs(x - rift_center)
            
            if distance_to_center < rift_width:
                # 裂谷内部（较低）
                rift_val = -np.exp(-(distance_to_center ** 2) / (rift_width ** 2))
            else:
                # 裂谷两侧的隆起
                rift_val = np.exp(-((distance_to_center - rift_width) ** 2) / ((rift_width * 2) ** 2)) * 0.5
            
            # 应用到整个高度方向
            rift_map[:, x] = rift_val
        
        # 添加火山特征（如果抬升强烈）
        if params.tectonic_uplift > 0.6:
            volcanic_noise = self._perlin_noise_2d(shape, scale=0.05, octaves=2)
            rift_map += volcanic_noise * 0.3
        
        # 归一化
        rift_map = (rift_map - np.min(rift_map)) / (np.max(rift_map) - np.min(rift_map) + 1e-8)
        
        return rift_map
    
    def _generate_transform_boundary(self, shape: Tuple[int, int], params: TerrainParams) -> np.ndarray:
        """生成走滑边界地形"""
        height, width = shape
        
        # 创建走滑带
        transform_map = np.zeros(shape)
        
        # 多条平行的走滑带
        num_zones = 2 + int(params.tectonic_uplift * 3)
        
        for zone in range(num_zones):
            # 走滑带位置
            zone_center = int(height * (zone + 1) / (num_zones + 1))
            zone_width = int(height * 0.05)
            
            for y in range(height):
                distance = abs(y - zone_center)
                if distance < zone_width * 3:
                    # 走滑带特征
                    zone_val = np.exp(-(distance ** 2) / (2 * (zone_width ** 2)))
                    
                    # 横向变化
                    for x in range(width):
                        # 添加挤压和拉张区域
                        if zone % 2 == 0:
                            # 挤压区（高地）
                            lateral_var = np.sin(x / width * np.pi * 8) * 0.5 + 0.5
                        else:
                            # 拉张区（低地）
                            lateral_var = np.cos(x / width * np.pi * 8) * 0.5 + 0.5
                        
                        transform_map[y, x] += zone_val * lateral_var
        
        # 添加细节
        detail_noise = self._perlin_noise_2d(shape, scale=0.08, octaves=4)
        transform_map = transform_map * 0.6 + detail_noise * 0.4
        
        # 归一化
        transform_map = (transform_map - np.min(transform_map)) / (np.max(transform_map) - np.min(transform_map) + 1e-8)
        
        return transform_map
    
    def _generate_stable_craton(self, shape: Tuple[int, int], params: TerrainParams) -> np.ndarray:
        """生成稳定克拉通地形"""
        # 使用多尺度噪声创建平缓地形
        base_noise = self._perlin_noise_2d(shape, scale=0.3, octaves=1)
        detail_noise = self._perlin_noise_2d(shape, scale=0.05, octaves=3)
        
        # 混合
        craton_map = base_noise * 0.8 + detail_noise * 0.2
        
        # 根据地形年龄平滑
        if params.terrain_age < 0.5:
            # 古老地形更平滑
            from scipy.ndimage import gaussian_filter
            sigma = 2 + (1 - params.terrain_age) * 5
            craton_map = gaussian_filter(craton_map, sigma=sigma)
        
        return craton_map
    
    def _generate_hardness_map(self, shape: Tuple[int, int], overall_hardness: float) -> np.ndarray:
        """生成岩性硬度图"""
        # 使用噪声生成硬度分布
        hardness_noise = self._perlin_noise_2d(shape, scale=0.2, octaves=2)
        
        # 调整整体硬度水平
        hardness_map = hardness_noise * 0.5 + overall_hardness * 0.5
        
        return hardness_map
    
    def generate_regions(self, params: TerrainParams) -> np.ndarray:
        """生成分区图"""
        print(f"生成分区，数量: {params.num_regions}")
        
        height, width = params.size[1], params.size[0]
        
        if params.num_regions == 1:
            # 单一区域
            return np.zeros((height, width), dtype=int)
        
        # 生成分区中心点
        centers = []
        for i in range(params.num_regions):
            # 确保中心点分散
            attempts = 0
            while attempts < 100:
                cx = self.rng.randint(width // 4, 3 * width // 4)
                cy = self.rng.randint(height // 4, 3 * height // 4)
                
                # 检查是否与其他中心点太近
                too_close = False
                for (ox, oy) in centers:
                    distance = np.sqrt((cx - ox) ** 2 + (cy - oy) ** 2)
                    min_distance = min(width, height) / (params.num_regions * 2)
                    if distance < min_distance:
                        too_close = True
                        break
                
                if not too_close:
                    centers.append((cx, cy))
                    break
                
                attempts += 1
            
            if attempts >= 100:
                # 如果无法找到合适位置，均匀分布
                row = i // 2
                col = i % 2
                cx = int(width * (col + 1) / 3)
                cy = int(height * (row + 1) / 3)
                centers.append((cx, cy))
        
        # 创建沃罗诺伊图（Voronoi diagram）
        region_map = np.zeros((height, width), dtype=int)
        region_distance = np.full((height, width), np.inf)
        
        for region_id, (cx, cy) in enumerate(centers):
            # 计算每个像素到该中心的距离
            y_indices, x_indices = np.ogrid[:height, :width]
            distances = np.sqrt((x_indices - cx) ** 2 + (y_indices - cy) ** 2)
            
            # 添加随机扰动以创建自然边界
            if params.region_contrast > 0.3:
                perturbation = self._perlin_noise_2d((height, width), scale=0.1) * params.region_contrast * 50
                distances += perturbation
            
            # 更新最近区域
            mask = distances < region_distance
            region_map[mask] = region_id
            region_distance[mask] = distances[mask]
        
        return region_map
    
    def generate_climate(self, params: TerrainParams, regions: np.ndarray) -> np.ndarray:
        """生成气候图"""
        print("生成气候图...")
        
        height, width = params.size[1], params.size[0]
        
        # 基础气候图（基于降水量参数）
        climate_map = np.full((height, width), params.precipitation)
        
        # 根据分区添加变化
        num_regions = np.max(regions) + 1
        for region_id in range(num_regions):
            mask = regions == region_id
            
            # 每个区域有自己的气候特征
            region_precip = params.precipitation * self.rng.uniform(0.7, 1.3)
            region_precip = np.clip(region_precip, 0.0, 1.0)
            
            # 应用区域气候
            climate_map[mask] = region_precip
            
            # 添加区域内部变化
            if np.any(mask):
                region_noise = self._perlin_noise_2d((height, width), scale=0.2) * 0.2
                climate_map[mask] += region_noise[mask]
                climate_map = np.clip(climate_map, 0.0, 1.0)
        
        return climate_map
    
    def simulate_erosion(self, heightmap: np.ndarray, params: TerrainParams, 
                         climate_map: np.ndarray, regions: np.ndarray) -> np.ndarray:
        """模拟侵蚀作用"""
        print(f"模拟侵蚀，迭代次数: {params.erosion_iterations}")
        
        eroded = heightmap.copy()
        height, width = heightmap.shape
        
        # 侵蚀迭代
        for iteration in range(params.erosion_iterations):
            if iteration % 2 == 0:
                print(f"  侵蚀迭代 {iteration + 1}/{params.erosion_iterations}")
            
            # 1. 水力侵蚀（基于降水）
            if params.precipitation > 0.1 and params.river_intensity > 0.1:
                eroded = self._simulate_hydraulic_erosion(
                    eroded, climate_map, params.river_intensity
                )
            
            # 2. 热力风化（基于温度变化）
            if params.temperature < 0.8:  # 不是极端炎热
                eroded = self._simulate_thermal_weathering(
                    eroded, params.temperature
                )
            
            # 3. 风力侵蚀（基于风力和干旱程度）
            if params.wind_intensity > 0.3 and params.precipitation < 0.4:
                eroded = self._simulate_wind_erosion(
                    eroded, params.wind_intensity
                )
        
        # 根据地形年龄进行平滑（古老地形更平缓）
        if params.terrain_age < 0.5:
            from scipy.ndimage import gaussian_filter
            sigma = 2 + (1 - params.terrain_age) * 3
            eroded = gaussian_filter(eroded, sigma=sigma)
        
        # 归一化到0-1范围
        eroded = (eroded - np.min(eroded)) / (np.max(eroded) - np.min(eroded) + 1e-8)
        
        return eroded
    
    def _simulate_hydraulic_erosion(self, heightmap: np.ndarray, 
                                   climate_map: np.ndarray, 
                                   intensity: float) -> np.ndarray:
        """模拟水力侵蚀（简化版）"""
        height, width = heightmap.shape
        eroded = heightmap.copy()
        
        # 计算坡度
        gradient_y, gradient_x = np.gradient(heightmap)
        slope = np.sqrt(gradient_x ** 2 + gradient_y ** 2)
        
        # 计算水流积累（简化）
        water_accumulation = np.zeros_like(heightmap)
        
        # 从高到低模拟水流
        sorted_indices = np.dstack(np.unravel_index(
            np.argsort(heightmap.ravel())[::-1], heightmap.shape
        ))[0]
        
        for idx in sorted_indices:
            y, x = idx[0], idx[1]
            
            if y == 0 or y == height-1 or x == 0 or x == width-1:
                continue
            
            # 流向最低的邻居
            local_heights = heightmap[y-1:y+2, x-1:x+2]
            min_height = np.min(local_heights)
            
            if min_height < heightmap[y, x]:
                # 计算侵蚀量
                erosion_amount = slope[y, x] * climate_map[y, x] * intensity * 0.01
                
                # 应用侵蚀
                eroded[y, x] -= erosion_amount
                
                # 沉积到最低点
                min_pos = np.argmin(local_heights)
                dy, dx = divmod(min_pos, 3)
                target_y = y + dy - 1
                target_x = x + dx - 1
                
                eroded[target_y, target_x] += erosion_amount * 0.5  # 部分沉积
        
        return eroded
    
    def _simulate_thermal_weathering(self, heightmap: np.ndarray, 
                                    temperature: float) -> np.ndarray:
        """模拟热力风化"""
        # 温度变化导致的热应力（简化）
        if temperature < 0.3 or temperature > 0.7:  # 极端温度
            weathering_rate = 0.005
        else:
            weathering_rate = 0.001
        
        # 计算坡度
        gradient_y, gradient_x = np.gradient(heightmap)
        slope = np.sqrt(gradient_x ** 2 + gradient_y ** 2)
        
        # 风化量与坡度成正比（陡坡更容易风化）
        weathering = slope * weathering_rate
        
        return heightmap - weathering
    
    def _simulate_wind_erosion(self, heightmap: np.ndarray, 
                              wind_intensity: float) -> np.ndarray:
        """模拟风力侵蚀"""
        # 风力侵蚀（简化）
        wind_erosion = np.zeros_like(heightmap)
        
        # 风向假设为从左到右
        for y in range(heightmap.shape[0]):
            for x in range(1, heightmap.shape[1]):
                # 如果当前点比左边点高，可能被侵蚀
                if heightmap[y, x] > heightmap[y, x-1]:
                    height_diff = heightmap[y, x] - heightmap[y, x-1]
                    erosion_amount = min(height_diff * 0.1 * wind_intensity, heightmap[y, x] * 0.05)
                    
                    wind_erosion[y, x] -= erosion_amount
        
        return heightmap + wind_erosion
    
    def post_process(self, heightmap: np.ndarray, params: TerrainParams) -> np.ndarray:
        """后处理"""
        print("进行后处理...")
        
        # 1. 确保非负
        heightmap = np.maximum(heightmap, 0)
        
        # 2. 根据距海岸距离调整（沿海较低）
        if params.distance_to_coast < 0.3:
            # 沿海区域：创建海岸线
            from scipy.ndimage import gaussian_filter
            coastal_mask = self._create_coastal_mask(heightmap.shape, params.distance_to_coast)
            heightmap = heightmap * (0.3 + coastal_mask * 0.7)
        
        # 3. 添加细节噪声
        detail_noise = self._perlin_noise_2d(heightmap.shape, scale=0.02, octaves=2)
        heightmap = heightmap * 0.95 + detail_noise * 0.05
        
        # 4. 最终归一化
        heightmap = (heightmap - np.min(heightmap)) / (np.max(heightmap) - np.min(heightmap) + 1e-8)
        
        return heightmap
    
    def _create_coastal_mask(self, shape: Tuple[int, int], distance_to_coast: float) -> np.ndarray:
        """创建海岸线掩码"""
        height, width = shape
        
        # 创建距离场（简化）
        mask = np.ones(shape)
        
        # 假设海岸线在图像边缘
        for y in range(height):
            for x in range(width):
                # 到最近边缘的距离
                dist_to_edge = min(x, width-1-x, y, height-1-y)
                
                # 归一化距离
                norm_dist = dist_to_edge / min(width, height) * 2
                
                # 根据距海岸距离参数调整
                if distance_to_coast < 0.3:  # 沿海
                    if norm_dist < 0.1:
                        mask[y, x] = 0.1  # 海洋
                    elif norm_dist < 0.2:
                        mask[y, x] = 0.3  # 海岸带
                elif distance_to_coast > 0.7:  # 内陆
                    mask[y, x] = 1.0  # 全部陆地
        
        return mask