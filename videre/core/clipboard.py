import logging

import pyperclip

logger = logging.getLogger(__name__)


class Clipboard:
    __slots__ = ()

    @classmethod
    def get_clipboard(cls) -> str:
        try:
            text = pyperclip.paste()
            logger.debug(f"Got clipboard text: {text!r}")
            return text
        except Exception as e:
            logger.warning(f"Failed to get clipboard text: {e}")
            return ""

    @classmethod
    def set_clipboard(cls, text: str):
        try:
            pyperclip.copy(text)
            logger.debug(f"Copied text to clipboard: {text!r}")
        except Exception as e:
            logger.warning(f"Failed to copy text to clipboard: {e}")
