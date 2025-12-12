"""
图像处理工具
"""
import numpy as np
from PIL import Image, ImageFilter
from PyQt5.QtGui import QImage, QColor


def array_to_qimage(array):
    """将NumPy数组转换为QImage"""
    if array is None:
        return None
    
    # 确保是2D数组
    if len(array.shape) == 2:
        height, width = array.shape
        channels = 1
    elif len(array.shape) == 3:
        height, width, channels = array.shape
    else:
        raise ValueError("数组必须是2D或3D")
    
    # 归一化到0-255
    if array.dtype != np.uint8:
        array_normalized = (array - np.min(array)) / (np.max(array) - np.min(array) + 1e-8)
        array_uint8 = (array_normalized * 255).astype(np.uint8)
    else:
        array_uint8 = array
    
    # 创建QImage
    if channels == 1:
        bytes_per_line = width
        qimage = QImage(array_uint8.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
    elif channels == 3:
        bytes_per_line = 3 * width
        qimage = QImage(array_uint8.data, width, height, bytes_per_line, QImage.Format_RGB888)
    elif channels == 4:
        bytes_per_line = 4 * width
        qimage = QImage(array_uint8.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
    else:
        raise ValueError(f"不支持的通道数: {channels}")
    
    # 保持对数组的引用，避免被垃圾回收
    qimage._array_ref = array_uint8
    
    return qimage


def generate_texture(heightmap, colormap='terrain'):
    """从高度图生成纹理"""
    if heightmap is None:
        return None
    
    height, width = heightmap.shape
    
    # 创建彩色纹理
    texture = np.zeros((height, width, 3), dtype=np.uint8)
    
    # 预定义颜色映射
    colormaps = {
        'terrain': [
            (0.0, (10, 10, 80)),      # 深海
            (0.2, (30, 30, 200)),     # 浅海
            (0.25, (240, 240, 100)),  # 海滩
            (0.35, (50, 180, 50)),    # 草地
            (0.5, (34, 139, 34)),     # 森林
            (0.7, (139, 90, 43)),     # 山地
            (0.85, (100, 100, 100)),  # 岩石
            (1.0, (255, 255, 255)),   # 雪
        ],
        'desert': [
            (0.0, (210, 180, 140)),   # 沙漠
            (0.7, (160, 120, 80)),    # 岩石
            (1.0, (255, 255, 255)),   # 雪
        ],
        'grayscale': [
            (0.0, (0, 0, 0)),
            (1.0, (255, 255, 255)),
        ]
    }
    
    # 选择颜色映射
    if colormap not in colormaps:
        colormap = 'terrain'
    
    cmap = colormaps[colormap]
    
    # 应用颜色映射
    for y in range(height):
        for x in range(width):
            height_val = heightmap[y, x]
            
            # 找到对应的颜色区间
            for i in range(len(cmap) - 1):
                if cmap[i][0] <= height_val <= cmap[i+1][0]:
                    # 线性插值
                    t = (height_val - cmap[i][0]) / (cmap[i+1][0] - cmap[i][0] + 1e-8)
                    color = [
                        int(cmap[i][1][0] * (1-t) + cmap[i+1][1][0] * t),
                        int(cmap[i][1][1] * (1-t) + cmap[i+1][1][1] * t),
                        int(cmap[i][1][2] * (1-t) + cmap[i+1][1][2] * t)
                    ]
                    texture[y, x] = color
                    break
    
    # 转换为PIL图像
    return Image.fromarray(texture)


def apply_lighting(heightmap, light_direction=(1, 1, 1)):
    """应用光照效果"""
    if heightmap is None:
        return None
    
    # 计算法向量
    gradient_y, gradient_x = np.gradient(heightmap)
    
    # 归一化光方向
    light_dir = np.array(light_direction)
    light_dir = light_dir / np.linalg.norm(light_dir)
    
    # 计算法向量
    normal = np.stack([-gradient_x, -gradient_y, np.ones_like(heightmap)], axis=2)
    normal_norm = np.linalg.norm(normal, axis=2, keepdims=True)
    normal = normal / (normal_norm + 1e-8)
    
    # 计算光照
    lighting = np.sum(normal * light_dir, axis=2)
    lighting = np.clip(lighting * 0.8 + 0.2, 0, 1)  # 添加环境光
    
    return lighting


def create_shaded_texture(heightmap, colormap='terrain'):
    """创建带阴影的纹理"""
    # 生成基础纹理
    texture = generate_texture(heightmap, colormap)
    if texture is None:
        return None
    
    # 应用光照
    lighting = apply_lighting(heightmap)
    if lighting is None:
        return texture
    
    # 转换为NumPy数组
    texture_array = np.array(texture).astype(np.float32) / 255.0
    
    # 应用光照
    for c in range(3):
        texture_array[:, :, c] *= lighting
    
    # 限制到0-1范围
    texture_array = np.clip(texture_array, 0, 1)
    
    # 转换回uint8
    texture_array = (texture_array * 255).astype(np.uint8)
    
    return Image.fromarray(texture_array)


def heightmap_to_colormap(heightmap, colormap='terrain'):
    """将高度图转换为彩色图（NumPy数组）"""
    if heightmap is None:
        return None
    
    # 生成纹理
    texture_img = generate_texture(heightmap, colormap)
    if texture_img is None:
        return None
    
    return np.array(texture_img)


def create_normal_map(heightmap, strength=1.0):
    """创建法线贴图"""
    if heightmap is None:
        return None
    
    height, width = heightmap.shape
    
    # 计算梯度
    gradient_y, gradient_x = np.gradient(heightmap)
    
    # 计算法向量
    normal = np.stack([-gradient_x * strength, -gradient_y * strength, np.ones_like(heightmap)], axis=2)
    normal_norm = np.linalg.norm(normal, axis=2, keepdims=True)
    normal = normal / (normal_norm + 1e-8)
    
    # 转换到0-255范围（法线贴图通常存储为RGB）
    normal_map = ((normal + 1) * 127.5).astype(np.uint8)
    
    return normal_map


if __name__ == "__main__":
    # 测试代码
    test_heightmap = np.random.rand(100, 100)
    
    # 测试生成纹理
    texture = generate_texture(test_heightmap)
    if texture:
        texture.save("test_texture.png")
        print("测试纹理已保存")
    
    # 测试带阴影的纹理
    shaded_texture = create_shaded_texture(test_heightmap)
    if shaded_texture:
        shaded_texture.save("test_shaded_texture.png")
        print("测试带阴影纹理已保存")
    
    print("测试完成!")