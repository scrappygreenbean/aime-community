"""
AIME Video Toolkit — FastAPI Server
POST /create-video  →  Claude generates scene content → HyperFrames renders → MP4 URL returned
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

import anthropic
import boto3
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="AIME Video Toolkit", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
R2_ACCOUNT_ID     = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID  = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_KEY     = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET         = os.getenv("R2_BUCKET", "aime-videos")
R2_PUBLIC_URL     = os.getenv("R2_PUBLIC_URL", "")  # e.g. https://cdn.gotaime.com

VIDEOS_DIR = Path("generated_videos")
VIDEOS_DIR.mkdir(exist_ok=True)

SKILLS_DIR = Path(".agents/skills/product-launch-video/scripts")


# ── Request / response models ──────────────────────────────────────────────────

class VideoRequest(BaseModel):
    prompt: str
    duration: int = 30          # seconds (default 30)
    aspect: str = "9:16"        # 9:16 | 16:9 | 1:1


class VideoResponse(BaseModel):
    video_id: str
    url: str
    duration: int
    message: str


# ── Claude: generate scene content ────────────────────────────────────────────

SCENE_SYSTEM = """You are AIME's video script writer. Turn a one-line topic into a punchy
JSON scene list for a short-form social media video. Gold-on-black luxury brand.
Real estate and insurance agent audience. Confident, irreverent tone.

Output ONLY valid JSON — an array of scene objects:
[
  {
    "id": "01-hook",
    "type": "hook",
    "duration": 3,
    "headline": "Short punchy headline (max 8 words)",
    "body": "Supporting line (max 12 words)",
    "emoji": "🚫",
    "style": "slam"   // slam | reveal | list | cta
  },
  ...
]

Style guide:
- slam: big text slams in, high energy (use for hook and gut-punch)
- reveal: elegant scale-in (use for product/brand moments)
- list: staggered list items appear one by one
- cta: final CTA with button

