"""Renderiza stdout de execução real, sem inventar linhas de terminal.

O PNG é uma visualização literal do log capturado, não foto de emulador GUI.
Requer Pillow (somente esta ferramenta). Não altera resultados publicados.
"""
from pathlib import Path
import subprocess
import sys
import json
import hashlib
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def main():
    command = [sys.executable, '-m', 'src.cli', 'report']
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    text = completed.stdout
    output = ROOT/'evidence'
    output.mkdir(exist_ok=True)
    (output/'terminal-stdout.txt').write_text(text)
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
    font = ImageFont.truetype(font_path, 21)
    lines = text.splitlines()
    width = max(1200, int(max(font.getlength(line) for line in lines))+90)
    image = Image.new('RGB', (width, 110+34*len(lines)), '#111722')
    draw = ImageDraw.Draw(image)
    draw.text((35, 20), 'STDOUT REAL | python -m src.cli report | visualização literal do log', font=font, fill='#74dccc')
    for i, line in enumerate(lines):
        draw.text((35, 85+34*i), line, font=font, fill='#e8edf5')
    image.save(output/'terminal.png')
    (output/'capture.json').write_text(json.dumps({'command':['python','-m','src.cli','report'], 'exit_code':completed.returncode,
         'stdout_sha256':hashlib.sha256(text.encode()).hexdigest(),
         'representation':'Literal rendering of real process stdout; not a GUI emulator screenshot.'},indent=2)+'\n')
    print('evidence/terminal.png: captured stdout rendered without edits')


if __name__=='__main__':
    main()
