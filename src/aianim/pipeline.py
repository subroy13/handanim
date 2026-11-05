"""Autonomous animation generation pipeline with self-correction feedback loop."""

import re
from dataclasses import dataclass

from .assets import format_assets_markdown
from .compiler import plan_to_python
from .diagnostics import check_code
from .executor import CodeExecutor, ExecutionResult
from .models import BaseLLMModel, get_model
from .prompts.prompt_manager import PromptManager
from .schema import ScenePlan


@dataclass
class PipelineResult:
    """Outcome of the animation generation pipeline."""

    success: bool
    code: str
    scene_plan: ScenePlan | None
    output_path: str
    retries_used: int
    execution_result: ExecutionResult | None
    error: str = ""


class AnimationGenerator:
    """Orchestrates topic ideation, code generation, execution, and self-correction."""

    def __init__(
        self,
        model: BaseLLMModel | None = None,
        prompt_manager: PromptManager | None = None,
        executor: CodeExecutor | None = None,
        prompt_version: str = "v1",
    ):
        self.model = model or get_model()
        self.prompt_manager = prompt_manager or PromptManager()
        self.executor = executor or CodeExecutor()
        self.prompt_version = prompt_version

    def generate(
        self,
        topic: str,
        output_path: str = "output.mp4",
        max_retries: int = 2,
        use_compiler: bool = False,
    ) -> PipelineResult:
        """Run end-to-end animation generation pipeline with self-correction feedback loop.

        Args:
            topic: Natural language topic description (e.g. 'explain Pythagorean theorem').
            output_path: Target video or image output path.
            max_retries: Maximum self-correction attempts upon syntax or execution failure.
            use_compiler: If True, compiles the ScenePlan directly using plan_to_python()
                          instead of calling the LLM codegen prompt.

        Returns:
            PipelineResult containing generated code, plan, and execution status.
        """
        assets_md = format_assets_markdown()

        # --- Stage 1: Topic -> ScenePlan ---
        big_picture_template = self.prompt_manager.get("big_picture", version=self.prompt_version)
        sys_msg, user_msg = big_picture_template.format(topic=topic, assets=assets_md)

        plan_raw = self.model.invoke(
            messages=[{"role": "user", "content": user_msg}],
            system_message=sys_msg,
            response_format={"type": "json_object"},
        )

        try:
            scene_plan = ScenePlan.from_json(plan_raw)
        except Exception:
            # Fallback attempt to extract JSON object with regex
            match = re.search(r"\{.*\}", plan_raw, re.DOTALL)
            if match:
                try:
                    scene_plan = ScenePlan.from_json(match.group(0))
                except Exception as e:
                    return PipelineResult(
                        success=False,
                        code="",
                        scene_plan=None,
                        output_path=output_path,
                        retries_used=0,
                        execution_result=None,
                        error=f"Failed to parse ScenePlan JSON: {e}\nRaw output: {plan_raw[:300]}",
                    )
            else:
                return PipelineResult(
                    success=False,
                    code="",
                    scene_plan=None,
                    output_path=output_path,
                    retries_used=0,
                    execution_result=None,
                    error=f"Model did not return valid JSON for ScenePlan.\nRaw output: {plan_raw[:300]}",
                )

        # --- Stage 2: ScenePlan -> Code ---
        if use_compiler:
            code = plan_to_python(scene_plan, output_path=output_path)
        else:
            codegen_template = self.prompt_manager.get("codegen", version=self.prompt_version)
            c_sys_msg, c_user_msg = codegen_template.format(
                scene_plan=scene_plan.to_json(),
                output_path=output_path,
                assets=assets_md,
            )
            code_raw = self.model.invoke(
                messages=[{"role": "user", "content": c_user_msg}],
                system_message=c_sys_msg,
            )
            code = self._extract_python_code(code_raw)

        # --- Stage 3: Verification & Feedback Loop ---
        retries_used = 0
        last_exec_result: ExecutionResult | None = None

        while retries_used <= max_retries:
            # Check AST / linter first
            diag = check_code(code)
            if not diag.is_valid:
                error_msg = "Linter / AST Errors:\n" + "\n".join(diag.errors)
                if retries_used >= max_retries:
                    return PipelineResult(
                        success=False,
                        code=code,
                        scene_plan=scene_plan,
                        output_path=output_path,
                        retries_used=retries_used,
                        execution_result=None,
                        error=error_msg,
                    )
                code = self._retry_correction(
                    scene_plan=scene_plan,
                    faulty_code=code,
                    error_message=error_msg,
                    output_path=output_path,
                )
                retries_used += 1
                continue

            # Execute code
            exec_result = self.executor.execute(code, expected_output=output_path)
            last_exec_result = exec_result

            if exec_result.success:
                return PipelineResult(
                    success=True,
                    code=code,
                    scene_plan=scene_plan,
                    output_path=output_path,
                    retries_used=retries_used,
                    execution_result=exec_result,
                )

            # Failure during execution -> Feed error back to LLM
            if retries_used >= max_retries:
                break

            retries_used += 1
            code = self._retry_correction(
                scene_plan=scene_plan,
                faulty_code=code,
                error_message=exec_result.error_summary or exec_result.stderr,
                output_path=output_path,
            )

        return PipelineResult(
            success=False,
            code=code,
            scene_plan=scene_plan,
            output_path=output_path,
            retries_used=retries_used,
            execution_result=last_exec_result,
            error=last_exec_result.error_summary if last_exec_result else "Execution failed.",
        )

    def _retry_correction(
        self,
        scene_plan: ScenePlan,
        faulty_code: str,
        error_message: str,
        output_path: str,
    ) -> str:
        """Call correction prompt to fix faulty code based on traceback."""
        try:
            correction_template = self.prompt_manager.get("correction", version=self.prompt_version)
            sys_msg, user_msg = correction_template.format(
                scene_plan=scene_plan.to_json(),
                faulty_code=faulty_code,
                error_message=error_message,
                output_path=output_path,
            )
            corrected_raw = self.model.invoke(
                messages=[{"role": "user", "content": user_msg}],
                system_message=sys_msg,
            )
            return self._extract_python_code(corrected_raw)
        except Exception:
            # Fallback to compiler if correction call fails
            return plan_to_python(scene_plan, output_path=output_path)

    @staticmethod
    def _extract_python_code(raw_text: str) -> str:
        """Extract code from within ```python ... ``` fences or return bare text."""
        match = re.search(r"```(?:python)?\n(.*?)```", raw_text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return raw_text.strip()
