import colour
import numpy as np

def resample_lut(lut3d, size):
    return colour.LUT3D(lut3d.apply(colour.LUT3D.linear_table(size), interpolator=colour.algebra.interpolation.table_interpolation_tetrahedral))

def to_12bit(a):
    return np.uint32(np.clip(a, 0, 1) * 4095 + 0.5)

def to_4096(a):
    return np.uint32(np.clip(a, 0, 1) * 4096 + 0.5)

def to_10bit(a):
    return np.uint32(np.clip(a, 0, 1) * 1023 + 0.5)

def load_argyll_cal(filename):
    from . import cgats
    with open(filename, "rb") as f:
        cal = cgats.read(f)
    return colour.LUT3x1D(np.asarray(cal.dataframe[['RGB_R', 'RGB_G', 'RGB_B']]))

def load_anylut(filename: str):
    if filename.endswith(".cal"):
        return load_argyll_cal(filename)
    lut = colour.io.read_LUT(filename)
    assert np.all(lut.domain == np.array([[0,0,0],[1,1,1]])), "LUT domain must be [0,0,0]-[1,1,1]"
    return lut

def load_lut3x1d(filename: str):
    lut = load_anylut(filename)
    assert isinstance(lut, colour.LUT3x1D)
    return lut

def load_lut3d(filename: str):
    lut = colour.io.read_LUT(filename)
    assert isinstance(lut, colour.LUT3D)
    return lut