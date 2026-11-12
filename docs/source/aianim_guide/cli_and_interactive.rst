CLI & Interactive Studio
========================

Installing ``handanim[ai]`` or ``handanim[all]`` registers the ``aianim`` and ``handanim-ai`` command-line entry points.

Command-Line Interface
----------------------

1. Generate an Animation from a Prompt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Using AWS Bedrock (default: Claude 3.5 Sonnet) or OpenRouter
   handanim-ai generate "Explain the Pythagorean theorem visually" \
       --provider bedrock \
       --output pythagoras_ai.mp4

   # Fast deterministic test run using the offline mock model
   handanim-ai generate "Show a flowchart of machine learning" \
       --provider mock \
       --output test_out.mp4

2. Launch the Interactive Terminal Studio
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run ``handanim-ai studio`` (or simply ``aianim`` with no arguments) to launch the interactive Rich + Questionary terminal wizard:

.. code-block:: bash

   handanim-ai studio

The interactive studio guides you through:

- Selecting an LLM provider (`AWS Bedrock`, `OpenRouter`, or `Mock`)
- Drafting and reviewing the structured :class:`~aianim.schema.ScenePlan`
- Compiling and executing the ``handanim`` script with live progress feedback

Programmatic Python API (:class:`~aianim.pipeline.AnimationPipeline`)
---------------------------------------------------------------------

You can also invoke the pipeline directly from Python:

.. code-block:: python

   from aianim.models import BedrockModel
   from aianim.pipeline import AnimationPipeline

   model = BedrockModel(model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0")
   pipeline = AnimationPipeline(model=model, max_retries=2)

   result = pipeline.run(
       topic="Explain binary search on a sorted array",
       output_path="binary_search.mp4",
   )
   print("Success:", result.success, "Output:", result.output_path)

