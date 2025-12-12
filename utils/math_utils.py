"""
数学工具函数
"""
import numpy as np


def normalize_array(arr):
    """归一化数组到0-1范围"""
    if arr is None:
        return None
    
    arr_min = np.min(arr)
    arr_max = np.max(arr)
    
    if arr_max - arr_min < 1e-8:
        return np.zeros_like(arr)
    
    return (arr - arr_min) / (arr_max - arr_min)


def calculate_slope(heightmap):
    """计算坡度"""
    if heightmap is None:
        return None
    
    gradient_y, gradient_x = np.gradient(heightmap)
    slope = np.sqrt(gradient_x**2 + gradient_y**2)
    
    return normalize_array(slope)


def calculate_aspect(heightmap):
    """计算坡向"""
    if heightmap is None:
        return None
    
    gradient_y, gradient_x = np.gradient(heightmap)
    aspect = np.arctan2(gradient_y, gradient_x)
    
    # 转换到0-1范围
    aspect = (aspect + np.pi) / (2 * np.pi)
    
    return aspect


def gaussian_kernel(size, sigma=1.0):
    """生成高斯核"""
    ax = np.arange(-size // 2 + 1., size // 2 + 1.)
    xx, yy = np.meshgrid(ax, ax)
    kernel = np.exp(-(xx**2 + yy**2) / (2. * sigma**2))
    return kernel / np.sum(kernel)


def apply_gaussian_filter(array, sigma=1.0):
    """应用高斯滤波"""
    if array is None:
        return None
    
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(array, sigma=sigma)


def resample_array(array, new_shape):
    """重采样数组到新尺寸"""
    if array is None:
        return None
    
    from scipy.ndimage import zoom
    zoom_factors = (new_shape[0] / array.shape[0], new_shape[1] / array.shape[1])
    return zoom(array, zoom_factors, order=1)