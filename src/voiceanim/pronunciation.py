"""Math and LaTeX to natural spoken English pronunciation engine for TTS."""

from __future__ import annotations

import re

# Ordered dictionary of LaTeX commands and symbols to spoken equivalents
_GREEK_AND_SYMBOLS: list[tuple[str, str]] = [
    (r"\mathbb{E}", "expected value"),
    (r"\mathbb{P}", "probability"),
    (r"\mathbb{R}", "R"),
    (r"\mathbb{N}", "N"),
    (r"\mathbb{Z}", "Z"),
    (r"\mathbb{C}", "C"),
    (r"\mathcal{N}", "normal"),
    (r"\mathcal{L}", "loss"),
    (r"\mathcal{O}", "big O"),
    (r"\infty", "infinity"),
    (r"\partial", "partial"),
    (r"\nabla", "nabla"),
    (r"\approx", "is approximately"),
    (r"\neq", "is not equal to"),
    (r"\ne", "is not equal to"),
    (r"\leq", "is less than or equal to"),
    (r"\le", "is less than or equal to"),
    (r"\geq", "is greater than or equal to"),
    (r"\ge", "is greater than or equal to"),
    (r"\equiv", "is equivalent to"),
    (r"\sim", "is distributed as"),
    (r"\propto", "is proportional to"),
    (r"\pm", "plus or minus"),
    (r"\mp", "minus or plus"),
    (r"\times", "times"),
    (r"\cdot", "times"),
    (r"\div", "divided by"),
    (r"\mid", "given"),
    (r"\in", "in"),
    (r"\notin", "not in"),
    (r"\subset", "is a subset of"),
    (r"\subseteq", "is a subset of"),
    (r"\cup", "union"),
    (r"\cap", "intersection"),
    (r"\forall", "for all"),
    (r"\exists", "there exists"),
    (r"\implies", "implies"),
    (r"\iff", "if and only if"),
    (r"\Leftrightarrow", "if and only if"),
    (r"\Rightarrow", "implies"),
    (r"\rightarrow", "to"),
    (r"\to", "to"),
    (r"\leftarrow", "from"),
    (r"\mapsto", "maps to"),
    (r"\dots", "dot dot dot"),
    (r"\cdots", "dot dot dot"),
    (r"\ldots", "dot dot dot"),
    # Functions
    (r"\arcsin", "arc sine"),
    (r"\arccos", "arc cosine"),
    (r"\arctan", "arc tangent"),
    (r"\sinh", "hyperbolic sine"),
    (r"\cosh", "hyperbolic cosine"),
    (r"\tanh", "hyperbolic tangent"),
    (r"\sin", "sine"),
    (r"\cos", "cosine"),
    (r"\tan", "tangent"),
    (r"\sec", "secant"),
    (r"\csc", "cosecant"),
    (r"\cot", "cotangent"),
    (r"\ln", "natural log"),
    (r"\log", "log"),
    (r"\exp", "e to the"),
    (r"\argmax", "arg max"),
    (r"\argmin", "arg min"),
    (r"\max", "max"),
    (r"\min", "min"),
    (r"\sup", "supremum"),
    (r"\inf", "infimum"),
    (r"\det", "determinant"),
    (r"\dim", "dimension"),
    (r"\Var", "variance"),
    (r"\Cov", "covariance"),
    # Greek letters
    (r"\varepsilon", "epsilon"),
    (r"\varphi", "phi"),
    (r"\vartheta", "theta"),
    (r"\alpha", "alpha"),
    (r"\beta", "beta"),
    (r"\gamma", "gamma"),
    (r"\Gamma", "capital gamma"),
    (r"\delta", "delta"),
    (r"\Delta", "delta"),
    (r"\epsilon", "epsilon"),
    (r"\zeta", "zeta"),
    (r"\eta", "eta"),
    (r"\theta", "theta"),
    (r"\Theta", "capital theta"),
    (r"\iota", "iota"),
    (r"\kappa", "kappa"),
    (r"\lambda", "lambda"),
    (r"\Lambda", "capital lambda"),
    (r"\mu", "mu"),
    (r"\nu", "nu"),
    (r"\xi", "xi"),
    (r"\Xi", "capital xi"),
    (r"\pi", "pi"),
    (r"\Pi", "capital pi"),
    (r"\rho", "rho"),
    (r"\sigma", "sigma"),
    (r"\Sigma", "sigma"),
    (r"\tau", "tau"),
    (r"\upsilon", "upsilon"),
    (r"\phi", "phi"),
    (r"\Phi", "capital phi"),
    (r"\chi", "chi"),
    (r"\psi", "psi"),
    (r"\Psi", "capital psi"),
    (r"\omega", "omega"),
    (r"\Omega", "omega"),
]

