import xml.dom.minidom
import colour
import numpy as np

from qdcmdiy.pipeline import ColorPipeline
from .data import resample_lut, to_10bit, to_12bit, to_4096

def lut3x1d_to_igc_xml(lut: colour.LUT3x1D):
    if lut.size != 256:
        lut = colour.LUT3x1D(lut.apply(colour.LUT3x1D.linear_table(256)))
    buf = np.zeros(1024*3+3, dtype="<u4")
    buf[0] = 0
    buf[1] = 256
    buf[2] = 6
    buf[3:256+3] = to_10bit(lut.table[:, 0].ravel())
    buf[1024+3:1024+3+256] = to_10bit(lut.table[:, 1].ravel())
    buf[2048+3:2048+3+256] = to_10bit(lut.table[:, 2].ravel())
    return buf.tobytes().hex().upper()

def lut3x1d_to_gc_xml(lut: colour.LUT3x1D):
    if lut.size != 1024:
        lut = colour.LUT3x1D(lut.apply(colour.LUT3x1D.linear_table(1024)))
    buf = np.zeros(1024*3+3, dtype="<u4")
    buf[0] = 1
    buf[1] = 1024
    buf[2] = 6
    buf[3:1024+3] = to_10bit(lut.table[:, 0].ravel())
    buf[1024+3:1024+3+1024] = to_10bit(lut.table[:, 1].ravel())
    buf[2048+3:2048+3+1024] = to_10bit(lut.table[:, 2].ravel())
    return buf.tobytes().hex().upper()

def lut3d_to_xml(lut: colour.LUT3D):
    linear17 = colour.LUT3D.linear_table(17)
    if lut.size != 17:
        lut = resample_lut(lut, 17)
    buf = np.zeros(17*17*17*6+4, dtype="<u4")
    buf[3] = 4913
    lutview = buf[4:].reshape((17, 17, 17, 2, 3))
    i = 4
    for b in range(17):
        for g in range(17):
            for r in range(17):
                lutview[b, g, r, 0, :] = to_4096(linear17[r, g, b])
                lutview[b, g, r, 1, :] = to_4096(lut.table[r, g, b])
    return buf.tobytes().hex().upper()

def set_inner_text(node, text):
    for child in node.childNodes:
        node.removeChild(child)
    node.appendChild(node.ownerDocument.createTextNode(text))

class QdcmDatabaseXml:
    def __init__(self, filename):
        self.dom = xml.dom.minidom.parse(filename)
        modes = {}
        for mode in self.dom.getElementsByTagName("Mode"):
            modes[mode.getAttribute("Name")] = QdcmModeXml(mode)
        self.modes = modes
    def get_mode(self, name):
        return self.modes[name]
    def get_mode_names(self):
        return list(self.modes.keys())
    def dump(self, io):
        self.dom.writexml(io)

class QdcmModeXml:
    def __init__(self, dom_node: xml.dom.minidom.Element):
        self.dom_node = dom_node

    def set_color_pipeline(self, pipeline: ColorPipeline):
        def find_feature(feature_type):
            for feature in self.dom_node.getElementsByTagName("Feature"):
                if feature.getAttribute("FeatureType") == feature_type:
                    return feature
            return None
        
        igc_feature = find_feature("7")
        gc_feature = find_feature("8")
        gamut_feature = find_feature("3")
        mixer_gc_feature = find_feature("6")
        pcc_feature = find_feature("2")

        if igc_feature is not None:
            print("found igc feature")
            if pipeline.degamma is not None:
                set_inner_text(igc_feature, lut3x1d_to_igc_xml(pipeline.degamma))
                igc_feature.setAttribute("Disable", "false")
            else:
                igc_feature.setAttribute("Disable", "true")
        elif pipeline.degamma is not None:
            igc_feature = self.dom_node.ownerDocument.createElement("Feature")
            igc_feature.setAttribute("FeatureType", "7")
            igc_feature.setAttribute("Disable", "false")
            igc_feature.setAttribute("DataSize", "12300")
            igc_feature.appendChild(self.dom_node.ownerDocument.createTextNode(lut3x1d_to_igc_xml(pipeline.degamma)))
            self.dom_node.appendChild(igc_feature)

        if gc_feature is not None:
            print("found gc feature")
            if pipeline.degamma is not None:
                set_inner_text(gc_feature, lut3x1d_to_igc_xml(pipeline.gamma))
                gc_feature.setAttribute("Disable", "false")
            else:
                gc_feature.setAttribute("Disable", "true")
        elif pipeline.gamma is not None:
            gc_feature = self.dom_node.ownerDocument.createElement("Feature")
            gc_feature.setAttribute("FeatureType", "8")
            gc_feature.setAttribute("Disable", "false")
            gc_feature.setAttribute("DataSize", "12300")
            igc_feature.appendChild(self.dom_node.ownerDocument.createTextNode(lut3x1d_to_gc_xml(pipeline.degamma)))
            self.dom_node.appendChild(gc_feature)

        if gamut_feature is not None:
            print("found gamut feature")
            if pipeline.gamut is not None:
                set_inner_text(gamut_feature, lut3d_to_xml(pipeline.gamut))
                gamut_feature.setAttribute("Disable", "false")
            else:
                gamut_feature.setAttribute("Disable", "true")
        elif pipeline.gamma is not None:
            gamut_feature = self.dom_node.ownerDocument.createElement("Feature")
            gamut_feature.setAttribute("FeatureType", "3")
            gamut_feature.setAttribute("Disable", "false")
            gamut_feature.setAttribute("DataSize", "117928")
            igc_feature.appendChild(self.dom_node.ownerDocument.createTextNode(lut3d_to_xml(pipeline.degamma)))
            self.dom_node.appendChild(gamut_feature)

        if mixer_gc_feature is not None:
            mixer_gc_feature.setAttribute("Disable", "true")

        if pcc_feature is not None:
            pcc_feature.setAttribute("Disable", "true")
