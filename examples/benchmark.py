import base64
import time
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Callable

import pyperclip
from PIL import Image

import videre
from videre.testing.step_window import StepWindow
from videre.widgets.widget import Widget

LIGHT_GREY = videre.parse_color((240, 240, 240))


class PerfCounter:
    __slots__ = ("_ns_start", "_ns_end")

    def __init__(self):
        self._ns_start = self._ns_end = 0

    def __enter__(self):
        self._ns_start = time.perf_counter_ns()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ns_end = time.perf_counter_ns()

    @property
    def nanoseconds(self) -> float:
        return self._ns_end - self._ns_start

    @property
    def microseconds(self) -> float:
        return (self._ns_end - self._ns_start) / 1000


class VideoPattern:
    __slots__ = ("_video_id", "_now")

    def __init__(self, video_id: int) -> None:
        self._video_id = video_id
        self._now = datetime(
            2020,
            (video_id % 12) + 1,
            (video_id % 28) + 1,
            microsecond=(video_id % 1_000_000),
            tzinfo=UTC,
        )

    def __eq__(self, other):
        return self.filename == other.filename

    @property
    def filename(self) -> str:
        return f"/path/to/this/video/{self.video_id}.mkv"

    @property
    def file_size(self) -> int:
        return (self.video_id + 1) * (1024**2)

    @property
    def errors(self) -> list[str]:
        return [f"error {i + 1}" for i in range(self.video_id)]

    @property
    def video_id(self) -> int:
        return self._video_id

    @property
    def mtime(self) -> float:
        return self._now.timestamp()

    @property
    def date_entry_modified(self) -> datetime:
        return self._now + timedelta(seconds=self.video_id)

    @property
    def date_entry_opened(self) -> datetime:
        return self.date_entry_modified + timedelta(seconds=self.video_id)

    @property
    def audio_bit_rate(self) -> int:
        return (self.video_id + 1) * 1000

    @property
    def audio_bits(self) -> int:
        return 16 if not self.video_id % 2 else 32

    @property
    def audio_codec(self) -> str:
        return f"ac_{self.video_id}"

    @property
    def audio_codec_description(self) -> str:
        return f"audio codec for {self.video_id}"

    @property
    def bit_depth(self) -> int:
        return 8 if self.video_id % 2 else 10

    @property
    def channels(self) -> int:
        return 2 if self.video_id % 2 else 6

    @property
    def container_format(self) -> str:
        return "mkv"

    @property
    def device_name(self) -> str:
        return "mydisk"

    @property
    def driver_id(self) -> int:
        return 0

    @property
    def duration(self) -> float:
        return timedelta(
            hours=(self.video_id % 24), seconds=(self.video_id % 60)
        ).total_seconds()

    @property
    def duration_time_base(self) -> int:
        return 1

    @property
    def frame_rate_den(self) -> int:
        return 1

    @property
    def frame_rate_num(self) -> int:
        return 30

    @property
    def height(self) -> int:
        return 720

    @property
    def meta_title(self) -> str:
        return f"meta title {self.video_id}"

    @property
    def sample_rate(self) -> int:
        return 44100

    @property
    def similarity_id(self) -> int | None:
        return None

    @property
    def video_codec(self) -> str:
        return "hevc"

    @property
    def video_codec_description(self) -> str:
        return "video codec for " + str(self.video_id)

    @property
    def width(self) -> int:
        return 1280

    @property
    def discarded(self) -> bool:
        return False

    @property
    def unreadable(self) -> bool:
        return False

    @property
    def found(self) -> bool:
        return True

    @property
    def with_thumbnails(self) -> bool:
        return True

    @property
    def audio_languages(self) -> list[str]:
        return ["fr", "en", "jp"]

    @property
    def subtitle_languages(self) -> list[str]:
        return ["ar", "du", "pc"]

    @property
    def properties(self) -> dict[str, list]:
        return {
            "property 1": [f"value for property 1: {self.video_id}"],
            "property 2": [f"value for property 2: {self.video_id}"],
            "property 3": [f"value for property 3: {self.video_id}"],
        }

    @property
    def moves(self) -> list:
        return []

    @property
    def thumbnail(self) -> bytes:
        img = Image.new(
            "RGB", (300, 200), color=(self.video_id, self.video_id, self.video_id)
        )
        byte_stream = BytesIO()
        img.save(byte_stream, format="PNG")
        return byte_stream.getvalue()

    @property
    def watched(self) -> bool:
        return bool(self.video_id % 2)

    @property
    def move_id(self):
        return None

    @property
    def thumbnail_base64(self):
        # Return thumbnail as HTML, base64 encoded image data
        data: bytes = self.thumbnail
        return base64.b64encode(data).decode() if data else None

    @property
    def thumbnail_path(self):
        thumbnail = self.thumbnail_base64
        return f"data:image/jpeg;base64,{thumbnail}" if thumbnail else None

    @property
    def readable(self) -> bool:
        return not self.unreadable

    @property
    def not_found(self) -> bool:
        return not self.found

    @property
    def without_thumbnails(self) -> bool:
        return not self.with_thumbnails

    @property
    def date(self) -> datetime:
        return datetime.fromtimestamp(self.mtime)

    @property
    def bit_rate(self) -> float:
        return (
            self.file_size * self.duration_time_base / self.duration
            if self.duration
            else 0
        )

    @property
    def length(self) -> float:
        return self.duration * 1000000 / self.duration_time_base

    @property
    def raw_microseconds(self):
        return self.duration * 1000000 / self.duration_time_base

    @property
    def size(self) -> int:
        return self.file_size

    @property
    def frame_rate(self) -> float:
        return self.frame_rate_num / (self.frame_rate_den or 1)

    @property
    def extension(self) -> str:
        return "extension"

    @property
    def file_title(self):
        return "this is a file title"

    @property
    def title(self) -> str:
        return self.meta_title or self.file_title

    @property
    def audio_bit_rate_kbps(self) -> int:
        return round(self.audio_bit_rate / 1000)

    @property
    def similarity(self) -> str:
        return (
            "not compared"
            if self.similarity_id is None
            else ("none" if self.similarity_id < 0 else str(self.similarity_id))
        )

    @property
    def meta_title_numeric(self) -> str:
        return self.meta_title

    @property
    def file_title_numeric(self) -> str:
        return self.file_title

    @property
    def title_numeric(self) -> str:
        return self.meta_title_numeric if self.meta_title else self.file_title_numeric

    @property
    def filename_numeric(self) -> str:
        return self.filename

    @property
    def year(self) -> int:
        return self.date.year

    @property
    def day(self) -> int:
        return self.date.day

    @property
    def disk(self):
        return self.driver_id

    @property
    def filename_length(self) -> int:
        return len(self.filename)

    @property
    def size_length(self) -> tuple:
        return (self.size, self.length)