_UNICODE_MATH_MAP: dict[str, str] = {
    "α": " alpha ",
    "β": " beta ",
    "γ": " gamma ",
    "δ": " delta ",
    "Δ": " delta ",
    "ε": " epsilon ",
    "θ": " theta ",
    "λ": " lambda ",
    "μ": " mu ",
    "π": " pi ",
    "ρ": " rho ",
    "σ": " sigma ",
    "Σ": " sum of ",
    "τ": " tau ",
    "φ": " phi ",
    "ω": " omega ",
    "Ω": " omega ",
    "∞": " infinity ",
    "≈": " is approximately ",
    "≠": " is not equal to ",
    "≤": " is less than or equal to ",
    "≥": " is greater than or equal to ",
    "±": " plus or minus ",
    "×": " times ",
    "÷": " divided by ",
    "→": " to ",
    "⇒": " implies ",
    "∈": " in ",
    "∉": " not in ",
    "∀": " for all ",
    "∃": " there exists ",
    "√": " square root of ",
    "∫": " integral of ",
    "∂": " partial ",
    "∇": " nabla ",
    "²": " squared ",
    "³": " cubed ",
}


def _extract_braced(s: str, start_idx: int) -> tuple[str, int] | None:
    """Extract content inside balanced `{...}` starting at `start_idx`."""
    if start_idx >= len(s) or s[start_idx] != "{":
        return None
    depth = 0
    for i in range(start_idx, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start_idx + 1 : i], i + 1
    return None


def _replace_fracs(expr: str) -> str:
    """Recursively replace `\\frac{num}{den}` (and `\\dfrac`, `\\tfrac`) with spoken English."""
    pattern = re.compile(r"\\[dt]?frac\s*")
    while True:
        match = pattern.search(expr)
        if not match:
            break
        num_res = _extract_braced(expr, match.end())
        if num_res is None:
            break
        num_str, after_num = num_res
        while after_num < len(expr) and expr[after_num].isspace():
            after_num += 1
        den_res = _extract_braced(expr, after_num)
        if den_res is None:
            break
        den_str, after_den = den_res

        num_clean = _convert_math_expr(num_str).strip()
        den_clean = _convert_math_expr(den_str).strip()

        if num_clean == "1" and den_clean == "2":
            spoken = "one half"
        elif num_clean == "1" and den_clean == "3":
            spoken = "one third"
        elif num_clean == "1" and den_clean == "4":
            spoken = "one quarter"
        elif num_str.strip() == "d" and den_str.strip().startswith("d"):
            var = _convert_math_expr(den_str.strip()[1:]).strip()
            spoken = f"d by d {var}"
        elif num_str.strip().startswith("d") and den_str.strip().startswith("d") and len(num_str.strip()) <= 3:
            n_var = _convert_math_expr(num_str.strip()[1:]).strip()
            d_var = _convert_math_expr(den_str.strip()[1:]).strip()
            spoken = f"d {n_var} by d {d_var}"
        else:
            spoken = f"{num_clean} over {den_clean}"

        expr = expr[: match.start()] + f" {spoken} " + expr[after_den:]
    return expr


def _replace_accents(expr: str) -> str:
    """Replace `\\hat{x}`, `\\bar{x}`, `\\tilde{x}`, `\\vec{x}`, `\\dot{x}`."""
    accent_map = {
        "hat": "hat",
        "widehat": "hat",
        "bar": "bar",
        "overline": "bar",
        "tilde": "tilde",
        "widetilde": "tilde",
        "vec": "vector",
        "dot": "dot",
        "ddot": "double dot",
    }
    for cmd, spoken_suffix in accent_map.items():
        pat = re.compile(rf"\\{cmd}\s*\{{([^{{}}]+)\}}")
        while pat.search(expr):
            expr = pat.sub(lambda m, suf=spoken_suffix: f" {_convert_math_expr(m.group(1)).strip()} {suf} ", expr)
    return expr


def _replace_roots(expr: str) -> str:
    """Replace `\\sqrt[n]{x}` and `\\sqrt{x}`."""
    nth_pat = re.compile(r"\\sqrt\s*\[([^\[\]]+)\]\s*\{([^{}]+)\}")
    while nth_pat.search(expr):
        def _nth_repl(m: re.Match) -> str:
            deg = _convert_math_expr(m.group(1)).strip()
            rad = _convert_math_expr(m.group(2)).strip()
            if deg == "3":
                return f" the cube root of {rad} "
            return f" the {deg}-th root of {rad} "

        expr = nth_pat.sub(_nth_repl, expr)

    sqrt_pat = re.compile(r"\\sqrt\s*\{([^{}]+)\}")
    while sqrt_pat.search(expr):
        expr = sqrt_pat.sub(lambda m: f" the square root of {_convert_math_expr(m.group(1)).strip()} ", expr)
    return expr


