import os

FONTS = {
    "feasibly": {"type": "ttf", "file": "FeasiblySingleLine-z8D90.ttf"},
    "headstay": {"type": "ttf", "file": "HeadstayRegular.ttf"},
    "backstay": {"type": "ttf", "file": "BackstaySingleLine-rgOw8.ttf"},
    "caveat": {"type": "ttf", "file": "Caveat-VariableFont_wght.ttf"},
    "permanent_marker": {"type": "ttf", "file": "PermanentMarker-Regular.ttf"},
    "notosans_math": {"type": "ttf", "file": "NotoSansMath-Regular.ttf"},
    "handanimtype1": {"type": "custom", "file": os.path.join("custom", "handanimtype1.json")},
    "hershey_mathlow": {"type": "hershey", "name": "mathlow"},
    "hershey_rowmans": {"type": "hershey", "name": "rowmans"},
    "hershey_cursive": {"type": "hershey", "name": "cursive"},
}


def list_fonts():
    """
    List all available fonts
    """
    return list(FONTS.keys())


def get_font_info(font_name):
    """
    Get the metadata for a font
    """
    return FONTS.get(font_name)


def get_font_path(font_name):
    """
    Get the physical path to a font (for TTF and Custom fonts)
    """
    info = FONTS.get(font_name)
    if not info or info.get("type") == "hershey":
        raise ValueError(f"Font {font_name} does not have a physical path")
        
    font_root_path = os.path.join(os.path.dirname(__file__), "../../../fonts/")
    return os.path.join(font_root_path, info["file"])
