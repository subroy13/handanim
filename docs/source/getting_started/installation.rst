Installation & Setup
====================

``handanim`` requires **Python 3.11+**.

.. tip::

   - **Zero-Install Browser Playground**: Try ``handanim`` immediately in Google Colab via `notebooks/handanim_colab_playground.ipynb <https://colab.research.google.com/github/subroy13/handanim/blob/master/notebooks/handanim_colab_playground.ipynb>`_.
   - **Bundled FFmpeg**: ``handanim`` depends on ``imageio-ffmpeg``, which ships a self-contained static ``ffmpeg`` binary for macOS, Linux, and Windows. Video rendering and audio muxing work out of the box without installing ``ffmpeg`` on your system ``PATH``.
   - **Automatic Cairo Backend (`pycairo` → `cairocffi`)**: ``handanim`` uses prebuilt ``pycairo`` binary wheels when available and automatically falls back to pure-Python ``cairocffi`` (with auto-discovery of Homebrew ``/opt/homebrew/lib``, ``/usr/local/lib``, and Conda ``$CONDA_PREFIX/lib``). Inspect the active backend via ``handanim.get_cairo_backend()`` or force ``HANDANIM_CAIRO_BACKEND=cairocffi``.

1. Installing via ``pip`` (from PyPI)
-------------------------------------

**Core Animation Library (`handanim`)**

.. code-block:: bash

   pip install handanim

**With Voice Synthesis & Audio Extras (`voiceanim`)**

.. code-block:: bash

   pip install "handanim[voice]"

**With AI Agentic Studio & MCP Server (`aianim`)**

.. code-block:: bash

   pip install "handanim[ai]"

**Full Installation (Everything)**

.. code-block:: bash

   pip install "handanim[all]"

2. Platform Notes for Cairo (If Prebuilt Wheel Is Unavailable)
--------------------------------------------------------------

If ``pip`` attempts to compile ``pycairo`` from source on your platform or ``libcairo`` is missing:

- **Force Prebuilt Binary Wheel**:

  .. code-block:: bash

     pip install --only-binary=:all: pycairo
     pip install handanim

- **macOS (Homebrew)**:

  .. code-block:: bash

     brew install cairo
     pip install handanim

- **Ubuntu / Debian / Google Colab**:

  .. code-block:: bash

     sudo apt-get update && sudo apt-get install -y libcairo2-dev
     pip install handanim

3. Installing with Conda / Mamba
--------------------------------

If you use Conda or Miniforge, ``conda-forge`` provides precompiled Cairo binaries on all operating systems:

.. code-block:: bash

   conda create -n handanim python=3.11
   conda activate handanim
   conda install -c conda-forge cairo pycairo
   pip install "handanim[all]"

4. Installing from Source (Poetry)
----------------------------------

For contributors or local development:

.. code-block:: bash

   git clone https://github.com/subroy13/handanim.git
   cd handanim
   poetry install --all-extras
   poetry run pytest
