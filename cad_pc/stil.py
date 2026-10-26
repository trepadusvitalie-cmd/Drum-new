"""Culorile și fonturile, după capturile din AutoCAD 2025 (tema întunecată)."""
import sys

TITLU = "#1f242b"; FILE = "#2a3039"; FILA_ACT = "#3b4453"; CORP = "#3b4453"; SEP = "#4b5566"
TEXT = "#e8ebef"; GRI = "#a3abb6"; ESTOMPAT = "#6f7884"; HOVER = "#4b5566"; APASAT = "#56627a"
DESEN = "#212830"; GRILA = "#283039"; GRILA2 = "#2e3742"; CMD = "#c9c9c9"; CMD_TXT = "#2b2b2b"
STARE = "#2a3039"; ACTIV = "#3f6fa8"; ALBASTRU = "#3a8ee6"; ROSU_A = "#c4161c"
SELECT = "#4f8ff7"; GRIP = "#2f6ce0"

F = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"
F_FILA = (F, -12); F_BTN = (F, -12); F_MIC = (F, -12); F_GRUP = (F, -12); F_TITLU = (F, -12)
F_ICON = ("Segoe UI Symbol" if sys.platform == "win32" else "DejaVu Sans", -26)
F_ICON_MIC = ("Segoe UI Symbol" if sys.platform == "win32" else "DejaVu Sans", -14)
F_CMD = ("Consolas" if sys.platform == "win32" else "DejaVu Sans Mono", -12)
