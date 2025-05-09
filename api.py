# pip install Flask Pillow requests
from flask import Flask, request, send_file, abort
from io import BytesIO
from PIL import Image, ImageDraw, ImageFilter
import base64, requests, json, math
import cv2, numpy as np
from PIL import Image

app = Flask(__name__)

def load_img(node):
    data = node["data"]
    if node["source"] == "base64":
        return Image.open(BytesIO(base64.b64decode(data)))
    r = requests.get(data, timeout=15)
    r.raise_for_status()
    return Image.open(BytesIO(r.content))

def apply_overlay(canvas, spec):
    w, h = canvas.size
    dx, dy = spec["paddingFromCenter"]["x"], spec["paddingFromCenter"]["y"]
    cx, cy = w // 2 + dx, h // 2 + dy
    ow, oh = spec["size"]["w"], spec["size"].get("h", spec["size"]["w"])

    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw  = ImageDraw.Draw(layer)

    # background
    bg = spec.get("background")
    if bg:
        bg_img = load_img(bg).convert("RGBA")
        if bg["fit"] == "cover":
            bg_img = bg_img.resize((ow, oh))
        else:                              # contain
            bg_img.thumbnail((ow, oh))
        mask = Image.new("L", (ow, oh), 255)
        layer.paste(bg_img, (cx - ow // 2, cy - oh // 2), mask)

    # border / shape
    if spec["shape"] == "rectangle":
        rect = [cx - ow//2, cy - oh//2, cx + ow//2, cy + oh//2]
        draw.rectangle(rect, outline=spec["border"]["color"],
                       width=spec["border"]["thickness"])
    else:
        r = ow//2
        draw.ellipse([cx-r, cy-r, cx+r, cy+r],
                     outline=spec["border"]["color"],
                     width=spec["border"]["thickness"])

    # shadow / glow
    sh = spec.get("shadow")
    if sh:
        blur_layer = layer.copy().filter(ImageFilter.GaussianBlur(sh["blur"]))
        tint = Image.new("RGBA", canvas.size, sh["color"])
        layer = Image.alpha_composite(blur_layer, tint) if sh["type"]=="glow" else Image.alpha_composite(canvas, layer)
        canvas.alpha_composite(layer, (sh["offset"]["x"], sh["offset"]["y"]))

    canvas.alpha_composite(layer)
def smart_crop(img: Image.Image, target_ratio: float,
               thresh=0.3, min_crop=0.6):
    """Return a PIL image cropped to the target aspect ratio
       using OpenCV fine-grained saliency."""
    w, h = img.size
    orig_area = w * h
    cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGR)
    sal = cv2.saliency.StaticSaliencyFineGrained_create()
    ok, salMap = sal.computeSaliency(cv)
    salMap = (salMap * 255).astype("uint8")
    _, salBin = cv2.threshold(salMap, int(thresh * 255), 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(salBin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return img                          # nothing salient → no crop
    x, y, wBox, hBox = cv2.boundingRect(np.vstack(contours))
    # expand box to desired ratio
    box_ratio = wBox / hBox
    if box_ratio < target_ratio:                   # need wider
        new_w = int(hBox * target_ratio)
        pad = max(0, (new_w - wBox) // 2)
        x, wBox = max(0, x - pad), min(cv.shape[1] - x + pad*2, new_w)
    else:                                          # need taller
        new_h = int(wBox / target_ratio)
        pad = max(0, (new_h - hBox) // 2)
        y, hBox = max(0, y - pad), min(cv.shape[0] - y + pad*2, new_h)
    # enforce minCrop area
    if (wBox * hBox) < orig_area * min_crop:
        return img
    crop = img.crop((x, y, x + wBox, y + hBox))
    return crop

@app.route("/v1/resize", methods=["POST"])
def resize():
    try:
        body = request.get_json(force=True)
        base = load_img(body["baseImage"]).convert("RGBA")
        ratio = body["ratio"]
        if isinstance(ratio, str) and ":" in ratio:
            a, b = map(float, ratio.split(":")); ratio = a / b
        sal = body.get("saliency", {})
        crop = smart_crop(
            base,
            target_ratio=ratio,
            thresh=sal.get("threshold", 0.3),
            min_crop=sal.get("minCrop", 0.6)
        )
        mode = body.get("mode", "cover")
        if mode == "contain":
            crop.thumbnail((base.width, base.height))
        elif mode == "pad":
            pad_w = int(crop.height * ratio)
            bg = Image.new("RGBA", (pad_w, crop.height), (0,0,0,0))
            bg.paste(crop, ((pad_w - crop.width)//2, 0))
            crop = bg
        out = BytesIO()
        fmt = body.get("output", {}).get("format", "jpeg").upper()
        save_kw = {"quality": body["output"].get("quality", 92)} if fmt=="JPEG" else {}
        crop.save(out, format=fmt, **save_kw)
        out.seek(0)
        return send_file(out, mimetype=f"image/{fmt.lower()}")
    except Exception as e:
        abort(400, description=str(e))    

@app.route("/v1/render", methods=["POST"])
def render():
    try:
        spec = request.get_json(force=True)
        canvas = load_img(spec["baseImage"]).convert("RGBA")
        for ov in spec["overlays"]:
            apply_overlay(canvas, ov)
        buf = BytesIO()
        fmt = spec.get("output", {}).get("format", "png").upper()
        canvas.save(buf, format=fmt)
        buf.seek(0)
        return send_file(buf, mimetype=f"image/{fmt.lower()}")
    except Exception as e:
        abort(400, description=str(e))

@app.route("/health")
def health(): return "ok"

if __name__ == "__main__": app.run()