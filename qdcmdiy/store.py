from typing import Protocol

from qdcmdiy.pipeline import ColorPipeline

class QdcmMode(Protocol):
    def set_color_pipeline(self, pipeline: ColorPipeline):
        ...

class QdcmDatabase(Protocol):
    def get_mode(self, name) -> QdcmMode:
        ...
    def get_mode_names(self) -> list[str]:
        ...
    def dump(self, io):
        ...

def load(filename: str) -> QdcmDatabase:
    if filename.endswith(".xml"):
        from qdcmdiy.store_xml import QdcmDatabaseXml
        return QdcmDatabaseXml(filename)
    elif filename.endswith(".json"):
        from qdcmdiy.store_json import QdcmDatabaseJson
        return QdcmDatabaseJson(filename)
    else:
        raise ValueError("Unknown file type")
