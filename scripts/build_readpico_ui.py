"""Generate Read Pico's 1.5x UI fonts from the existing licensed font sources."""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

Import("env")

project = Path(env.subst("$PROJECT_DIR"))
fonts = project / "lib/EpdFont/builtinFonts"
converter = project / "lib/EpdFont/scripts/fontconvert.py"
outputs = []
upstream_script = converter.parent / "convert-builtin-fonts.sh"
arabic_block = re.search(
    r"ARABIC_INTERVALS=\((.*?)^\)",
    upstream_script.read_text(encoding="utf-8"),
    re.S | re.M,
).group(1)
# Reuse upstream's script coverage, including presentation forms for shaping.
intervals = [
    "0x05D0,0x05EA",
    *re.findall(r"--additional-intervals\s+(0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+)", arabic_block),
]

for size in (15, 18, 22):
    for style in (("Regular",) if size == 22 else ("Regular", "Bold")):
        name = f"readpico_ui{size}_{style.lower()}"
        output = fonts / f"{name}.generated.h"
        sources = [
            fonts / f"source/Ubuntu/Ubuntu-{style}.ttf",
            fonts / f"source/NotoSansHebrew/NotoSansHebrew-{style}.ttf",
            fonts / f"source/NotoSansArabic/NotoSansArabic-{style}.ttf",
            fonts / f"source/Ubuntu/Ubuntu-Vietnamese-{style}.ttf",
        ]
        inputs = [project / "scripts/build_readpico_ui.py", converter, upstream_script, *sources]
        if not output.exists() or output.stat().st_mtime < max(p.stat().st_mtime for p in inputs):
            command = [sys.executable, str(converter), name, str(size), *(str(p) for p in sources)]
            for interval in intervals:
                command += ["--additional-intervals", interval]
            result = subprocess.run(command, check=True, capture_output=True)
            output.write_bytes(result.stdout)
        outputs.append(output.name)

header = fonts / "readpico_ui.generated.h"
content = "#pragma once\n" + "".join(f'#include "{name}"\n' for name in outputs)
if not header.exists() or header.read_text() != content:
    header.write_text(content, encoding="utf-8")

# Follow the built-in font ID scheme without modifying upstream's generated IDs.
menu_font = fonts / "readpico_ui22_regular.generated.h"
menu_id = int(hashlib.sha256(menu_font.read_bytes()).hexdigest(), 16) % (2**32) - (2**31)
ids_header = fonts / "readpico_ui_ids.generated.h"
ids_content = (
    "#pragma once\n"
    f"#define READPICO_HOME_MENU_FONT_ID ({menu_id})\n"
    'static_assert(READPICO_HOME_MENU_FONT_ID != 0, "Font ID collision with sentinel");\n'
)
if not ids_header.exists() or ids_header.read_text() != ids_content:
    ids_header.write_text(ids_content, encoding="utf-8")
