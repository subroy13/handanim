import os

FONT_PATHS = {
    "feasibly": "FeasiblySingleLine-z8D90.ttf",
    "headstay": "HeadstayRegular.ttf",
    "backstay": "BackstaySingleLine-rgOw8.ttf",
    "caveat": "Caveat-VariableFont_wght.ttf",
    "permanent_marker": "PermanentMarker-Regular.ttf",
    "notosans_math": "NotoSansMath-Regular.ttf",
    "handanimtype1": os.path.join("custom", "handanimtype1.json"),
}


def list_fonts():
    """
    List all available fonts
    """
    return list(FONT_PATHS.keys())


def get_font_path(font_name):
    """
    Get the path to a font
    """
    font_root_path = os.path.join(os.path.dirname(__file__), "../../../fonts/")
    return os.path.join(font_root_path, FONT_PATHS[font_name])
