# app.py — google-genai SDK mới, fix RECITATION bằng prompt + retry
# Cài đặt: pip install flask google-genai werkzeug
# Chạy:    export GEMINI_API_KEY=AIza...   &&   python app.py

import os, traceback, logging, time, base64, subprocess
from google import genai
from google.genai import types as genai_types
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s — %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

# ── Flask ─────────────────────────────────────────────────────────────────────
app = Flask(__name__)

@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

@app.route('/api/<path:p>', methods=['OPTIONS'])
def handle_options(p):
    return '', 204

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER']      = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Gemini ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = "APIHERE"
if not GEMINI_API_KEY:
    raise RuntimeError(
        "Chưa set GEMINI_API_KEY!\n"
        "  Mac/Linux: export GEMINI_API_KEY=AIza...\n"
        "  Windows:   set GEMINI_API_KEY=AIza..."
    )

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL  = 'gemini-2.5-flash'
log.info(f"✅ Gemini client ready — key prefix: {GEMINI_API_KEY[:8]}...")


# ── Prompt ────────────────────────────────────────────────────────────────────
def get_prompt(fmt: str) -> str:
    """
    Prompt rõ ràng là TASK CHUYỂN ĐỔI FORMAT, không phải copy nội dung.
    Điều này giúp tránh Gemini kích hoạt RECITATION filter.
    """
    p = (
        f"Nhiệm vụ của bạn là PHÂN TÍCH cấu trúc và layout của tài liệu trong ảnh, "
        f"sau đó TỰ VIẾT LẠI toàn bộ nội dung đó dưới dạng {fmt} hợp lệ.\n"
        f"Đây là công việc chuyển đổi định dạng (format conversion), "
        f"KHÔNG phải sao chép (copy) nội dung gốc.\n"
        f"Hãy diễn giải lại theo cách của bạn, giữ đúng ý nghĩa và cấu trúc.\n"
    )
    if fmt == 'LaTeX':
        p += (
            "Yêu cầu LaTeX:\n"
            "- \\documentclass{article}\n"
            "- \\usepackage[utf8]{inputenc}\n"
            "- \\usepackage[T5]{fontenc}\n"
            "- \\usepackage[vietnamese]{babel}\n"
            "- \\usepackage{amsmath,amssymb}\n"
            "- Có đầy đủ \\begin{document} ... \\end{document}\n"
        )
    elif fmt == 'HTML':
        p += (
            "Yêu cầu HTML:\n"
            "- <!DOCTYPE html> và <meta charset='UTF-8'>\n"
            "- Bootstrap 5 CDN\n"
            "- MathJax CDN nếu có công thức toán\n"
        )
    elif fmt == 'Markdown':
        p += "Yêu cầu Markdown: dùng $...$ cho inline math, $$...$$ cho block math, giữ nguyên tiếng Việt.\n"

    p += "\nCHỈ TRẢ RAW CODE, KHÔNG GIẢI THÍCH, KHÔNG BỌC TRONG ```."
    return p


# ── Gemini call với retry khi gặp RECITATION ─────────────────────────────────
GEMINI_CONFIG = genai_types.GenerateContentConfig(
    temperature=0.4,          # tăng nhẹ temperature để tránh RECITATION
    max_output_tokens=8192,
    safety_settings=[
        genai_types.SafetySetting(category='HARM_CATEGORY_HARASSMENT',        threshold='BLOCK_NONE'),
        genai_types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH',       threshold='BLOCK_NONE'),
        genai_types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
        genai_types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
    ]
)

