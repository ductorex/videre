import logging

import videre
from videre.layouts.div import Div
from videre.testing.utils import LOREM_IPSUM
from videre.windowing.windowutils import OnEvent

logger = logging.getLogger(__name__)


class Demo:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)

        self.window = videre.Window()
        self.work = videre.Container(padding=videre.Padding.all(10), weight=1)

        self.demos = self.on_demo
        buttons = [
            videre.Button(str(title), on_click=self._demo_from(function))
            for title, function in self.demos.items()
        ]
        self.window.controls = [
            videre.Column(
                [
                    videre.Text("Demo of many things", strong=False),
                    videre.Row([videre.Button("clear", on_click=self.clear)]),
                    videre.Row(buttons),
                    self.work,
                ]
            )
        ]

    def _demo_from(self, function):
        def wrapper(*args):
            ret = function(self, *args)
            if ret is not None:
                self.work.control = ret

        return wrapper

    def start(self):
        first_demo_title = list(self.demos.keys())[0]
        first_demo = self.demos[first_demo_title]
        # self._demo_from(self.on_text_input)()
        self._demo_from(first_demo)()
        self.window.run()

    def clear(self, *args):
        self.work.control = None

    on_demo = OnEvent[str]()

    @on_demo("clipboard")
    def demo_clipboard(self, *args):
        sentence = "☐ ☑ ✅ ✓ ✔ 🗸 🗹 ◉ ○"
        text = videre.Text(sentence)

        def to_clipboard(*args):
            self.window.set_clipboard(sentence)

        def from_clipboard(*args):
            text.text = self.window.get_clipboard()

        return videre.Column(
            [
                videre.Button("To clipboard", on_click=to_clipboard),
                videre.Button("From clipboard", on_click=from_clipboard),
                text,
            ],
            space=10,
        )

    @on_demo("context button")
    def on_context_button(self, *args):
        total = 10
        actions = [f"Item {i + 1}/{total}" for i in range(total)]

        return videre.Column(
            [videre.ContextButton("context button", actions=actions)],
            expand_horizontal=False,
        )

    @on_demo("text input")
    def on_text_input(self, *args):
        return videre.Container(videre.TextInput(), padding=videre.Padding.all(20))

    @on_demo("nested_scrollview")
    def on_nested_scrollview(self, *args):
        inner_content = videre.Column(
            [videre.Text(f"Inner {i}", size=14) for i in range(10)]
        )
        inner_scroll = videre.ScrollView(inner_content)

        outer_content = videre.Column(
            [
                videre.Text("Before inner scroll", size=16),
                videre.Container(inner_scroll, width=150, height=100),
                videre.Text("After inner scroll", size=16),
            ]
            + [videre.Text(f"Outer item {i}", size=14) for i in range(10)]
        )

        outer_scroll = videre.ScrollView(outer_content)
        return outer_scroll

    @on_demo("radio")
    def on_radio(self, *args):
        radio1 = videre.Radio(value="one")
        radio2 = videre.Radio(value="two")
        radio3 = videre.Radio(value="three")
        text = videre.Text("none")

        def on_change(group: videre.RadioGroup):
            text.text = group.value

        group = videre.RadioGroup(
            videre.Column([radio1, radio2, radio3, text]), on_change=on_change
        )
        return group

    @on_demo("label")
    def on_label(self, *args):
        checkbox = videre.Checkbox()
        label = videre.Label(checkbox, text="control checkbox!", height_delta=0)
        return videre.Row(
            [label, videre.Container(checkbox, padding=videre.Padding(left=10))]
        )

    @on_demo("scroll view")
    def on_scroll_view(self, *args):
        return videre.ScrollView(
            videre.Column(
                [
                    videre.Text("Hello"),
                    videre.Text("World"),
                    videre.Text("This is a test"),
                    videre.Text("of the scroll view"),
                    videre.Text("in the videre_examples demo."),
                    videre.Row(
                        [
                            videre.Text("Hello"),
                            videre.Text("World"),
                            videre.ScrollView(
                                videre.Text(LOREM_IPSUM, wrap=videre.TextWrap.WORD),
                                # wrap_horizontal=True,
                                # wrap_vertical=False,
                                weight=1,
                                key="scrollview2",
                            ),
                        ]
                    ),
                    videre.Text(LOREM_IPSUM, wrap=videre.TextWrap.WORD),
                ]
            ),
            wrap_horizontal=True,
            wrap_vertical=False,
            key="scrollview1",
        )

    @on_demo("container")
    def on_container(self, *args):
        text = (
            "Hello, World! How are you? I'm fine, thanks, and you? I am ok, too, dear!"
        )
        parameters = {
            "padding": videre.Padding.all(50),
            "border": videre.Border.all(1),
            "weight": 1,
        }
        return videre.Column(
            [
                videre.Container(
                    videre.Text(text),
                    **parameters,
                    horizontal_alignment=videre.Alignment.START,
                ),
                videre.Container(
                    videre.Text(text),
                    **parameters,
                    horizontal_alignment=videre.Alignment.CENTER,
                ),
                videre.Container(
                    videre.Text(text),
                    **parameters,
                    horizontal_alignment=videre.Alignment.END,
                ),
                Div(
                    videre.Text(
                        text, wrap=videre.TextWrap.WORD, align=videre.TextAlign.CENTER
                    ),
                    weight=1,
                ),
                videre.Button(text, weight=1),
                Div(
                    videre.Text(
                        text, wrap=videre.TextWrap.WORD, align=videre.TextAlign.CENTER
                    ),
                    style={"default": {"square": True}},
                    weight=1,
                ),
                videre.Button(text, square=True, weight=1),
            ]
        )

    @on_demo("Animator, progressing and progress bars")
    def on_demo_animator(self, *args):
        label = videre.Text("Frame 0")

        def on_label_frame(w, f):
            label.text = f"Frame {f}"

        pb = videre.ProgressBar()

        def on_pb_frame(w, f):
            pb.value = (f % 31) / 30

        aw = videre.Animator(label, on_frame=on_label_frame)
        ap = videre.Animator(pb, on_frame=on_pb_frame, fps=30)
        return videre.Column(
            [
                aw,
                ap,
                videre.Progressing(),
                videre.ProgressBar(),
                videre.ProgressBar(),
                videre.ProgressBar(0.1),
                videre.ProgressBar(0.5),
                videre.ProgressBar(0.8),
                videre.ProgressBar(0.9),
                videre.ProgressBar(1),
            ]
        )

    @on_demo("fancybox")
    def on_demo_fancybox(self, *args):
        self.window.set_fancybox(
            videre.ScrollView(
                videre.Column([videre.Text(f"Item {i + 1}") for i in range(100)])
            ),
            buttons=[videre.Button("yes"), videre.Button("NO!")],
        )

    @on_demo("alert")
    def on_alert(self, *args):
        self.window.alert("You have an alert")

    @on_demo("choose file")
    def on_choose_file(self, *args):
        text = videre.Text("no file chosen ...")

        def on_click(*args):
            path = videre.Dialog.select_file_to_open()
            if path:
                text.text = "File chosen: " + path
            else:
                text.text = "You have not chosen any file!"

        button = videre.Button("Choose file", on_click=on_click)
        return videre.Column([button, text])

    @on_demo("dropdown")
    def on_dropdown(self, *args):
        return videre.Column(
            [
                videre.TextInput(),
                videre.Container(background_color="green", weight=0.5),
                videre.TextInput(),
                videre.Row(
                    [
                        videre.Dropdown([1, 2, 3, 4, 100_000]),
                        videre.Container(
                            Div(videre.Text("Hello", height_delta=0)),
                            padding=videre.Padding(left=10),
                        ),
                        videre.Container(
                            videre.Button("Hello"), padding=videre.Padding(left=10)
                        ),
                    ]
                ),
                videre.Container(
                    videre.Text(
                        "Hello, World! How are you? ", wrap=videre.TextWrap.WORD
                    ),
                    background_color="yellow",
                    weight=0.5,
                    horizontal_alignment=videre.Alignment.CENTER,
                    padding=videre.Padding.all(50),
                ),
                videre.Button("Hello, World! How are you? ", weight=0.5),
            ]
        )


def main():
    Demo().start()


if __name__ == "__main__":
    main()
