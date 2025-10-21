Place your admin and doctor icon files here.

Recommended filenames:
- admin.png (or .svg)
- doctor.png (or .svg)

Usage in templates:
<img src="{{ url_for('static', filename='icons/admin.png') }}" alt="Admin" class="header-icon">

Notes:
- Keep icons around 64x64 for best results in header components.
- You can use SVG files for crisp scaling.
