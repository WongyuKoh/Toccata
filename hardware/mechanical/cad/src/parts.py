"""Part registry shared by every generator.

A Part is one physical thing in the instrument (one instance, WORLD coordinates, assembled pose).
Printed parts also say how they lie on the bed; identical printed parts share `print_key`, so the
print folder gets one STL per distinct shape with the total quantity.

World coordinates: x across (0 = A0 left boundary), y from the white-key front lip (+ away from the
player), z from the desk; mm.
"""
from dataclasses import dataclass, field
from typing import Optional

from manifold3d import Manifold


@dataclass
class Part:
    id: str                       # ascii, unique per instance, e.g. "O3-KEY-E"
    name_ko: str                  # real part name (Korean, as in the parts list / purchase list)
    name_en: str
    kind: str                     # print | bought | plywood | electronics | consumable
    group: str                    # assembly group, e.g. "O3 건반", "뒷바 가운데 유닛"
    solid: Manifold               # world coordinates, assembled pose
    color: str = "#cccccc"
    material: str = ""
    # printing
    print_key: Optional[str] = None       # same key = same printed shape (one STL, qty summed)
    print_name: Optional[str] = None      # file stem for the print STL, e.g. "백건_E"
    print_folder: Optional[str] = None    # e.g. "01_건반"
    print_solid: Optional[Manifold] = None  # already oriented on the bed (z=0); None = not printed
    print_note: str = ""                  # orientation / supports / post-processing
    dims: list = field(default_factory=list)  # [(label, value_mm, source)] shown in the README + annotated STL
    source: str = ""
    note: str = ""


COLORS = {
    "white_key": "#f4f1ea",
    "black_key": "#1d1d1f",
    "lever": "#7fb77e",
    "frame": "#9aa3ad",
    "sensorbar": "#6b8fb5",
    "padbar": "#c9a86a",
    "curtain": "#50565e",
    "plug": "#e0a040",
    "steel": "#5a5f66",
    "stainless": "#c0c6cc",
    "felt": "#b0413e",
    "pad": "#e8c547",
    "spring": "#d9d9d9",
    "magnet": "#8a8f98",
    "pcb_perf": "#c8a45a",
    "pcb_green": "#2f7d4f",
    "pcb_blue": "#2a5caa",
    "module": "#264b7a",
    "plywood": "#d9b98b",
    "printed_body": "#7d858f",
    "speaker": "#2b2b2b",
    "rubber": "#333333",
    "cable": "#3a3a3a",
    "metal": "#b8b8b8",
}
