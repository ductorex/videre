from typing import TypeAlias

from videre.core.pygame_utils import Color


class Colors:
    aliceblue = Color(240, 248, 255)
    antiquewhite = Color(250, 235, 215)
    aqua = Color(0, 255, 255)
    aquamarine = Color(127, 255, 212)
    azure = Color(240, 255, 255)
    beige = Color(245, 245, 220)
    bisque = Color(255, 228, 196)
    black = Color(0, 0, 0)
    blanchedalmond = Color(255, 235, 205)
    blue = Color(0, 0, 255)
    blueviolet = Color(138, 43, 226)
    brown = Color(165, 42, 42)
    burlywood = Color(222, 184, 135)
    cadetblue = Color(95, 158, 160)
    chartreuse = Color(127, 255, 0)
    chocolate = Color(210, 105, 30)
    coral = Color(255, 127, 80)
    cornflowerblue = Color(100, 149, 237)
    cornsilk = Color(255, 248, 220)
    crimson = Color(220, 20, 60)
    cyan = Color(0, 255, 255)
    darkblue = Color(0, 0, 139)
    darkcyan = Color(0, 139, 139)
    darkgoldenrod = Color(184, 134, 11)
    darkgray = Color(169, 169, 169)
    darkgreen = Color(0, 100, 0)
    darkkhaki = Color(189, 183, 107)
    darkmagenta = Color(139, 0, 139)
    darkolivegreen = Color(85, 107, 47)
    darkorange = Color(255, 140, 0)
    darkorchid = Color(153, 50, 204)
    darkred = Color(139, 0, 0)
    darksalmon = Color(233, 150, 122)
    darkseagreen = Color(143, 188, 139)
    darkslateblue = Color(72, 61, 139)
    darkslategray = Color(47, 79, 79)
    darkturquoise = Color(0, 206, 209)
    darkviolet = Color(148, 0, 211)
    deeppink = Color(255, 20, 147)
    deepskyblue = Color(0, 191, 255)
    dimgray = Color(105, 105, 105)
    dodgerblue = Color(30, 144, 255)
    floralwhite = Color(253, 245, 230)
    forestgreen = Color(34, 139, 34)
    fuchsia = Color(255, 0, 255)
    gainsboro = Color(220, 220, 220)
    ghostwhite = Color(248, 248, 255)
    gold = Color(255, 215, 0)
    goldenrod = Color(218, 165, 32)
    gray = Color(128, 128, 128)
    green = Color(0, 128, 0)
    greenyellow = Color(173, 255, 47)
    honeydew = Color(240, 255, 240)
    hotpink = Color(255, 105, 180)
    indianred = Color(205, 92, 92)
    indigo = Color(75, 0, 130)
    ivory = Color(255, 255, 240)
    khaki = Color(240, 230, 140)
    lavender = Color(230, 230, 250)
    lavenderblush = Color(255, 240, 245)
    lawngreen = Color(124, 252, 0)
    lemonchiffon = Color(255, 250, 205)
    lightblue = Color(173, 216, 230)
    lightcoral = Color(240, 128, 128)
    lightcyan = Color(224, 255, 255)
    lightgoldenrodyellow = Color(250, 250, 210)
    lightgray = Color(211, 211, 211)
    lightgreen = Color(144, 238, 144)
    lightpink = Color(255, 182, 193)
    lightsalmon = Color(255, 160, 122)
    lightseagreen = Color(32, 178, 170)
    lightskyblue = Color(135, 206, 250)
    lightslategray = Color(119, 136, 153)
    lightsteelblue = Color(176, 196, 222)
    lightyellow = Color(255, 255, 224)
    lime = Color(0, 255, 0)
    limegreen = Color(50, 205, 50)
    linen = Color(250, 240, 230)
    magenta = Color(255, 0, 255)
    maroon = Color(128, 0, 0)
    mediumaquamarine = Color(102, 205, 170)
    mediumblue = Color(0, 0, 205)
    mediumorchid = Color(186, 85, 211)
    mediumpurple = Color(147, 112, 219)
    mediumseagreen = Color(60, 179, 113)
    mediumslateblue = Color(123, 104, 238)
    mediumspringgreen = Color(0, 250, 154)
    mediumturquoise = Color(72, 209, 204)
    mediumvioletred = Color(199, 21, 133)
    midnightblue = Color(25, 25, 112)
    mintcream = Color(245, 255, 250)
    mistyrose = Color(255, 228, 225)
    moccasin = Color(255, 228, 181)
    navajowhite = Color(255, 222, 173)
    navy = Color(0, 0, 128)
    oldlace = Color(253, 245, 230)
    olive = Color(128, 128, 0)
    olivedrab = Color(107, 142, 35)
    orange = Color(255, 165, 0)
    orangered = Color(255, 69, 0)
    orchid = Color(218, 112, 214)
    palegoldenrod = Color(238, 232, 170)
    palegreen = Color(152, 251, 152)
    paleturquoise = Color(175, 238, 238)
    palevioletred = Color(219, 112, 147)
    papayawhip = Color(255, 239, 213)
    peachpuff = Color(255, 218, 185)
    peru = Color(205, 133, 63)
    pink = Color(255, 192, 203)
    plum = Color(221, 160, 221)
    powderblue = Color(176, 224, 230)
    purple = Color(128, 0, 128)
    rebeccapurple = Color(102, 51, 153)
    red = Color(255, 0, 0)
    rosybrown = Color(188, 143, 143)
    royalblue = Color(65, 105, 225)
    saddlebrown = Color(139, 69, 19)
    salmon = Color(250, 128, 114)
    sandybrown = Color(244, 164, 96)
    seagreen = Color(46, 139, 87)
    seashell = Color(255, 245, 238)
    sienna = Color(160, 82, 45)
    silver = Color(192, 192, 192)
    skyblue = Color(135, 206, 235)
    slateblue = Color(106, 90, 205)
    slategray = Color(112, 128, 144)
    snow = Color(255, 250, 250)
    springgreen = Color(0, 255, 127)
    steelblue = Color(70, 130, 180)
    tan = Color(210, 180, 140)
    teal = Color(0, 128, 128)
    thistle = Color(216, 191, 216)
    tomato = Color(255, 99, 7)
    turquoise = Color(64, 224, 208)
    violet = Color(238, 130, 238)
    wheat = Color(245, 222, 179)
    white = Color(255, 255, 255)
    whitesmoke = Color(245, 245, 245)
    yellow = Color(255, 255, 0)
    yellowgreen = Color(154, 205, 50)
    # Non-HTML, supplementary colors
    transparent = Color(0, 0, 0, 0)


