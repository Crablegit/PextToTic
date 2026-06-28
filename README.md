# PextToTic

A web application that converts images or text into **LaTeX**, **HTML**, or **Markdown** using Google's Gemini AI. The application also supports **PDF generation from LaTeX** via XeLaTeX.

<img width="1913" height="923" alt="image" src="https://github.com/user-attachments/assets/350d69bd-3e6f-456f-9cc4-58598e627648" />

from this

<img width="1016" height="604" alt="Screenshot 2026-06-28 at 10 02 32" src="https://github.com/user-attachments/assets/fa21b837-0607-4b3a-bd00-6b5d2c5c1934" />

to this

![Uploading Screenshot 2026-06-28 at 10.12.26.png…]()


## Features

- Upload an image and convert it into:
  - LaTeX
  - HTML
  - Markdown
- Enter text directly for conversion
- Syntax-highlighted source code output
- Live preview
- Light/Dark mode
- English/Vietnamese interface
- Optional PDF export for LaTeX output

---

# Prerequisites

Before running the project, make sure you have:

- Python 3.10 or newer
- A Google Gemini API Key
- XeLaTeX installed (required for PDF export)

---

# Getting a Gemini API Key

1. Go to:

   https://aistudio.google.com/

2. Sign in with your Google account.

3. Create a new API key.

4. Open `app.py` and replace:

```python
genai.configure(api_key="YOUR_API_KEY")
```

with:

```python
genai.configure(api_key="PASTE_YOUR_API_KEY_HERE")
```

---

# Installation

## Windows

### Update pip

```cmd
python -m pip install --upgrade pip
```

### Install Python dependencies

```cmd
pip install Flask google-generativeai Pillow Werkzeug
```

### Install MiKTeX (required for PDF export)

Requires Chocolatey:

```cmd
choco install miktex -y
```

### Verify installation

```cmd
python --version
pip --version
xelatex --version
```

---

## macOS

### Install Python

```bash
brew install python
```

### Update pip

```bash
python3 -m pip install --upgrade pip
```

### Install Python dependencies

```bash
pip3 install Flask google-generativeai Pillow Werkzeug
```

### Install MacTeX (required for PDF export)

```bash
brew install --cask mactex
```

### Verify installation

```bash
python3 --version
pip3 --version
xelatex --version
```

---

# Running the Application

Start the Flask server:

### Windows

```cmd
python app.py
```

### macOS

```bash
python3 app.py
```

You should see something similar to:

```text
* Running on http://127.0.0.1:5000
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

---


# Required Python Packages

```text
Flask
google-generativeai
Pillow
Werkzeug
```

---

# PDF Export Notes

PDF export relies on:

```text
XeLaTeX
```

If the "Compile to PDF" option does not work:

1. Verify that XeLaTeX is installed.
2. Run:

```bash
xelatex --version
```

3. Ensure XeLaTeX is available in your system PATH.

---

# Troubleshooting

### ModuleNotFoundError

Install missing packages:

```bash
pip install Flask google-generativeai Pillow Werkzeug
```

### API Key Error

Make sure:

- Your Gemini API key is valid.
- The key is correctly inserted into `app.py`.
- Gemini API access is enabled for your Google account.

### PDF Export Fails

Check that:

```bash
xelatex --version
```

returns a valid version number.

If not, reinstall MiKTeX (Windows) or MacTeX (macOS).

---

# License

This project is provided as-is for educational and personal use.
