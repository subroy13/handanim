import string

alphabet_symbols = list(string.ascii_letters)
number_symbols = [str(i) for i in range(10)]

# Greek letters (uppercase and lowercase)
greek_uppercase = ["Γ", "Δ", "Θ", "Λ", "Ξ", "Π", "Σ", "Φ", "Ψ", "Ω"]
greek_lowercase = [
    "α",
    "β",
    "γ",
    "δ",
    "ε",
    "ζ",
    "η",
    "θ",
    "ι",
    "κ",
    "λ",
    "μ",
    "ν",
    "ξ",
    "ο",
    "π",
    "ρ",
    "σ",
    "τ",
    "υ",
    "φ",
    "χ",
    "ψ",
    "ω",
]

# Common math symbols
math_symbols = [
    "+",
    "-",
    "=",
    "≠",
    "≈",
    "≡",
    "±",
    "∞",
    "∑",
    "∫",
    "∂",
    "∇",
    "√",
    "∝",
    "∈",
    "∉",
    "⊂",
    "⊆",
    "⊇",
    "⊄",
    "⊃",
    "⊥",
    "∠",
]

SYMBOL_LABELS = (
    alphabet_symbols + number_symbols + greek_lowercase + greek_uppercase + math_symbols
)
# List of symbol names to include (can extend)
