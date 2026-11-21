"""Fail when a hand-typed number appears in the text of the paper.

Every number must come from generated/numbers.tex (macros written by scripts/make_assets.py) or from the generated
tables. This script scans main.tex and sections/*.tex, removes what may legitimately contain digits (comments,
citation and reference keys, file names, URLs, display equations, names of models and software), and reports every
digit that is left, with file and line. It also checks that every macro used in the text is defined in
generated/numbers.tex or in the preamble.

Usage: python3 scripts/check_numbers.py [paper_dir]     (exit code 1 on any finding)
"""
import re
import sys
from pathlib import Path

paper = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
files = [paper / "main.tex", paper / "author_preprint.tex"] + sorted((paper / "sections").glob("*.tex"))

# Names that contain digits but are not numbers of this study.
NAMES = [r"OpenVLA-7B", r"Llama~2", r"Llama 2", r"DINOv2", r"RT-1", r"RT-2", r"Lanczos3", r"bfloat16", r"L1",
         r"\\pizero", r"\\pifive", r"A/A",
         r"\\\{0, 1\\\}", r"\[-1, 1\]"]  # the last two: notation for a binary outcome and a scaled range
# Commands whose arguments are keys, paths or lengths, not prose.
KEY_CMDS = r"(?:cite[tp]?\*?|ref|eqref|label|input|include|includegraphics|url|href|path|bibliography|bibliographystyle|" \
           r"usepackage|documentclass|setlength|hypersetup|newcolumntype|texttt|pdftrailerid)"
DISPLAY_ENVS = ("equation", "equation*", "align", "align*")

defined = set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", (paper / "generated/numbers.tex").read_text()))
for f in files:
    defined |= set(re.findall(r"\\(?:new|provide)command\{\\([A-Za-z]+)\}", f.read_text()))

findings = []
used = set()
for f in files:
    text = f.read_text()
    # remove display equations, keeping line count
    for env in DISPLAY_ENVS:
        pat = re.compile(r"\\begin\{" + re.escape(env) + r"\}.*?\\end\{" + re.escape(env) + r"\}", re.S)
        text = pat.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    lines = text.splitlines()
    doc_start = next((i + 1 for i, l in enumerate(lines) if l.startswith("\\begin{document}")), 0)
    for no, line in enumerate(lines, 1):
        line = re.sub(r"(?<!\\)%.*", "", line)                       # comments
        if f.name == "main.tex" and no < doc_start and not line.strip().startswith("\\title"):
            continue                                                  # preamble of main.tex: packages and options
        used |= set(re.findall(r"\\([A-Z][A-Za-z]+)", line))
        line = re.sub(r"\\" + KEY_CMDS + r"(\[[^\]]*\])?\{[^}]*\}", " ", line)
        line = re.sub(r"\\(?:begin|end)\{[^}]*\}(\{[^}]*\})?(\[[^\]]*\])?", " ", line)
        for n in NAMES:
            line = re.sub(n, " ", line)
        line = re.sub(r"\\[A-Za-z]+", " ", line)                     # macros (names have no digits)
        for m in re.finditer(r"\d+", line):
            findings.append(f"{f.relative_to(paper)}:{no}: hand-typed number '{m.group(0)}' in: {line.strip()[:120]}")

LATEX_CMDS = {"The", "This", "In", "A", "If"}  # not macros; guards against prose matched by the pattern above
missing = sorted(u for u in used - defined if u[0].isupper() and u not in LATEX_CMDS and not u.startswith(("Tex", "LaTeX")))
known_latex = {"Delta", "Var", "Binomial"}
missing = [m for m in missing if m not in known_latex]
for m in missing:
    findings.append(f"undefined number macro \\{m} (not in generated/numbers.tex)")

for x in findings:
    print(x)
print(f"check_numbers: {len(findings)} finding(s) in {len(files)} files")
sys.exit(1 if findings else 0)