def _replace_big_operators(expr: str) -> str:
    """Replace `\\int`, `\\sum`, `\\prod`, `\\lim` with bounds."""
    ops = [
        ("int", "integral", "from", "to", "of"),
        ("sum", "sum", "from", "to", "of"),
        ("prod", "product", "from", "to", "of"),
    ]
    for cmd, name, low_prep, high_prep, trail in ops:
        # Both _ and ^ (either order)
        pat_sub_sup = re.compile(
            rf"\\{cmd}\s*_(?:\{{([^{{}}]+)\}}|([A-Za-z0-9]))\s*\^(?:\{{([^{{}}]+)\}}|([A-Za-z0-9\\]+))"
        )
        expr = pat_sub_sup.sub(
            lambda m, n=name, lp=low_prep, hp=high_prep, tr=trail: (
                f" the {n} {lp} {_convert_math_expr(m.group(1) or m.group(2)).strip()} "
                f"{hp} {_convert_math_expr(m.group(3) or m.group(4)).strip()} {tr} "
            ),
            expr,
        )
        # Only _
        pat_sub = re.compile(rf"\\{cmd}\s*_(?:\{{([^{{}}]+)\}}|([A-Za-z0-9]))")
        expr = pat_sub.sub(
            lambda m, n=name, tr=trail: f" the {n} over {_convert_math_expr(m.group(1) or m.group(2)).strip()} {tr} ",
            expr,
        )
        # Bare operator
        pat_bare = re.compile(rf"\\{cmd}\b")
        expr = pat_bare.sub(f" the {name} {trail} ", expr)

    # \lim_{x \to a}
    lim_pat = re.compile(r"\\lim\s*_(?:\{([^{}]+)\}|([A-Za-z0-9]))")
    def _lim_repl(m: re.Match) -> str:
        sub = m.group(1) or m.group(2)
        sub = re.sub(r"\\(?:to|rightarrow)\b", " approaches ", sub)
        return f" the limit as {_convert_math_expr(sub).strip()} of "
    expr = lim_pat.sub(_lim_repl, expr)
    expr = re.sub(r"\\lim\b", " the limit of ", expr)
    return expr


def _format_exponent(exp_raw: str) -> str:
    exp_clean = _convert_math_expr(exp_raw).strip()
    if exp_clean == "2":
        return "squared"
    if exp_clean == "3":
        return "cubed"
    if exp_clean in ("T", "top", "\\top"):
        return "transpose"
    if exp_clean in ("-1", "- 1", "minus 1"):
        return "inverse"
    if exp_clean == "*":
        return "star"
    return f"to the power of {exp_clean}"