Always include: one hook, one or two pain/problem scenes, one product reveal,
one or two feature scenes, one comparison or proof scene, one CTA.
Total scenes: 6-8. Total duration: must equal the requested duration in seconds.
"""

def generate_scenes(prompt: str, duration: int) -> list[dict]:
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SCENE_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Topic: {prompt}\nRequested duration: {duration} seconds"
        }]
    )
    raw = msg.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── HyperFrames: build & render ────────────────────────────────────────────────

FRAME_TEMPLATE = """\
<!doctype html>
<html>
<head><meta charset="UTF-8"/></head>
<body>
<template>
  <style>
    .{cid}-root {{
      position: relative;
      width: {w}px;
      height: {h}px;
      background: #050505;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      font-family: 'Montserrat', sans-serif;
      padding: 60px 50px;
      box-sizing: border-box;
    }}
    .{cid}-emoji {{
      font-size: 100px;
      margin-bottom: 24px;
      opacity: 0;
    }}
    .{cid}-headline {{
      font-family: 'Playfair Display', serif;
      font-weight: 900;
      font-size: {hfont}px;
      line-height: 1.1;
      text-align: center;
      background: {hcolor};
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 20px;
      opacity: 0;
    }}
    .{cid}-body {{
      font-family: 'Montserrat', sans-serif;
      font-weight: 600;
      font-size: {bfont}px;
      color: #A89F8C;
      text-align: center;
      line-height: 1.5;
      max-width: {maxw}px;
      opacity: 0;
    }}
    .{cid}-btn {{
      margin-top: 36px;
      background: linear-gradient(135deg,#F1D18A 0%,#D4AF37 45%,#B8932E 100%);
      color: #000;
      font-family: 'Montserrat', sans-serif;
      font-weight: 900;
      font-size: {btnfont}px;
      text-transform: uppercase;
      letter-spacing: 1px;
      border-radius: 14px;
      padding: 20px 48px;
      border: none;
      opacity: 0;
      box-shadow: 0 0 50px rgba(212,175,55,0.45);
    }}
    .{cid}-url {{
      margin-top: 16px;
      font-size: 22px;
      color: #A89F8C;
      font-weight: 600;
      letter-spacing: 2px;
      opacity: 0;
    }}
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Montserrat:wght@600;700;800;900&display=swap');
  </style>

  <div class="{cid}-root" data-composition-id="{cid}" data-width="{w}" data-height="{h}">
    {emoji_el}
    <div class="{cid}-headline" id="{cid}-hl">{headline}</div>
    <div class="{cid}-body"    id="{cid}-bd">{body}</div>
    {btn_el}
  </div>

  <script>
    window.__timelines = window.__timelines || {{}};
    const tl = gsap.timeline({{ paused: true }});
    {anim}
    window.__timelines["{cid}"] = tl;
  </script>
</template>
</body>
</html>
"""

def _anim(cid: str, style: str, has_emoji: bool, has_btn: bool) -> str:
    lines = []
    t = 0.0
    if has_emoji:
        lines.append(f'tl.from(".{cid}-emoji", {{scale:0.2,opacity:0,duration:0.5,ease:"elastic.out(1,0.5)"}},{t});')
        t += 0.4
    if style == "slam":
        lines.append(f'tl.from("#{cid}-hl",{{scale:1.8,opacity:0,duration:0.5,ease:"elastic.out(1,0.5)"}},{t});')
    elif style == "reveal":
        lines.append(f'tl.from("#{cid}-hl",{{scale:0.7,opacity:0,duration:0.7,ease:"power4.out"}},{t});')
    else:
        lines.append(f'tl.from("#{cid}-hl",{{y:30,opacity:0,duration:0.5,ease:"power3.out"}},{t});')
    t += 0.4
    lines.append(f'tl.from("#{cid}-bd",{{y:20,opacity:0,duration:0.5,ease:"power3.out"}},{t});')
    if has_btn:
        t += 0.4
        lines.append(f'tl.from("#{cid}-btn",{{scale:0.5,opacity:0,duration:0.5,ease:"elastic.out(1,0.4)"}},{t});')
        t += 0.3
        lines.append(f'tl.from("#{cid}-url",{{y:10,opacity:0,duration:0.4,ease:"power3.out"}},{t});')
        # Pulse the button after entrance
        lines.append(f'tl.to("#{cid}-btn",{{scale:1.04,duration:0.6,ease:"sine.inOut",yoyo:true,repeat:-1}},">+0.2");')
    # Camera drift
    lines.append(f'tl.from(".{cid}-root",{{scale:0.97,duration:{3},ease:"none"}},0);')
    return "\n    ".join(lines)


def build_frame(scene: dict, canvas_w: int, canvas_h: int, out_dir: Path) -> Path:
    cid   = scene["id"].replace("-", "_")
    style = scene.get("style", "reveal")
    emoji = scene.get("emoji", "")
    is_cta = scene.get("type") == "cta"

    # Responsive font sizes
    is_vertical = canvas_h > canvas_w
    hfont  = 90 if is_vertical else 120
    bfont  = 42 if is_vertical else 54
    btnfont = 34 if is_vertical else 44
    maxw   = canvas_w - 100

    hcolor = ("linear-gradient(135deg,#F1D18A 0%,#D4AF37 45%,#B8932E 100%)"
              if style in ("reveal", "cta") else "#ECE7DA")

    emoji_el = f'<div class="{cid}-emoji">{emoji}</div>' if emoji else ""
    btn_el   = (f'<button class="{cid}-btn" id="{cid}-btn">Learn More</button>\n'
                f'    <div class="{cid}-url">Gotaime.com</div>') if is_cta else ""

    anim = _anim(cid, style, bool(emoji), is_cta)

    html = FRAME_TEMPLATE.format(
        cid=cid, w=canvas_w, h=canvas_h,
        hfont=hfont, bfont=bfont, btnfont=btnfont, maxw=maxw,
        hcolor=hcolor,
        headline=scene["headline"],
        body=scene.get("body", ""),
        emoji_el=emoji_el, btn_el=btn_el,
        anim=anim,
    )
    path = out_dir / f"{scene['id']}.html"
    path.write_text(html)
    return path


def build_index(scenes: list[dict], canvas_w: int, canvas_h: int, project_dir: Path) -> None:
    total = sum(s.get("duration", 3) for s in scenes)
    clips = []
    t = 0
    for i, s in enumerate(scenes):
        cid  = s["id"].replace("-", "_")
        dur  = s.get("duration", 3)
        src  = f"compositions/frames/{s['id']}.html"
        clip = (
            f'<div id="clip-{i}" '
            f'data-composition-id="{cid}" '
            f'data-composition-src="{src}" '
            f'data-start="{t}" data-duration="{dur}" '
            f'data-track-index="1" '
            f'data-width="{canvas_w}" data-height="{canvas_h}"></div>'
        )
        clips.append(clip)
        t += dur

    html = f"""\
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width={canvas_w}, height={canvas_h}"/>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    html,body{{width:{canvas_w}px;height:{canvas_h}px;overflow:hidden;background:#050505}}
  </style>
</head>
<body>
  <div id="root"
       data-composition-id="main"
       data-width="{canvas_w}"
       data-height="{canvas_h}"
       data-duration="{total}">
    {"    ".join(clips)}
  </div>
  <script>
    window.__timelines = window.__timelines || {{}};
    window.__timelines["main"] = gsap.timeline({{paused:true}});
  </script>
</body>
</html>"""
    (project_dir / "index.html").write_text(html)


def render_video(project_dir: Path, video_id: str) -> Path:
    out_path = VIDEOS_DIR / f"{video_id}.mp4"
    result = subprocess.run(
        ["npx", "--yes", "hyperframes@0.7.0", "render", "--output", str(out_path.absolute())],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Render failed:\n{result.stderr}")
    return out_path


# ── R2 upload (optional) ───────────────────────────────────────────────────────

def upload_to_r2(file_path: Path, key: str) -> str:
    endpoint = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_KEY,
    )
    s3.upload_file(
        str(file_path),
        R2_BUCKET,
        key,
        ExtraArgs={"ContentType": "video/mp4"},
    )
    return f"{R2_PUBLIC_URL.rstrip('/')}/{key}"


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    ui = Path("video_ui/index.html")
    if ui.exists():
        return ui.read_text()
    return "<h1>AIME Video Toolkit</h1><p>Place video_ui/index.html to load the UI.</p>"


@app.get("/health")
async def health():
    return {"status": "ok", "anthropic_key": bool(ANTHROPIC_API_KEY)}


@app.post("/create-video", response_model=VideoResponse)
async def create_video(req: VideoRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=422, detail="prompt must not be empty")

    video_id = str(uuid.uuid4())[:8]

    # Parse canvas dimensions
    ratio_map = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}
    canvas_w, canvas_h = ratio_map.get(req.aspect, (1080, 1920))

    # Step 1 — Generate scenes via Claude
    try:
        scenes = generate_scenes(req.prompt, req.duration)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Claude returned invalid JSON: {e}")

    # Step 2 — Build HyperFrames project
    project_dir = Path(tempfile.mkdtemp(prefix="aime-video-"))
    frames_dir  = project_dir / "compositions" / "frames"
    frames_dir.mkdir(parents=True)

    # Copy package.json so hyperframes CLI works
    pkg = {"name": "aime-video", "version": "1.0.0", "scripts": {
        "render": "hyperframes render --output renders/video.mp4"
    }}
    (project_dir / "package.json").write_text(json.dumps(pkg, indent=2))
    (project_dir / "hyperframes.json").write_text(json.dumps({
        "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
        "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}
    }, indent=2))

    for scene in scenes:
        build_frame(scene, canvas_w, canvas_h, frames_dir)

    build_index(scenes, canvas_w, canvas_h, project_dir)

    # Step 3 — Render to MP4
    try:
        mp4_path = render_video(project_dir, video_id)
    except Exception as e:
        shutil.rmtree(project_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(project_dir, ignore_errors=True)

    # Step 4 — Upload to R2 or serve locally
    if all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_KEY]):
        try:
            url = upload_to_r2(mp4_path, f"videos/{video_id}.mp4")
        except Exception as e:
            url = f"/video/{video_id}"
    else:
        url = f"/video/{video_id}"

    return VideoResponse(
        video_id=video_id,
        url=url,
        duration=req.duration,
        message="Video generated successfully",
    )


@app.get("/video/{video_id}")
async def serve_video(video_id: str):
    path = VIDEOS_DIR / f"{video_id}.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(path, media_type="video/mp4")


# Mount UI static files (CSS/JS) if present
_ui = Path("video_ui")
if _ui.exists():
    app.mount("/ui", StaticFiles(directory=str(_ui)), name="ui")
