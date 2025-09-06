import base64
import io

from PIL import Image

from albumentations_mcp.server import (
    _load_and_preprocess_from_base64,
    _load_and_preprocess_from_file,
)


def _mk_img(w=1800, h=1200, color=(200, 50, 50)):
    img = Image.new("RGB", (w, h), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return img, buf.getvalue()


def _to_b64(raw):
    return base64.b64encode(raw).decode("ascii")


def test_file_path_resize(tmp_path):
    # make big image
    img, raw = _mk_img()
    p = tmp_path / "big.jpg"
    p.write_bytes(raw)
    b64, err = _load_and_preprocess_from_file(str(p))
    assert err is None
    assert isinstance(b64, str) and len(b64) > 0


def test_base64_resize_permissive():
    _, raw = _mk_img()
    b64_in = _to_b64(raw)
    b64_out, err = _load_and_preprocess_from_base64(b64_in)
    assert err is None
    assert isinstance(b64_out, str) and len(b64_out) > 0


def test_base64_invalid():
    b64, err = _load_and_preprocess_from_base64("not_base64")
    assert err and "B64_INVALID" in err
