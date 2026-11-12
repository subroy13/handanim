Installation & Setup
====================

``handanim`` requires **Python 3.11+** and the native **Cairo** 2D graphics library.

1. System Prerequisites (Cairo)
-------------------------------

Install the Cairo system library before installing Python packages:

**macOS (Homebrew)**

.. code-block:: bash

   brew install cairo ffmpeg

**Ubuntu / Debian**

.. code-block:: bash

   sudo apt update
   sudo apt install libcairo2 libcairo2-dev ffmpeg

**Windows**

1. Install the `GTK 3 Runtime <https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases>`_ (which bundles Cairo DLLs) and ensure its ``bin/`` directory is on your ``PATH``, or use Conda (see below).

.. note::

   ``handanim`` uses ``imageio-ffmpeg``, which automatically bundles a portable ``ffmpeg`` binary for MP4 video encoding and audio multiplexing—even if ``ffmpeg`` is not installed globally on your system.

2. Installing via ``pip`` (from PyPI)
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

3. Installing from Source (Poetry)
----------------------------------

For contributors or local development:

.. code-block:: bash

   git clone https://github.com/subroy13/handanim.git
   cd handanim
   poetry install --all-extras
   poetry run pytest

4. Installing with Conda
------------------------

If you use Conda or Miniforge, you can install Cairo and PyCairo directly from ``conda-forge``:

.. code-block:: bash

   conda create -n handanim python=3.11
   conda activate handanim
   conda install -c conda-forge cairo pycairo ffmpeg
   pip install "handanim[all]"

