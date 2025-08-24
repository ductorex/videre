import os
from videre.fonts import _file_path

FOLDER_FONT = os.path.abspath(os.path.join(os.path.dirname(__file__)))

_FOLDER_SOURCE_SANS = os.path.join(FOLDER_FONT, "source-sans", "TTF")
PATH_SOURCE_SANS_REGULAR = _file_path(_FOLDER_SOURCE_SANS, "SourceSans3-Regular.ttf")
PATH_SOURCE_SANS_LIGHT = _file_path(_FOLDER_SOURCE_SANS, "SourceSans3-Light.ttf")
PATH_SOURCE_HAN_SANS_TTC = _file_path(FOLDER_FONT, "other-ttc/SourceHanSans-VF.ttf.ttc")
PATH_SOURCE_HAN_SANS_JP = _file_path(FOLDER_FONT, "other-ttf/SourceHanSans-VF.ttf")
