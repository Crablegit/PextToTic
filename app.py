# Tên file: app.py
import os
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
import subprocess
from PIL import Image

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Cấu hình API Key (sẽ lấy từ biến môi trường khi chạy)
genai.configure(api_key="ENTERYOUR_API_KEY_HERE")
model = genai.GenerativeModel('gemini-2.5-flash')

def get_system_prompt(format_type):
    base_prompt = f"""Bạn là một kỹ sư phần mềm chuyên nghiệp chuyên soạn thảo văn bản theo yêu cầu từ những hình ảnh hoặc dạng text raw có sẵn. 
    Nhiệm vụ của bạn là chuyển đổi hình ảnh hoặc văn bản được cung cấp sang định dạng {format_type}.
    
BẮT BUỘC THỰC HIỆN BƯỚC KIỂM TRA LẠI (SELF-CHECK) TRƯỚC KHI TRẢ VỀ KẾT QUẢ:
"""
    if format_type == "LaTeX":
        base_prompt += """
1. [ ] Đã import đủ thư viện toán chưa? (amsmath, amssymb, mathtools).
2. [ ] Đã import đủ thư viện bảng biểu chưa? (booktabs, multirow, array).
3. [ ] ĐÃ ĐẢM BẢO THƯ VIỆN TIẾNG VIỆT CHƯA? Bắt buộc phải có:
   \\usepackage[utf8]{inputenc}
   \\usepackage[T5]{fontenc}
   \\usepackage[vietnamese]{babel}
4. [ ] Cấu trúc chuẩn có \\begin{document} và \\end{document} không?
"""
    elif format_type == "HTML":
        base_prompt += """
1. [ ] Đã khai báo <!DOCTYPE html> và thẻ <html lang="vi"> chưa?
2. [ ] ĐÃ ĐẢM BẢO HIỂN THỊ TIẾNG VIỆT CHƯA? Bắt buộc phải có <meta charset="UTF-8">.
3. [ ] Đã import Bootstrap 5 (CDN) và MathJax (để hiển thị toán) chưa?
"""
    elif format_type == "Markdown":
        base_prompt += """
1. [ ] Đã dùng các chuẩn thẻ Markdown cho tiêu đề, bảng biểu chưa?
2. [ ] Công thức toán phải bọc trong $ (inline) hoặc $$ (block).
3. [ ] Đảm bảo giữ nguyên tiếng Việt có dấu chuẩn xác.
"""
    
    base_prompt += "\nCHỈ TRẢ VỀ DUY NHẤT MÃ NGUỒN (RAW CODE), KHÔNG KÈM GIẢI THÍCH, KHÔNG BỌC TRONG ```."
    return base_prompt

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/convert', methods=['POST'])
def convert():
    try:
        text_input = request.form.get('text', '')
        format_choice = request.form.get('format', 'LaTeX')
        export_pdf = request.form.get('export_pdf') == 'true'
        
        contents = [get_system_prompt(format_choice)]
        
        # Xử lý file ảnh
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
                file.save(filepath)
                img = Image.open(filepath)
                contents.append(img)
                
        if text_input.strip():
            contents.append(f"Dữ liệu cần xử lý: {text_input}")
            
        if len(contents) == 1:
            return jsonify({'error': 'Vui lòng cung cấp ảnh hoặc văn bản!'}), 400

        # Gọi API
        response = model.generate_content(contents)
        raw_code = response.text.strip()
        
        pdf_url = ""
        # Xử lý xuất PDF nếu là LaTeX
        if export_pdf and format_choice == 'LaTeX':
            tex_file = os.path.join(app.config['UPLOAD_FOLDER'], 'output.tex')
            pdf_file = os.path.join(app.config['UPLOAD_FOLDER'], 'output.pdf')
            with open(tex_file, 'w', encoding='utf-8') as f:
                f.write(raw_code)
            
            # Biên dịch sang PDF bằng xelatex (hỗ trợ tiếng Việt tốt nhất)
            subprocess.run(['xelatex', '-output-directory', app.config['UPLOAD_FOLDER'], tex_file], capture_output=True)
            if os.path.exists(pdf_file):
                pdf_url = "/api/download/output.pdf"

        return jsonify({
            'code': raw_code,
            'format': format_choice,
            'pdf_url': pdf_url
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>')
def download(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)