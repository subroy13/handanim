# Hershey font rendering constants for the Math primitive.

# Coordinate units used by the Hershey font library.  A typical glyph
# spans roughly ±12–15 units in both axes.
HERSHEY_FONT_UNITS: float = 30.0

# Standard Hershey font that covers the full printable-ASCII range
# (digits, Latin letters, punctuation).  Must be used for any character
# in the range 0x20–0x7E instead of mathlow/mathupp, because those
# fonts encode *Greek* glyphs at the Latin character positions (e.g.
# 'x' in mathlow renders ξ, not the letter x).
HERSHEY_ASCII_FALLBACK: str = "rowmans"

# Direct mapping: Unicode codepoint → (hershey_font_name, char_in_that_font).
#
# pyhershey encodes Greek glyphs sequentially in the Latin-alphabet positions:
#   greeks  a→α  b→β  c→γ  d→δ  e→ε  f→ζ  g→η  h→θ  i→ι  j→κ  k→λ
#           l→μ  m→ν  n→ξ  o→ο  p→π  q→ρ  r→σ  s→τ  t→υ  u→φ  v→χ
#           w→ψ  x→ω
#   greekc  A→Α  B→Β  C→Γ  D→Δ  E→Ε  F→Ζ  G→Η  H→Θ  I→Ι  J→Κ  K→Λ
#           L→Μ  M→Ν  N→Ξ  O→Ο  P→Π  Q→Ρ  R→Σ  S→Τ  T→Υ  U→Φ  V→Χ
#           W→Ψ  X→Ω
# NOTE: mathlow/mathupp are broken in pyhershey (all chars → charcode 12345).
UNICODE_TO_HERSHEY: dict[int, tuple[str, str]] = {
    # ---- lowercase Greek → greeks -----------------------------------------
    945: ("greeks", "a"),   # α alpha
    946: ("greeks", "b"),   # β beta
    947: ("greeks", "c"),   # γ gamma
    948: ("greeks", "d"),   # δ delta
    949: ("greeks", "e"),   # ε epsilon
    950: ("greeks", "f"),   # ζ zeta
    951: ("greeks", "g"),   # η eta
    952: ("greeks", "h"),   # θ theta
    953: ("greeks", "i"),   # ι iota
    954: ("greeks", "j"),   # κ kappa
    955: ("greeks", "k"),   # λ lambda
    956: ("greeks", "l"),   # μ mu
    957: ("greeks", "m"),   # ν nu
    958: ("greeks", "n"),   # ξ xi
    959: ("greeks", "o"),   # ο omicron
    960: ("greeks", "p"),   # π pi
    961: ("greeks", "q"),   # ρ rho
    962: ("greeks", "r"),   # ς final sigma
    963: ("greeks", "r"),   # σ sigma
    964: ("greeks", "s"),   # τ tau
    965: ("greeks", "t"),   # υ upsilon
    966: ("greeks", "u"),   # φ phi
    967: ("greeks", "v"),   # χ chi
    968: ("greeks", "w"),   # ψ psi
    969: ("greeks", "x"),   # ω omega
    # ---- uppercase Greek → greekc -----------------------------------------
    913: ("greekc", "A"),   # Α Alpha
    914: ("greekc", "B"),   # Β Beta
    915: ("greekc", "C"),   # Γ Gamma
    916: ("greekc", "D"),   # Δ Delta
    917: ("greekc", "E"),   # Ε Epsilon
    918: ("greekc", "F"),   # Ζ Zeta
    919: ("greekc", "G"),   # Η Eta
    920: ("greekc", "H"),   # Θ Theta
    921: ("greekc", "I"),   # Ι Iota
    922: ("greekc", "J"),   # Κ Kappa
    923: ("greekc", "K"),   # Λ Lambda
    924: ("greekc", "L"),   # Μ Mu
    925: ("greekc", "M"),   # Ν Nu
    926: ("greekc", "N"),   # Ξ Xi
    927: ("greekc", "O"),   # Ο Omicron
    928: ("greekc", "P"),   # Π Pi
    929: ("greekc", "Q"),   # Ρ Rho
    931: ("greekc", "R"),   # Σ Sigma
    932: ("greekc", "S"),   # Τ Tau
    933: ("greekc", "T"),   # Υ Upsilon
    934: ("greekc", "U"),   # Φ Phi
    935: ("greekc", "V"),   # Χ Chi
    936: ("greekc", "W"),   # Ψ Psi
    937: ("greekc", "X"),   # Ω Omega
    # ---- common math operators → rowmans ----------------------------------
    8722: ("rowmans", "-"),  # − minus sign
    8901: ("rowmans", "."),  # · dot operator
    215:  ("rowmans", "x"),  # × multiplication (rendered as x)
    247:  ("rowmans", "/"),  # ÷ division
    8260: ("rowmans", "/"),  # ⁄ fraction slash
    # ---- blackboard-bold / double-struck letters → rowmans ----------------
    8477: ("rowmans", "R"),  # ℝ real numbers
    8469: ("rowmans", "N"),  # ℕ natural numbers
    8484: ("rowmans", "Z"),  # ℤ integers
    8474: ("rowmans", "Q"),  # ℚ rationals
    8450: ("rowmans", "C"),  # ℂ complex numbers
}