def _convert_math_expr(expr: str) -> str:
    """Convert a single LaTeX math expression (without outer `$`) into spoken English."""
    # Remove formatting commands like \left, \right, \big, \text{...}, \mathrm{...}, \mathbf{...}
    s = expr.strip()
    s = re.sub(r"\\(?:left|right|big|Big|bigg|Bigg)\b", " ", s)
    s = re.sub(r"\\(?:text|mathrm|mathbf|mathit|mathsf|operatorname)\s*\{([^{}]*)\}", r" \1 ", s)

    # Big O notation: O(...)
    s = re.sub(r"\bO\s*\(", "big O of (", s)

    # Fractions, accents, roots, and big operators
    s = _replace_fracs(s)
    s = _replace_accents(s)
    s = _replace_roots(s)
    s = _replace_big_operators(s)

    # Norms \|x\| and absolute values |x|
    s = re.sub(r"\\\|([^\\]+)\\\|", lambda m: f" the norm of {_convert_math_expr(m.group(1)).strip()} ", s)

    # Replace e^{...} with "e to the ..."
    s = re.sub(
        r"\be\s*\^\s*(?:\{([^{}]+)\}|([A-Za-z0-9\-]+))",
        lambda m: f" e to the {_convert_math_expr(m.group(1) or m.group(2)).strip()} ",
        s,
    )

    # Superscripts: ^{...} or ^x
    s = re.sub(
        r"\^\s*\{([^{}]+)\}",
        lambda m: f" {_format_exponent(m.group(1))} ",
        s,
    )
    s = re.sub(
        r"\^\s*([A-Za-z0-9])",
        lambda m: f" {_format_exponent(m.group(1))} ",
        s,
    )

    # Subscripts: _{...} or _x
    s = re.sub(
        r"_\s*\{([^{}]+)\}",
        lambda m: f" sub {_convert_math_expr(m.group(1)).strip()} ",
        s,
    )
    s = re.sub(
        r"_\s*([A-Za-z0-9])",
        lambda m: f" sub {m.group(1)} ",
        s,
    )

    # Greek letters & LaTeX symbols
    for cmd, spoken in _GREEK_AND_SYMBOLS:
        if cmd.startswith("\\") and cmd[-1].isalpha():
            s = re.sub(re.escape(cmd) + r"\b", f" {spoken} ", s)
        else:
            s = s.replace(cmd, f" {spoken} ")

    # Unicode math characters
    for ch, spoken in _UNICODE_MATH_MAP.items():
        s = s.replace(ch, spoken)

    # Conditional probability P(A | B)
    s = re.sub(
        r"\b([Pp])\s*\(\s*([^()|]+?)\s*\|\s*([^()|]+?)\s*\)",
        r"probability of \2 given \3",
        s,
    )

    # Basic arithmetic operators inside math mode
    s = s.replace("=", " equals ")
    s = s.replace("+", " plus ")
    # Minus sign: binary vs unary
    s = re.sub(r"(?<=[A-Za-z0-9\)\}])\s*-\s*(?=[A-Za-z0-9\(\\])", " minus ", s)
    s = re.sub(r"(?:^|(?<=[\(\{=]))\s*-\s*(?=[A-Za-z0-9\\])", " negative ", s)
    s = s.replace("<", " is less than ")
    s = s.replace(">", " is greater than ")

    # Differential dx, dy, dt at end of integral
    s = re.sub(r"\bd([xyzuvwt])\b", r"d \1", s)

    # Clean up remaining braces, parens, and unknown backslashes
    s = s.replace("{", " ").replace("}", " ")
    s = s.replace("(", " ").replace(")", " ")
    s = re.sub(r"\\[,;:!]\s*", " ", s)
    s = re.sub(r"\\([A-Za-z]+)", r" \1 ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def latex_to_speech(text: str) -> str:
    """Convert a string containing LaTeX math (`$...$`, `$$...$$`, or raw LaTeX) into natural spoken English.

    If `text` contains delimited math spans (`$$...$$`, `$...$`, `\\(...\\)`, `\\[...\\]`),
    each math span is converted while surrounding prose is preserved (with any stray
    Unicode math symbols or inline LaTeX commands also expanded). If `text` has no `$`
    delimiters but contains LaTeX math commands (like `\\frac`, `\\int`, `\\sum`, `^`, `_`),
    the entire string is converted as a math expression.

    Examples::

        >>> latex_to_speech("Euler's identity is $e^{i\\pi} + 1 = 0$.")
        "Euler's identity is e to the i pi plus 1 equals 0."
        >>> latex_to_speech(r"\\int_0^\\pi \\sin(x) dx = 2")
        'the integral from 0 to pi of sine x d x equals 2'
    """
    if not text:
        return text

    has_delimiters = any(d in text for d in ("$", r"\(", r"\["))
    if has_delimiters:
        out = text
        # 1. $$...$$
        out = re.sub(r"\$\$(.+?)\$\$", lambda m: f" {_convert_math_expr(m.group(1))} ", out, flags=re.DOTALL)
        # 2. \[...\]
        out = re.sub(r"\\\[(.+?)\\\]", lambda m: f" {_convert_math_expr(m.group(1))} ", out, flags=re.DOTALL)
        # 3. \(...\)
        out = re.sub(r"\\\((.+?)\\\)", lambda m: f" {_convert_math_expr(m.group(1))} ", out, flags=re.DOTALL)
        # 4. $...$
        out = re.sub(r"\$([^\$]+)\$", lambda m: f" {_convert_math_expr(m.group(1))} ", out)
        # Also replace any standalone Unicode math symbols in prose
        for ch, spoken in _UNICODE_MATH_MAP.items():
            out = out.replace(ch, spoken)
        out = re.sub(r"\s+([.,!?;:])", r"\1", out)
        out = re.sub(r"\s+", " ", out).strip()
        return out

    # Check if the string looks like a bare LaTeX math expression
    math_indicators = ("\\", "^", "_", "=", "∫", "∑", "√", "≈", "≠", "≤", "≥")
    if any(tok in text for tok in math_indicators) or re.search(r"\bO\s*\(", text):
        out = _convert_math_expr(text)
        out = re.sub(r"\s+([.,!?;:])", r"\1", out)
        return re.sub(r"\s+", " ", out).strip()

    return text
