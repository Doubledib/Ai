"""Cut a window and render it as a 1080x1920 short: blurred fill, burned captions, source credit."""
from __future__ import annotations

import subprocess
from pathlib import Path

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _ass_time(t: float) -> str:
    h, rem = divmod(max(t, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def write_captions(words, start: float, end: float, path: Path, per_line: int = 3) -> bool:
    """Punchy 3-word captions as an .ass file, timed relative to the clip start."""
    ws = [(s - start, e - start, t) for s, e, t in words if s >= start and e <= end and t]
    if not ws:
        return False
    head = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, Bold, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV\n"
        "Style: Cap,DejaVu Sans,84,&H00FFFFFF,&H00000000,1,1,6,0,2,60,60,520\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Text\n")
    lines = []
    for i in range(0, len(ws), per_line):
        chunk = ws[i:i + per_line]
        text = " ".join(t for _, _, t in chunk).upper().replace("{", "").replace("}", "")
        lines.append(f"Dialogue: 0,{_ass_time(chunk[0][0])},{_ass_time(chunk[-1][1])},Cap,{text}")
    path.write_text(head + "\n".join(lines) + "\n")
    return True


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "").replace("%", "\\%")


def render_short(src: str | Path, start: float, end: float, out: str | Path,
                 credit: str = "", words=None) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    dur = min(end - start, 59.0)   # stay inside every platform's short-form limit
    vf = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=24:2[bgb];"
        "[fg]scale=1080:-2[fgs];"
        "[bgb][fgs]overlay=(W-w)/2:(H-h)/2[v0]")
    last = "v0"
    if credit:
        vf += (f";[{last}]drawtext=fontfile={FONT}:text='{_esc('clip via ' + credit)}':fontsize=40:"
               "fontcolor=white@0.85:borderw=3:bordercolor=black@0.7:x=(w-text_w)/2:y=h-200[v1]")
        last = "v1"
    cap = out.with_suffix(".ass")
    if words and write_captions(words, start, start + dur, cap):
        vf += f";[{last}]ass='{_esc(str(cap))}'[v2]"
        last = "v2"
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{start}", "-t", f"{dur}", "-i", str(src),
           "-filter_complex", vf, "-map", f"[{last}]", "-map", "0:a?",
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-r", "30",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    return out


def probe(path: str | Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:format=duration", "-of", "csv=p=0:s=,", str(path)],
        check=True, capture_output=True, text=True).stdout.split()
    w, h = r[0].split(",")[:2]
    return {"width": int(w), "height": int(h), "duration": float(r[1])}
