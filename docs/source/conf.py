# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from __future__ import annotations

import os
import sys

# Ensure src/ is on sys.path so autodoc resolves handanim, voiceanim, and aianim
sys.path.insert(0, os.path.abspath("../../src"))

# -- Project information -----------------------------------------------------

project = "handanim"
copyright = "2025-2026, Subhrajyoty Roy"
author = "Subhrajyoty Roy"
release = "1.0.0"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.githubpages",
]

autosummary_generate = False
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

# Mock optional runtime dependencies if not installed in a minimal doc build environment
autodoc_mock_imports = [
    "kokoro_onnx",
    "kokoro",
    "vtracer",
]

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------

html_theme = "furo"
html_title = "handanim — Hand-Drawn Whiteboard Animation Studio"
html_static_path = ["_static"]
html_css_files = ["custom.css"]

html_theme_options = {
    "source_repository": "https://github.com/subroy13/handanim/",
    "source_branch": "master",
    "source_directory": "docs/source/",
    "navigation_with_keys": True,
    "light_css_variables": {
        "color-brand-primary": "#1d4ed8",
        "color-brand-content": "#1e40af",
        "color-admonition-background": "rgba(29, 78, 216, 0.06)",
    },
    "dark_css_variables": {
        "color-brand-primary": "#60a5fa",
        "color-brand-content": "#93c5fd",
        "color-admonition-background": "rgba(96, 165, 250, 0.1)",
    },
}