def call_gemini(contents: list, fmt: str):
    """
    Gọi Gemini, retry tối đa 2 lần nếu RECITATION.
    Lần retry dùng prompt khác nhấn mạnh hơn vào việc TỰ VIẾT LẠI.
    Returns: (code_text, finish_reason)
    """
    retry_prompt = (
        f"Hãy tự tạo code {fmt} mô tả lại nội dung trong ảnh theo cách diễn giải của riêng bạn. "
        f"Không cần giống từng chữ, chỉ cần đúng cấu trúc và ý nghĩa. "
        f"Đây là bài tập viết lại (rewrite), không phải trích dẫn.\n"
        + get_prompt(fmt)
    )

    for attempt in range(3):
        log.info(f"  [GEMINI] Attempt {attempt + 1}/3 ...")

        # Lần retry: thay prompt đầu tiên bằng retry_prompt mạnh hơn
        call_contents = contents if attempt == 0 else [retry_prompt] + contents[1:]

        # Tăng temperature mỗi lần retry để phá vỡ pattern RECITATION
        cfg = genai_types.GenerateContentConfig(
            temperature=0.4 + attempt * 0.3,   # 0.4 → 0.7 → 1.0
            max_output_tokens=8192,
            safety_settings=GEMINI_CONFIG.safety_settings
        )

        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=call_contents,
                config=cfg
            )
        except Exception as e:
            log.error(f"  [GEMINI] Exception attempt {attempt+1}: {e}")
            if attempt == 2:
                raise
            time.sleep(1)
            continue

        # Đọc finish_reason
        finish_reason = ''
        try:
            finish_reason = str(resp.candidates[0].finish_reason)
        except Exception:
            pass

        log.info(f"  [GEMINI] finish_reason={finish_reason!r}")

        # Đọc text
        code = None
        try:
            code = resp.text
        except Exception:
            try:
                code = ''.join(
                    p.text for p in resp.candidates[0].content.parts
                    if hasattr(p, 'text') and p.text
                )
            except Exception:
                pass

        if code and code.strip():
            log.info(f"  [GEMINI] OK — {len(code)} chars ✓")
            return code.strip(), finish_reason

        # RECITATION hoặc rỗng → retry
        if 'RECITATION' in finish_reason:
            log.warning(f"  [GEMINI] RECITATION ở attempt {attempt+1}, retry...")
            time.sleep(0.5)
            continue

        # Lý do khác mà rỗng → không retry
        log.error(f"  [GEMINI] Rỗng vì {finish_reason!r}, dừng retry")
        return None, finish_reason

    return None, 'RECITATION_MAX_RETRY'


# ── Error handler ─────────────────────────────────────────────────────────────
@app.errorhandler(Exception)
def on_error(e):
    log.error(traceback.format_exc())
    return jsonify({'error': str(e), 'type': type(e).__name__}), 500


