import json
import numpy as np
import colour
from qdcmdiy.data import resample_lut, to_12bit, to_10bit, to_4096
from qdcmdiy.pipeline import ColorPipeline


_gamut_map = {
    'sRGB': '1',
    'P3': '12'
}

_transfer_map = {
    'sRGB': '1'
}

_dummy_pcc = {
        "B": {
        "b": 1.0,
        "bb": 0.0,
        "c": 0.0,
        "g": 0.0,
        "gb": 0.0,
        "gg": 0.0,
        "r": 0.0,
        "rb": 0.0,
        "rg": 0.0,
        "rgb": 0.0,
        "rr": 0.0
    },
    "G": {
        "b": 0.0,
        "bb": 0.0,
        "c": 0.0,
        "g": 1.0,
        "gb": 0.0,
        "gg": 0.0,
        "r": 0.0,
        "rb": 0.0,
        "rg": 0.0,
        "rgb": 0.0,
        "rr": 0.0
    },
    "R": {
        "b": 0.0,
        "bb": 0.0,
        "c": 0.0,
        "g": 0.0,
        "gb": 0.0,
        "gg": 0.0,
        "r": 1.0,
        "rb": 0.0,
        "rg": 0.0,
        "rgb": 0.0,
        "rr": 0.0
    },
    "disableBeforeUpload": False,
    "displayID": 0,
    "enable": False
}

_linear_igc = {
    "displayID": 0,
    "ditherEnable": True,
    "ditherStrength": 4,
    "enable": False,
    "lutB": [int(x) for x in to_12bit(np.arange(257) / 256)],
    "lutG": [int(x) for x in to_12bit(np.arange(257) / 256)],
    "lutR": [int(x) for x in to_12bit(np.arange(257) / 256)],
}

_linear_gc = {
    "bitsRounding": 10,
    "displayID": 0,
    "enable": False,
    "lutB": list(range(1024)),
    "lutG": list(range(1024)),
    "lutR": list(range(1024)),
}

def decode_str(s: str):
    assert len(s) % 2 == 0
    size = len(s) // 2
    buf = bytearray(size)
    pos = 0
    if size % 2 == 1:
        buf[0] = int(s[0:2], 16)
        pos = 2
    for i in range(pos, len(s), 4):
        byte0 = int(s[i:i+2], 16)
        byte1 = int(s[i+2:i+4], 16)
        pos = i // 2
        buf[pos] = byte1
        buf[pos+1] = byte0
    return buf

class NioStyleBuffer:
    def __init__(self, size):
        self.buffer = bytearray(size)
        self.pos = 0
    def write(self, s):
        view = memoryview(self.buffer)
        view[self.pos:self.pos+len(s)] = s
        self.pos += len(s)

def encode(b):
    buffer = NioStyleBuffer(len(b) * 2)
    offset = 0
    if len(b) % 2 == 1:
        buffer.write("{:02X}".format(b[0]).encode())
        offset = 1
    for i in range(offset, len(b), 2):
        buffer.write("{:02X}{:02X}".format(b[i+1], b[i]).encode())
    return buffer.buffer.decode()

def encode_nested_json(jdoc):
    s = json.dumps(jdoc, indent=None, separators=(',', ':'))
    return encode(s.encode())


def lut3x1d_to_igc_json(lut: colour.LUT3x1D):
    if lut.size != 257:
        lut = colour.LUT3x1D(lut.apply(colour.LUT3x1D.linear_table(257)))
    return {
        "displayID": 0,
        "ditherEnable": True,
        "ditherStrength": 4,
        "enable": True,
        "lutB": [int(x) for x in to_12bit(lut.table[:, 2].ravel())],
        "lutG": [int(x) for x in to_12bit(lut.table[:, 1].ravel())],
        "lutR": [int(x) for x in to_12bit(lut.table[:, 0].ravel())],
    }


def lut3x1d_to_gc_json(lut: colour.LUT3x1D):
    if lut.size != 1024:
        lut = colour.LUT3x1D(lut.apply(colour.LUT3x1D.linear_table(1024)))
    return {
        "bitsRounding": 10,
        "displayID": 0,
        "enable": True,
        "lutB": [int(x) for x in to_10bit(lut.table[:, 2].ravel())],
        "lutG": [int(x) for x in to_10bit(lut.table[:, 1].ravel())],
        "lutR": [int(x) for x in to_10bit(lut.table[:, 0].ravel())],
    }


def lut3d_to_json(lut: colour.LUT3D):
    
    def convert_to_qdcmjson(lut3d):
        table = lut3d.table
        size = lut3d.size
        return [",".join(str(x) for x in to_4096(table[r, g, b])) for b in range(size) for g in range(size) for r in range(size)]

    assert lut.size >= 17, "LUT3D size must be at least 17"
    if lut.size > 17:
        fine = resample_lut(lut, 17)
    else:
        fine = lut
    coarse = resample_lut(lut, 5)
    return {
        "displayID": 0,
        "enable": True,
        "mapCoarse": convert_to_qdcmjson(coarse),
        "mapFine": convert_to_qdcmjson(fine),
    }

_linear_3dlut = lut3d_to_json(colour.LUT3D(size=17))
_linear_3dlut["enable"] = False

class QdcmDatabaseJson:
    def __init__(self, filename: str):
        with open(filename, 'r') as f:
            jdoc = json.load(f)
        self.jdoc = jdoc
        modes = {}
        panel_key = next(iter(set(jdoc.keys()) - {"Copyright", "Version"}))
        for mode_name, mode_obj in jdoc[panel_key].items():
            try:
                modename2 = (
                    f"gamut {_gamut_map[mode_obj['Applicability']['ColorPrimaries']]}" +
                    f" gamma {_transfer_map[mode_obj['Applicability']['GammaTransfer']]}" +
                    f" intent {mode_obj['Applicability']['RenderIntent']}" +
                    f" Dynamic_range {mode_obj['DynamicRange']}"
                )
                modes[modename2] = QdcmModeJson(mode_obj)
            except KeyError:
                pass
        self.modes = modes

    def get_mode_names(self):
        return list(self.modes.keys())

    def get_mode(self, name):
        return self.modes[name]
    
    def dump(self, io):
        json.dump(self.jdoc, io, indent=None, separators=(',', ':'))
        
class QdcmModeJson:
    def __init__(self, objref: dict):
        self.objref = objref
    def set_color_pipeline(self, pipeline: ColorPipeline):
        assert pipeline is not None
        if pipeline.degamma is not None:
            self.objref["PostBlendIGC"] = encode_nested_json(lut3x1d_to_igc_json(pipeline.degamma))
        else:
            self.objref["PostBlendIGC"] = encode_nested_json(_linear_igc)
        if pipeline.gamut is not None:
            self.objref["PostBlendGamut"] = encode_nested_json(lut3d_to_json(pipeline.gamut))
        else:
            self.objref["PostBlendGamut"] = encode_nested_json(_linear_3dlut)
        if pipeline.gamma is not None:
            self.objref["PostBlendGC"] = encode_nested_json(lut3x1d_to_gc_json(pipeline.gamma))
        else:
            self.objref["PostBlendGC"] = encode_nested_json(_linear_gc)
        self.objref["PostBlendPCC"] = encode_nested_json(_dummy_pcc)