# Composed glyphs: unicode → list of strokes.
# Each stroke is an ordered list of (x, y) points.
#
# Coordinate convention
# ---------------------
#   • y increases DOWNWARD (screen / Cairo coordinate system)
#   • Shapes are designed to be symmetric about y = 0 so that the
#     bounding-box centre lies at the origin.  This is required for the
#     normalisation in _scale_hershey_opsset to be exact (it scales each
#     point from the raw origin, then translates by the post-scale bbox).
#   • Typical operator size: ±7–9 units in y; tall operators (∑ ∫): ±12–16.
COMPOSED_GLYPHS: dict[int, list[list[tuple[float, float]]]] = {
    # ± plus-minus (177): total y range [-9, 9]
    177: [
        [(-7, -3), (7, -3)],    # + horizontal bar
        [(0, -9), (0, 3)],      # + vertical
        [(-7, 9), (7, 9)],      # − bar below
    ],
    # ≠ not-equal (8800): total y range [-9, 9]
    8800: [
        [(-7, -4), (7, -4)],    # top bar of =
        [(-7, 4),  (7, 4)],     # bottom bar of =
        [(5, -9),  (-5, 9)],    # diagonal slash
    ],
    # ≤ less-than-or-equal (8804): total y range [-10, 10]
    8804: [
        [(7, -10), (-7, -2), (7, 6)],   # < chevron
        [(-7, 10), (7, 10)],            # = line below
    ],
    # ≥ greater-than-or-equal (8805): total y range [-10, 10]
    8805: [
        [(-7, -10), (7, -2), (-7, 6)],  # > chevron
        [(-7, 10),  (7, 10)],           # = line below
    ],
    # ≈ approximately equal (8776): total y range [-8, 8]
    8776: [
        [(-7, -4), (-3, -8), (0, -4), (3, 0),  (7, -4)],
        [(-7,  4), (-3,  0), (0,  4), (3, 8),  (7,  4)],
    ],
    # ∞ infinity (8734): total y range [-5, 5]
    8734: [
        [(0, 0), (-2, -5), (-7, -5), (-10, 0), (-7, 5),
         (-2, 5), (0, 0), (2, -5), (7, -5), (10, 0),
         (7, 5), (2, 5), (0, 0)],
    ],
    # ∇ nabla (8711): total y range [-9, 9]
    8711: [
        [(-9, -9), (9, -9), (0, 9), (-9, -9)],
    ],
    # ∑ summation (8721): total y range [-12, 12]
    8721: [
        [(9, -12), (-7, -12), (7, 0), (-7, 12), (9, 12)],
    ],
    # ∏ product (8719): total y range [-12, 12]
    8719: [
        [(-9, -12), (-9, 12)],
        [( 9, -12), ( 9, 12)],
        [(-9, -12), ( 9, -12)],
    ],
    # ∫ integral (8747): total y range [-16, 16]
    8747: [
        [(3, -12), (0, -16), (-3, -12),
         (-3, 12), (0,  16), ( 3,  12)],
    ],
    # ∂ partial derivative (8706): total y range [-9, 9]
    8706: [
        [(5, -3), (0, -9), (-5, -5), (-5, 4),
         (0, 9), (5, 5), (5, -2), (0, -6), (-5, 0)],
    ],
    # √ square root hook (8730): the overline vinculum is drawn by the rect
    # system in Math.draw(); this glyph is only the hook/tick portion.
    8730: [
        [(-9, 1), (-5, 6), (0, -9), (8, -9)],
    ],
    # → right arrow (8594): total y range [-5, 5]
    8594: [
        [(-10, 0), (10, 0)],
        [(5, -5), (10, 0), (5, 5)],
    ],
    # ← left arrow (8592): total y range [-5, 5]
    8592: [
        [(10, 0), (-10, 0)],
        [(-5, -5), (-10, 0), (-5, 5)],
    ],
    # ↑ up arrow (8593): total y range [-9, 9]
    8593: [
        [(0, 9), (0, -9)],
        [(-5, -4), (0, -9), (5, -4)],
    ],
    # ↓ down arrow (8595): total y range [-9, 9]
    8595: [
        [(0, -9), (0, 9)],
        [(-5, 4), (0, 9), (5, 4)],
    ],
    # ⇒ double right arrow (8658): total y range [-8, 8]
    8658: [
        [(-10, -4), (5, -4), (5, -8), (10, 0), (5, 8), (5, 4), (-10, 4), (-10, -4)],
    ],
    # ∀ for all (8704): total y range [-9, 9]
    8704: [
        [(-8, 9), (0, -9), (8, 9)],
        [(-4, 1), (4, 1)],
    ],
    # ∃ there exists (8707): backwards E, total y range [-9, 9]
    8707: [
        [(7, -9), (7, 9)],
        [(7, -9), (-7, -9)],
        [(7,  0), (-2,  0)],
        [(7,  9), (-7,  9)],
    ],
    # ∈ element of (8712): total y range [-8, 8]
    8712: [
        [(7, -8), (-5, -8), (-8, 0), (-5, 8), (7, 8)],
        [(-8, 0), (4, 0)],
    ],
    # ⊂ subset of (8834): total y range [-8, 8]
    8834: [
        [(7, -8), (-5, -8), (-8, 0), (-5, 8), (7, 8)],
    ],
    # ⊃ superset of (8835): total y range [-8, 8]
    8835: [
        [(-7, -8), (5, -8), (8, 0), (5, 8), (-7, 8)],
    ],
    # ∩ intersection (8745): total y range [-9, 9]
    8745: [
        [(-8, 9), (-8, -3), (-4, -9), (0, -9), (4, -9), (8, -3), (8, 9)],
    ],
    # ∪ union (8746): total y range [-9, 9]
    8746: [
        [(-8, -9), (-8, 3), (-4, 9), (0, 9), (4, 9), (8, 3), (8, -9)],
    ],
    # ≡ identical to / triple bar (8801): total y range [-6, 6]
    8801: [
        [(-7, -6), (7, -6)],
        [(-7,  0), (7,  0)],
        [(-7,  6), (7,  6)],
    ],
    # ∝ proportional to (8733): total y range [-5, 5]
    8733: [
        [(-11, 0), (-7, -5), (-2, -5), (2, 0),
         (-2, 5), (-7, 5), (-11, 0)],
        [(2, 0), (11, 0)],
    ],
    # ∅ empty set (8709): total y range [-8, 8]
    8709: [
        [(0, -8), (5, -5), (8, 0), (5, 5), (0, 8),
         (-5, 5), (-8, 0), (-5, -5), (0, -8)],
        [(6, -6), (-6, 6)],
    ],
    # ∴ therefore (8756): total y range [-7, 7]
    8756: [
        [(0, -7), (0, -6)],
        [(-5, 7), (-4, 7)],
        [( 4, 7), ( 5, 7)],
    ],
    # ⟨ left angle bracket (10216): total y range [-10, 10]
    10216: [
        [(6, -10), (-6, 0), (6, 10)],
    ],
    # ⟩ right angle bracket (10217): total y range [-10, 10]
    10217: [
        [(-6, -10), (6, 0), (-6, 10)],
    ],
    # ⌊ left floor bracket (8970): total y range [-10, 10]
    8970: [
        [(-4, -10), (-4, 10), (6, 10)],
    ],
    # ⌋ right floor bracket (8971): total y range [-10, 10]
    8971: [
        [(4, -10), (4, 10), (-6, 10)],
    ],
    # ⌈ left ceiling bracket (8968): total y range [-10, 10]
    8968: [
        [(-4, 10), (-4, -10), (6, -10)],
    ],
    # ⌉ right ceiling bracket (8969): total y range [-10, 10]
    8969: [
        [(4, 10), (4, -10), (-6, -10)],
    ],
}
