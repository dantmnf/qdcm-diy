import colour
from typing import Optional

class ColorPipeline:
    def __init__(self, degamma: Optional[colour.LUT3x1D] = None, gamut: Optional[colour.LUT3D] = None, gamma: Optional[colour.LUT3x1D] = None):
        self.degamma = degamma
        self.gamut = gamut
        self.gamma = gamma