class DialogRenameVideo(videre.Column):
    __wprops__ = {}
    __slots__ = ("entry",)

    def __init__(self, video: VideoPattern) -> None:
        filename = videre.Text(
            str(video.filename), wrap=videre.TextWrap.CHAR, strong=True
        )
        self.entry = videre.TextInput(str(video.file_title))
        super().__init__(
            [filename, self.entry],
            horizontal_alignment=videre.Alignment.CENTER,
            expand_horizontal=True,
            space=10,
        )

    def get_value(self) -> str:
        return self.entry.value


class VideoView(videre.Container):
    __wprops__ = {}
    __slots__ = (
        "_video",
        "_menu",
        "_text_path",
        "_label_title",
        "_hold_file_title",
        "_similarity",
    )
    __BACKGROUND_EVEN__ = videre.parse_color((240, 240, 240))

    def __init__(self, video: VideoPattern, index: int, selected: bool = False):
        self._video = video
        checkbox = videre.Checkbox(checked=selected, on_change=self._on_select_video)
        properties = video.properties
        self._menu = videre.ContextButton(
            "[*]", actions=self._get_menu_actions(video), square=True
        )
        self._label_title = videre.Label(
            for_button=checkbox, text=str(video.title), strong=True
        )
        self._hold_file_title = videre.Container(
            videre.Text(str(video.file_title)) if video.meta_title else None
        )
        self._text_path = videre.Text(
            str(video.filename),
            wrap=videre.TextWrap.CHAR,
            color=videre.Colors.lightgray if video.watched else videre.Colors.blue,
            strong=video.watched,
        )
        self._similarity = videre.Text(f"Similarity: {video.similarity}")
        thumbnail = self._get_thumbnail()
        attributes = videre.Column(
            [
                videre.Row(
                    [self._menu, checkbox, self._label_title],
                    vertical_alignment=videre.Alignment.CENTER,
                    space=5,
                ),
                self._hold_file_title,
                self._text_path,
                videre.Text(
                    f"{video.extension.upper()} {video.size} / "
                    f"{video.container_format} /"
                    f" ({video.video_codec}, {video.audio_codec}) / "
                    f"bite rate: {video.bit_rate}/s",
                    wrap=videre.TextWrap.WORD,
                ),
                videre.Text(
                    f"{video.length} | "
                    f"{video.width} x {video.height} @ {round(video.frame_rate)} fps, "
                    f"{video.bit_depth} bits | "
                    f"{video.sample_rate} Hz x {video.audio_bits or '32?'} bits "
                    f"({video.channels} channels), "
                    f"{video.audio_bit_rate_kbps} Kb/s",
                    wrap=videre.TextWrap.WORD,
                ),
                videre.Text(
                    f"{video.date} | "
                    f"(entry) {video.date_entry_modified} | "
                    f"(opened) {video.date_entry_opened}",
                    wrap=videre.TextWrap.WORD,
                ),
                videre.Text(
                    f"Audio: {', '.join(video.audio_languages or ['(none)'])} | "
                    f"Subtitles: {', '.join(video.subtitle_languages or ['(none)'])}"
                ),
                self._similarity,
            ]
            + (
                [
                    videre.Text("PROPERTIES", strong=True),
                    *(
                        videre.Row(
                            [
                                videre.Text(f"{name}:", strong=True),
                                *(
                                    videre.Container(
                                        videre.Text(str(value), italic=True),
                                        background_color=LIGHT_GREY,
                                        padding=videre.Padding.axis(2, 10),
                                    )
                                    for value in values
                                ),
                            ],
                            space=5,
                            vertical_alignment=videre.Alignment.CENTER,
                        )
                        for name, values in properties.items()
                    ),
                ]
                if properties
                else []
            ),
            space=2,
            weight=1,
        )
        super().__init__(
            videre.Row([thumbnail, attributes], space=6),
            padding=videre.Padding.axis(vertical=10),
            background_color=(self.__BACKGROUND_EVEN__ if index % 2 == 1 else None),
        )

    def _get_thumbnail(self) -> videre.Container:
        return videre.Container(
            videre.Picture(self._video.thumbnail),
            width=300,
            horizontal_alignment=videre.Alignment.CENTER,
        )

    def _get_menu_actions(self, video: VideoPattern) -> list[tuple[str, Callable]]:
        actions = []
        if video.found:
            actions.extend(
                [
                    (
                        f"Mark as {'unwatched' if video.watched else 'watched'}",
                        self._action_change_watched,
                    ),
                    ("Open file", self._action_open_file),
                ]
            )
            actions.extend(
                [("Open from local server", self._action_open_from_local_server)]
            )
            actions.extend(
                [("Open containing folder", self._action_open_containing_folder)]
            )
        if video.meta_title:
            actions.extend([("Copy meta title", self._action_copy_meta_title)])
        actions.extend(
            [
                ("Copy file title", self._action_copy_file_title),
                ("Copy path", self._action_copy_path),
                ("Copy video ID", self._action_copy_video_id),
                ("Rename video", self._action_rename),
                ("Reset similarity", self._action_reset_similarity),
            ]
        )
        return actions

    def _action_change_watched(self):
        pass

    def _action_open_file(self):
        pass

    def _action_open_from_local_server(self):
        pass

    def _action_open_containing_folder(self):
        pass

    def _action_copy_meta_title(self):
        self._action_copy("meta_title")

    def _action_copy_file_title(self):
        self._action_copy("file_title")

    def _action_copy_path(self):
        self._action_copy("filename", "path")

    def _action_copy_video_id(self):
        self._action_copy("video_id", "video ID")

    def _action_copy(self, field: str, title=None):
        value = getattr(self._video, field)
        pyperclip.copy(str(value))

    def _action_rename(self):
        dialog = DialogRenameVideo(self._video)
        button = videre.FancyCloseButton(
            "rename", on_click=self._on_rename, data=dialog
        )
        self.get_window().set_fancybox(dialog, title="Rename Video", buttons=[button])

    def _on_rename(self, widget: Widget):
        pass

    def _action_reset_similarity(self):
        self.get_window().confirm(
            videre.ScrollView(
                videre.Column(
                    [
                        videre.Text(
                            "Are you sure you want to reset similarity for this video?",
                            wrap=videre.TextWrap.WORD,
                            strong=True,
                        ),
                        videre.Text(
                            "Video will then be re-compared at next similarity search",
                            wrap=videre.TextWrap.WORD,
                        ),
                        videre.Text(
                            str(self._video.filename),
                            wrap=videre.TextWrap.CHAR,
                            align=videre.TextAlign.CENTER,
                            color=videre.Colors.red,
                        ),
                        self._get_thumbnail(),
                    ],
                    space=10,
                    horizontal_alignment=videre.Alignment.CENTER,
                ),
                wrap_horizontal=True,
            ),
            "Reset similarity",
            on_confirm=self._on_reset_similarity,
        )

    def _on_reset_similarity(self):
        pass

    def _on_select_video(self, checkbox: Widget):
        pass


def main():
    with StepWindow() as window:
        window.controls = [
            videre.ScrollView(
                videre.Column(
                    [VideoView(VideoPattern(i), i, selected=False) for i in range(100)]
                ),
                wrap_horizontal=True,
                weight=4,
            )
        ]
        for i in range(5):
            with PerfCounter() as pc:
                window.render()
            print(f"Time {i + 1}:", timedelta(microseconds=pc.microseconds))


if __name__ == "__main__":
    main()
