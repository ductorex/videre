import pytest

from videre.colors import ColorDef
from videre.testing.utils import HD, SD


def win_parameters(
    *,
    width: int | None = None,
    height: int | None = None,
    background: ColorDef | None = None,
):
    parameters = {}
    if width is not None:
        parameters["width"] = width
    if height is not None:
        parameters["height"] = height
    if background is not None:
        parameters["background"] = background
    return pytest.mark.win_params(parameters)


def win_hd_parameters(*, background: ColorDef | None = None):
    return win_parameters(**HD, background=background)


def win_sd_parameters(*, background: ColorDef | None = None):
    return win_parameters(**SD, background=background)