ColorDef: TypeAlias = (
    Color | tuple[int, int, int] | tuple[int, int, int, int] | list[int] | str | None
)


def parse_color(value: ColorDef) -> Color:
    """
    Parse color.
    Options:
        parse_color((r, g, b))
        parse_color((r, g, b, a))
        parse_color([r, g, b])
        parse_color([r, g, b, a])
        parse_color("#<hex>")
            Examples:
                #0bffff (alpha value will be 255)
                #0bff1bee (alpha value will be 0xee)
        parse_color("<color_name>")
            For valid color names, see members of class Colors
        parse_color(Color)
            Return given color.
    :return: a Color object.
    """
    if isinstance(value, Color):
        return value
    elif isinstance(value, (tuple, list)):
        if len(value) not in (3, 4):
            raise ValueError(
                f"Color tuple/list must have 3 or 4 values, got {len(value)}"
            )
        return Color(*value)
    elif isinstance(value, str):
        if not value:
            raise ValueError("Expected a non-empty string color")
        if value[0] == "#":
            hex_code = value[1:]
            if len(hex_code) > 8:
                raise ValueError(
                    f"Too long color hex (at most 8 digits expected): {value}"
                )
            color_integer = int(hex_code, 16)
            v1 = color_integer >> (3 * 8)
            v2 = (color_integer & 0xFFFFFF) >> (2 * 8)
            v3 = (color_integer & 0xFFFF) >> (1 * 8)
            v4 = color_integer & 0xFF
            if v1:
                r, g, b, a = v1, v2, v3, v4
            else:
                r, g, b, a = v2, v3, v4, 255
            return Color(r, g, b, a)
        else:
            color = getattr(Colors, value, None)
            if not isinstance(color, Color):
                raise ValueError(f"Unknown color name: {value}")
            return color
    elif value is None:
        return Colors.transparent
    else:
        raise ValueError(f"Unsupported color definition: {type(value).__name__}")


class _ColorToString:
    __slots__ = ["_color_to_name"]

    def __init__(self):
        self._color_to_name: dict[tuple[int, int, int, int], str] = {}
        for name in dir(Colors):
            if "a" <= name[0] <= "z":
                val = getattr(Colors, name)
                if isinstance(val, Color):
                    self._color_to_name[(val.r, val.g, val.b, val.a)] = name

    def __call__(self, color: Color) -> str:
        color_tuple = (color.r, color.g, color.b, color.a)
        if color_tuple not in self._color_to_name:
            name = "#"
            values = color_tuple if color.a != 255 else (color.r, color.g, color.b)
            for value in values:
                assert isinstance(value, int)
                assert 0 <= value < 256
                name += hex(value)[2:].ljust(2, "0")
            self._color_to_name[color_tuple] = name
        return self._color_to_name[color_tuple]


stringify_color = _ColorToString()