# ── /api/convert ──────────────────────────────────────────────────────────────
@app.route('/api/convert', methods=['POST'])
def convert():
    log.info("═══ POST /api/convert ═══")

    is_multipart = request.content_type and 'multipart/form-data' in request.content_type

    if is_multipart:
        fmt        = request.form.get('format', 'LaTeX')
        text       = (request.form.get('text') or '').strip()
        export_pdf = request.form.get('export_pdf', 'false').lower() == 'true'
        img_file   = request.files.get('image')
    else:
        body       = request.get_json(force=True, silent=True) or {}
        fmt        = body.get('format', 'LaTeX')
        text       = body.get('text', '').strip()
        export_pdf = bool(body.get('export_pdf', False))
        img_file   = None

    log.info(f"  fmt={fmt!r}  text_len={len(text)}  has_image={img_file is not None}  pdf={export_pdf}")

    contents = []

    # CP1 — prompt
    contents.append(get_prompt(fmt))
    log.info(f"  [CP1] Prompt ✓")

    # CP2 — ảnh
    if img_file and img_file.filename:
        log.info(f"  [CP2] Đọc ảnh: '{img_file.filename}' ({img_file.content_type})")
        img_bytes = img_file.read()
        log.info(f"  [CP2] {len(img_bytes)} bytes")

        if len(img_bytes) == 0:
            return jsonify({'error': 'File ảnh rỗng 0 bytes'}), 400

        ext_low  = os.path.splitext(img_file.filename)[1].lower()
        mime_map = {'.jpg':'image/jpeg', '.jpeg':'image/jpeg',
                    '.png':'image/png',  '.gif':'image/gif',
                    '.webp':'image/webp','.bmp':'image/bmp'}
        mime = (img_file.content_type
                if img_file.content_type and img_file.content_type.startswith('image/')
                else mime_map.get(ext_low, 'image/jpeg'))
        log.info(f"  [CP2] mime={mime!r}")

        img_part = genai_types.Part.from_bytes(data=img_bytes, mime_type=mime)
        contents.append(img_part)
        log.info("  [CP2] Part ảnh OK ✓")
    else:
        log.info("  [CP2] Không có ảnh")

    # CP3 — text
    if text:
        contents.append(f"Nội dung cần xử lý:\n{text}")
        log.info(f"  [CP3] {len(text)} chars ✓")

    if len(contents) <= 1:
        return jsonify({'error': 'Chưa có input (ảnh hoặc text)'}), 400

    # CP4 — gọi Gemini (có retry)
    t0 = time.time()
    try:
        code, finish_reason = call_gemini(contents, fmt)
    except Exception as e:
        log.error(f"  [CP4] Exception: {e}")
        return jsonify({'error': f'Gemini lỗi: {e}', 'type': type(e).__name__}), 500

    elapsed = round(time.time() - t0, 1)
    log.info(f"  [CP4] {elapsed}s total")

    if not code:
        if 'RECITATION' in finish_reason:
            msg = (
                "Gemini từ chối xử lý ảnh này vì nhận dạng nội dung có bản quyền (RECITATION).\n"
                "Thử lại với ảnh khác, hoặc nhập text trực tiếp vào ô bên dưới."
            )
        else:
            msg = f'Gemini trả về rỗng (finish_reason={finish_reason})'
        return jsonify({'error': msg}), 500

    # Bóc ``` nếu model vẫn bọc
    if code.startswith('```'):
        lines = code.splitlines()
        end   = -1 if lines[-1].strip() == '```' else len(lines)
        code  = '\n'.join(lines[1:end]).strip()
    log.info(f"  [OUT] Code cuối: {len(code)} chars ✓")

    # PDF
    pdf_url = pdf_error = ''
    if export_pdf and fmt == 'LaTeX':
        tex_path = os.path.join(UPLOAD_FOLDER, 'output.tex')
        pdf_path = os.path.join(UPLOAD_FOLDER, 'output.pdf')
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(code)
        r = subprocess.run(
            ['xelatex', '-interaction=nonstopmode', '-output-directory', UPLOAD_FOLDER, tex_path],
            capture_output=True, timeout=60
        )
        if os.path.exists(pdf_path):
            pdf_url = '/api/download/output.pdf'
        else:
            pdf_error = f"xelatex lỗi (exit {r.returncode})"
            log.error(f"  [PDF] {pdf_error}\n{r.stderr.decode('utf-8','replace')[-500:]}")

    log.info("  ✓ Xong")
    return jsonify({
        'code': code, 'format': fmt,
        'pdf_url': pdf_url, 'pdf_error': pdf_error, 'elapsed': elapsed
    })


# ── /api/download ─────────────────────────────────────────────────────────────
@app.route('/api/download/<name>')
def download(name):
    path = os.path.join(UPLOAD_FOLDER, secure_filename(name))
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return jsonify({'error': '404'}), 404


# ── /api/ping ─────────────────────────────────────────────────────────────────
@app.route('/api/ping')
def ping():
    log.info("GET /api/ping")
    gemini_test = gemini_error = None
    try:
        r = client.models.generate_content(model=MODEL, contents="Say exactly: PONG")
        gemini_test = r.text.strip()
        log.info(f"  ping OK: {gemini_test!r}")
    except Exception as e:
        gemini_error = str(e)
        log.error(f"  ping fail: {e}")
    return jsonify({
        'status': 'ok',
        'api_key_prefix': GEMINI_API_KEY[:8] + '...',
        'model': MODEL,
        'gemini_test': gemini_test or 'error',
        'gemini_error': gemini_error or ''
    })


# ── / ─────────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    log.info(f"🚀 http://0.0.0.0:5000  |  UPLOAD_FOLDER: {UPLOAD_FOLDER}")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
