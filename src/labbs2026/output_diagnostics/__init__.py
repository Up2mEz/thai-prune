"""Why an OCR output scores the way it does — shared by tracks A-D.

T1's registered normalization (`labbs2026.thai_marks.normalize`) stays the
primary metric everywhere, for comparability. This package adds, as
sensitivity measures only, a structure-aware normalization and a per-item
error taxonomy, so that a bad score can be traced to formatting, looping,
omission or genuine misreading instead of being read as "the model cannot
read".
"""
