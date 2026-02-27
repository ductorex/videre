import flet as ft

_irrelevant_ = [
    ft.ButtonStyle,
    ft.Control,
    ft.CrossAxisAlignment,
    ft.FontWeight,
    ft.IconButton,
    ft.ListView,
    ft.MainAxisAlignment,
    ft.MarkdownExtensionSet,
    ft.MenuStyle,
    ft.RoundedRectangleBorder,
    ft.ScrollMode,
    ft.TextStyle,
]

_to_do_ = [ft.MenuBar, ft.MenuItemButton, ft.SubmenuButton]
_doing_ = [
    ft.Markdown
    # Notes:
    # A Text can set color, strong, italic and underline.
    # Markdown not yet parsed.
    # Full rich text not yet available.
]
_done_ = [
    ft.AlertDialog,
    ft.Checkbox,
    ft.Column,
    ft.Container,
    ft.ElevatedButton,
    ft.FilePicker,
    ft.Image,
    ft.ProgressBar,
    ft.ProgressRing,
    ft.Radio,
    ft.RadioGroup,
    ft.Row,
    ft.Text,
    ft.Dropdown,  # <select>options...</select>
    ft.TextField,
]
