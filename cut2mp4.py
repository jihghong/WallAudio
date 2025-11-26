"""
Cut segments from .m4a files into clock-overlay .mp4 clips per time ranges listed
in companion .txt files.

Usage:
    python cut2mp4.py <txt_or_dir> [more txt_or_dir ...]

Behavior:
    - If an arg is a directory: glob all *.txt inside and process each.
    - If an arg is a txt file: process it directly.
    - If an arg path doesn't exist: print a warning and continue.
    - For a txt named abc.txt, expect audio abc.m4a in the same directory.
    - Each line: "HH:MM:SS HH:MM:SS" -> output abc.HH-MM-SS.HH-MM-SS.mp4
    - If output mp4 already exists: warn and skip (do not overwrite).
    - Silent on success; only warnings/errors are printed.
"""

from __future__ import annotations

import configparser
import shlex
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List

# Video / overlay defaults (tweak if needed)
RESOLUTION = "1280x720"
FPS = 1  # one tick per second
# Use Windows path with escaped drive colon so ffmpeg's drawtext parses it correctly.
FONT_FILE = "C\\:/Windows/Fonts/arial.ttf"  # must be a valid font file path for ffmpeg
DATE_FONTSIZE = 52
TIME_FONTSIZE = 96
FONT_COLOR = "white"
BACKGROUND_COLOR = "black"
VIDEO_CRF = 20
VIDEO_PRESET = "medium"
FFMPEG_LOGLEVEL = "error"  # reduce drawtext chatter; was "warning"


def parse_time_flexible(text: str) -> tuple[float, str]:
    """
    Parse time in flexible formats and return (seconds, normalized HH:MM:SS).

    Accepted forms:
        SS
        MM:SS
        HH:MM:SS
    Examples:
        "27:00"   -> 00:27:00
        "3"       -> 00:00:03
        "3:4"     -> 00:03:04
    """
    parts = text.split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        raise ValueError("non-numeric time")

    if len(nums) == 1:
        total = nums[0]
    elif len(nums) == 2:
        total = nums[0] * 60 + nums[1]
    elif len(nums) == 3:
        total = nums[0] * 3600 + nums[1] * 60 + nums[2]
    else:
        raise ValueError("too many components")

    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    norm = f"{h:02d}:{m:02d}:{s:02d}"
    return float(total), norm


def iter_txt_files(arg: Path) -> Iterable[Path]:
    if arg.is_dir():
        yield from sorted(arg.glob("*.txt"))
    elif arg.is_file() and arg.suffix.lower() == ".txt":
        yield arg


def load_extra_args(config_path: Path) -> List[str]:
    """Load optional ffmpeg extra args from a .ini file."""
    if not config_path.exists():
        return []
    cfg = configparser.ConfigParser()
    try:
        cfg.read(config_path, encoding="utf-8")
        val = cfg.get("ffmpeg", "extra_args", fallback="").strip()
    except Exception:
        return []
    return shlex.split(val) if val else []


def parse_recording_start(stem: str) -> datetime:
    """
    Parse filename stem like '2025-11-01_04-00-00' into a naive local datetime.
    The filename time is interpreted as local time (no timezone conversion).
    """
    try:
        return datetime.strptime(stem, "%Y-%m-%d_%H-%M-%S")
    except ValueError as exc:
        raise ValueError(f"stem '{stem}' is not YYYY-MM-DD_HH-MM-SS") from exc


def build_filter(start_dt: datetime) -> str:
    """
    Build the drawtext filter string without deprecated strftime expansion.
    - Date line: static text (date does not change within short clips).
    - Time line: manual HH:MM:SS counter based on filter time t (seconds).
    """
    date_text = start_dt.strftime("%Y-%m-%d")

    start_us = int(start_dt.timestamp() * 1_000_000)

    return (
        "[0:v]"
        f"drawtext=fontfile='{FONT_FILE}':expansion=strftime:basetime={start_us}:"
        f"text='%Y-%m-%d':fontcolor={FONT_COLOR}:fontsize={DATE_FONTSIZE}:"
        "x=(w-text_w)/2:y=(h/2-90),"
        f"drawtext=fontfile='{FONT_FILE}':expansion=strftime:basetime={start_us}:"
        "text='%H\\:%M\\:%S':"
        f"fontcolor={FONT_COLOR}:fontsize={TIME_FONTSIZE}:x=(w-text_w)/2:y=(h/2+10)"
        "[v]"
    )


def process_txt(txt_path: Path, extra_args: List[str]) -> None:
    stem = txt_path.stem
    audio = txt_path.with_name(f"{stem}.m4a")
    if not audio.exists():
        print(f"[missing audio] {audio}")
        return

    try:
        base_dt = parse_recording_start(stem)
    except ValueError as exc:
        print(f"[stem error] {txt_path}: {exc}")
        return

    try:
        lines = txt_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        print(f"[missing txt] {txt_path}")
        return

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            raw_t1, raw_t2 = line.split()
            start_s, t1_norm = parse_time_flexible(raw_t1)
            end_s, t2_norm = parse_time_flexible(raw_t2)
            if end_s <= start_s:
                print(f"[bad range] {txt_path} line '{line}'")
                continue
        except Exception:
            print(f"[parse error] {txt_path} line '{line}'")
            continue

        out_name = f"{stem}.{t1_norm.replace(':','-')}.{t2_norm.replace(':','-')}.mp4"
        out_path = txt_path.with_name(out_name)

        if out_path.exists():
            print(f"[exists] {out_path}")
            continue

        duration = end_s - start_s
        seg_start_dt = base_dt + timedelta(seconds=start_s)
        filter_expr = build_filter(seg_start_dt)

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            FFMPEG_LOGLEVEL,
            "-nostdin",
            "-y",
            # Video source: solid background limited to clip duration
            "-f",
            "lavfi",
            "-t",
            f"{duration:.3f}",
            "-i",
            f"color=size={RESOLUTION}:rate={FPS}:color={BACKGROUND_COLOR}",
            # Audio input trimmed by range
            "-ss",
            t1_norm,
            "-to",
            t2_norm,
            "-i",
            str(audio),
            # Overlay date/time
            "-filter_complex",
            filter_expr,
            # Stream mapping: video from input 0, audio from input 1
            "-map",
            "[v]",
            "-map",
            "1:a:0",
        ]

        if extra_args:
            cmd.extend(extra_args)

        cmd.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                VIDEO_PRESET,
                "-crf",
                str(VIDEO_CRF),
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(out_path),
            ]
        )

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            print(f"[ffmpeg failed] {out_path}")
            continue


def main(argv: list[str]) -> None:
    if not argv:
        print("Usage: python cut2mp4.py <txt_file_or_dir> [more ...]")
        return

    config_path = Path(__file__).with_suffix(".ini")
    extra_args = load_extra_args(config_path)

    for raw in argv:
        path = Path(raw)
        if not path.exists():
            print(f"[missing path] {path}")
            continue

        txts = list(iter_txt_files(path))
        if not txts:
            print(f"[no txt] {path}")
            continue

        for txt in txts:
            process_txt(txt, extra_args)


if __name__ == "__main__":
    main(sys.argv[1:])
