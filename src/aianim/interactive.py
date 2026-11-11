"""Interactive terminal assistant for conversational animation planning and generation."""

import os
import re
import sys

try:
    import questionary

    HAS_QUESTIONARY = True
except ImportError:
    HAS_QUESTIONARY = False

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.tree import Tree

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from .assets import format_assets_markdown
from .compiler import plan_to_python
from .diagnostics import check_code
from .executor import CodeExecutor
from .models import BaseLLMModel, get_model
from .prompts.prompt_manager import PromptManager
from .schema import ScenePlan

BANNER = r"""
  _                     _             _                     _
 | |__   __ _ _ __   __| | __ _ _ __ (_)_ __ ___         __ _(_)
 | '_ \ / _` | '_ \ / _` |/ _` | '_ \| | '_ ` _ \ _____ / _` | |
 | | | | (_| | | | | (_| | (_| | | | | | | | | | |_____| (_| | |
 |_| |_|\__,_|_| |_|\__,_|\__,_|_| |_|_|_| |_| |_|      \__,_|_|
               Interactive Animation Assistant
"""


class InteractiveSession:
    """Conversational CLI session with live inspection and arrow-key user feedback."""

    def __init__(
        self,
        model: BaseLLMModel | None = None,
        verbose: bool = True,
        output_dir: str = ".",
    ):
        self.model = model or get_model()
        self.verbose = verbose
        self.output_dir = output_dir
        self.prompt_manager = PromptManager()
        self.executor = CodeExecutor()
        self.conversation_history: list[dict[str, str]] = []
        self.current_plan: ScenePlan | None = None
        self.current_code: str | None = None
        self.console = Console() if HAS_RICH else None

    def log(self, tag: str, message: str, color: str = "\033[94m"):
        """Print formatted stage log."""
        if HAS_RICH and self.console:
            tag_color = "cyan" if "TASK" in tag else ("yellow" if "WARN" in tag else "green")
            self.console.print(f"[{tag_color} bold][{tag}][/] {message}")
        else:
            reset = "\033[0m"
            bold = "\033[1m"
            print(f"\n{bold}{color}[{tag}]{reset} {message}")

    def log_prompt(self, system_message: str, user_message: str):
        """Print under-the-hood prompt when verbose mode is active."""
        if not self.verbose:
            return
        if HAS_RICH and self.console:
            body = ""
            if system_message:
                body += f"[bold cyan]--- System Prompt ---[/bold cyan]\n{system_message}\n\n"
            body += f"[bold yellow]--- User Prompt ---[/bold yellow]\n{user_message}"
            self.console.print(
                Panel(
                    body,
                    title="🔍 [bold magenta]UNDER THE HOOD: PROMPT SENT TO MODEL[/bold magenta]",
                    border_style="magenta",
                )
            )
        else:
            dim = "\033[2m"
            reset = "\033[0m"
            cyan = "\033[96m"
            print(f"\n{dim}{'=' * 60}{reset}")
            print(f"{cyan}[UNDER THE HOOD: PROMPT SENT TO MODEL]{reset}")
            if system_message:
                print(f"{dim}--- System Prompt ---{reset}\n{system_message}")
            print(f"{dim}--- User Prompt ---{reset}\n{user_message}")
            print(f"{dim}{'=' * 60}{reset}\n")

    def prompt_choice(self, message: str, choices: list[str], default: str | None = None) -> str:
        """Prompt user with an interactive arrow-key choice menu using questionary with fallback."""
        if HAS_QUESTIONARY and sys.stdin.isatty():
            try:
                selected = questionary.select(
                    message,
                    choices=choices,
                    default=default or choices[0],
                    use_indicator=True,
                ).ask()
                if selected is not None:
                    return str(selected)
                # Handle Ctrl+C
                return choices[-1] if any("Exit" in c or "Quit" in c for c in choices) else choices[0]
            except Exception:
                pass

        # Fallback for non-TTY / automated tests / pipe environments
        print(f"\n{message}")
        for idx, opt in enumerate(choices, 1):
            print(f"  [{idx}] {opt}")
        try:
            val = input("Choice > ").strip()
            if not val:
                return choices[0]
            if val.isdigit() and 1 <= int(val) <= len(choices):
                return choices[int(val) - 1]
            for opt in choices:
                if val.lower() in opt.lower():
                    return opt
            return choices[0]
        except (KeyboardInterrupt, EOFError):
            return choices[-1] if any("Exit" in c or "Quit" in c for c in choices) else choices[0]

    def prompt_text(self, message: str, default: str = "") -> str:
        """Prompt for text input using questionary or standard input."""
        if HAS_QUESTIONARY and sys.stdin.isatty():
            try:
                res = questionary.text(message, default=default).ask()
                return (res or "").strip()
            except Exception:
                pass
        try:
            return input(f"\n{message}\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            return ""

    def run(self):
        """Run the interactive session."""
        model_name = getattr(self.model, "model_id", getattr(self.model, "model_name", type(self.model).__name__))
        if HAS_RICH and self.console:
            self.console.print(BANNER, style="bold cyan")
            info = (
                f"[bold]Connected Provider:[/bold] {type(self.model).__name__}\n"
                f"[bold]Model / Profile:[/bold] {model_name}\n"
                f"[bold]Verbose Mode:[/bold] {'[green]ENABLED[/green]' if self.verbose else '[dim]DISABLED[/dim]'}\n"
                f"[bold]Output Directory:[/bold] {os.path.abspath(self.output_dir)}"
            )
            self.console.print(Panel(info, title="⚙️ Configuration", border_style="blue"))
        else:
            print(BANNER)
            print(f"Connected Provider: {type(self.model).__name__} (Model: {model_name})")
            print(f"Verbose prompt logging: {'ENABLED' if self.verbose else 'DISABLED'}")
            print(f"Output Directory: {os.path.abspath(self.output_dir)}")
            print("-" * 65)

        initial_topic = self.prompt_text("What whiteboard animation would you like to create?")
        if not initial_topic:
            print("No topic provided. Goodbye!")
            return

        self.handle_topic_turn(initial_topic)

    def handle_topic_turn(self, topic: str):
        """Analyze topic, ask clarifying questions if ambiguous, or draft plan."""
        self.log("TASK 1/4", f"Analyzing topic and checking for clarifications: '{topic}'...")

        clarification_system = (
            "You are a helpful animation director for handanim whiteboard videos.\n"
            "Analyze the user's topic request. If the request is clear and specific, reply with: PROCEED_TO_PLAN.\n"
            "If the request could benefit from choices (e.g. visual approach, target duration, mathematical style, level of detail),\n"
            "ask 1 to 3 friendly, concise clarifying questions or propose 2 creative approaches for the user to choose."
        )
        user_msg = f"User wants an animation on: {topic}"
        self.log_prompt(clarification_system, user_msg)

        resp = self.model.invoke(
            messages=[{"role": "user", "content": user_msg}],
            system_message=clarification_system,
        )

        if "PROCEED_TO_PLAN" in resp:
            self.generate_and_review_plan(topic)
        else:
            if HAS_RICH and self.console:
                self.console.print(Panel(resp, title="🎬 Director's Suggestions & Questions", border_style="yellow"))
            else:
                print(f"\nAssistant:\n{resp}\n")
            self.conversation_history.append({"role": "user", "content": topic})
            self.conversation_history.append({"role": "assistant", "content": resp})

            if sys.stdin.isatty():
                reply = self.prompt_text("Your answer / preferences (or press Enter to proceed with defaults):")
                if reply:
                    self.handle_user_message(reply)
                else:
                    self.generate_and_review_plan(topic)

    def handle_user_message(self, message: str):
        """Handle iterative conversational user feedback."""
        if message.lower() in ("yes", "proceed", "go", "generate", "looks good", "y"):
            if self.current_plan and not self.current_code:
                self.generate_code_from_plan()
            elif self.current_code:
                self.execute_and_verify(self.current_code, os.path.join(self.output_dir, "output.mp4"))
            else:
                self.generate_and_review_plan(message)
            return

        self.conversation_history.append({"role": "user", "content": message})
        self.log("TASK", "Processing user feedback...")

        prompt = (
            "You are an animation director conversing with a user.\n"
            "Conversation so far:\n"
            + "\n".join(f"{m['role'].upper()}: {m['content']}" for m in self.conversation_history)
            + "\n\nIf the user is ready to build the animation or has specified their preference, reply with: [ACTION: BUILD_PLAN].\n"
            "Otherwise, reply conversationally answering their questions."
        )

        resp = self.model.invoke(
            messages=[{"role": "user", "content": prompt}],
            system_message="You are a whiteboard animation assistant.",
        )

        if "[ACTION: BUILD_PLAN]" in resp:
            context = " ".join(m["content"] for m in self.conversation_history if m["role"] == "user")
            self.generate_and_review_plan(context)
        else:
            if HAS_RICH and self.console:
                self.console.print(Panel(resp, title="🎬 Assistant", border_style="yellow"))
            else:
                print(f"\nAssistant:\n{resp}")
            self.conversation_history.append({"role": "assistant", "content": resp})
            if sys.stdin.isatty():
                followup = self.prompt_text("Your response (or press Enter to generate plan):")
                if followup:
                    self.handle_user_message(followup)
                else:
                    context = " ".join(m["content"] for m in self.conversation_history if m["role"] == "user")
                    self.generate_and_review_plan(context)

    def generate_and_review_plan(self, topic_summary: str):
        """Run Ideation stage, display plan, and provide interactive arrow-key choice menu."""
        self.log("TASK 2/4", "Generating structured ScenePlan specification...")
        assets_md = format_assets_markdown()
        bp = self.prompt_manager.get("big_picture", version="v1")
        sys_msg, user_msg = bp.format(topic=topic_summary, assets=assets_md)
        self.log_prompt(sys_msg, user_msg)

        plan_raw = self.model.invoke(
            messages=[{"role": "user", "content": user_msg}],
            system_message=sys_msg,
            response_format={"type": "json_object"},
        )

        try:
            self.current_plan = ScenePlan.from_json(plan_raw)
        except Exception as e:
            self.log("WARN", f"Failed to parse model plan directly ({e}). Retrying with repair...", color="\033[93m")
            try:
                match = re.search(r"\{.*\}", plan_raw, re.DOTALL)
                self.current_plan = ScenePlan.from_json(match.group(0)) if match else None
            except Exception:
                self.current_plan = None

        if not self.current_plan:
            print("\nError: Could not generate a valid scene plan. Raw response:")
            print(plan_raw[:400])
            return

        self.display_plan_summary(self.current_plan)

        if not sys.stdin.isatty():
            return

        # Interactive arrow-key choice loop
        while self.current_plan:
            choice = self.prompt_choice(
                "What would you like to do with this plan?",
                choices=[
                    "🚀 Generate Python code and render video",
                    "✏️  Request changes / adjustments to this plan",
                    "📄 View raw JSON plan",
                    "❌ Exit",
                ],
            )
            if "Generate" in choice or "🚀" in choice:
                self.generate_code_from_plan()
                break
            elif "Request changes" in choice or "✏️" in choice:
                changes = self.prompt_text("Describe the changes or adjustments you'd like:")
                if changes:
                    self.refine_plan(changes)
                    self.display_plan_summary(self.current_plan)
            elif "View raw JSON" in choice or "📄" in choice:
                if HAS_RICH and self.console:
                    self.console.print(Syntax(self.current_plan.to_json(), "json", theme="monokai", word_wrap=True))
                else:
                    print(self.current_plan.to_json())
            elif "Exit" in choice or "❌" in choice:
                print("Exiting interactive session.")
                break

    def refine_plan(self, feedback: str):
        """Ask the model to update the current ScenePlan based on user feedback."""
        if not self.current_plan:
            return
        self.log("TASK", f"Refining plan based on feedback: '{feedback}'...")
        prompt = (
            f"Current ScenePlan:\n{self.current_plan.to_json()}\n\n"
            f"User requested adjustments:\n{feedback}\n\n"
            "Update the ScenePlan accordingly. Output ONLY valid JSON conforming to the ScenePlan schema."
        )
        self.log_prompt("You are an expert whiteboard animation director. Output only valid JSON.", prompt)
        resp = self.model.invoke(
            messages=[{"role": "user", "content": prompt}],
            system_message="You are an expert whiteboard animation director. Output only valid JSON.",
            response_format={"type": "json_object"},
        )
        try:
            self.current_plan = ScenePlan.from_json(resp)
            self.log("SUCCESS", "Plan successfully updated!", color="\033[92m")
        except Exception as e:
            self.log("WARN", f"Could not update plan ({e}). Keeping existing plan.", color="\033[93m")

    def display_plan_summary(self, plan: ScenePlan):
        """Format and print an attractive summary of the plan using rich tree/panels or ANSI."""
        if HAS_RICH and self.console:
            self.console.print()
            desc = f"\n[italic]{plan.description}[/italic]" if plan.description else ""
            self.console.print(
                Panel(
                    f"[bold green]=== SCENE PLAN: {plan.title} ===[/bold green]\n"
                    f"[dim]Total Duration: {plan.total_duration:.1f}s | Resolution: {plan.width}x{plan.height} (16:9)[/dim]"
                    f"{desc}",
                    border_style="green",
                    title="🎬 ScenePlan Specification",
                )
            )

            tree = Tree(f"[bold cyan]{plan.title}[/bold cyan] [dim]({len(plan.scenes)} scenes)[/dim]")
            for scene in plan.scenes:
                scene_node = tree.add(
                    f"[bold yellow]Scene {scene.id}: {scene.title}[/bold yellow] [dim]({scene.duration:.1f}s)[/dim]"
                )
                if scene.drawables:
                    drawables_node = scene_node.add(f"[blue]Drawables ({len(scene.drawables)}):[/blue]")
                    for d in scene.drawables:
                        drawables_node.add(f"[magenta]{d.type}[/magenta] [dim]id='{d.id}'[/dim]")
                if scene.animations:
                    anim_node = scene_node.add(f"[green]Animations ({len(scene.animations)}):[/green]")
                    for a in scene.animations:
                        anim_node.add(
                            f"[cyan]{a.type}[/cyan] on '{a.drawable_id}' [dim](t={a.start_time:.1f}s, dur={a.duration:.1f}s)[/dim]"
                        )
            self.console.print(tree)
            self.console.print()
        else:
            bold = "\033[1m"
            green = "\033[92m"
            reset = "\033[0m"
            print(f"\n{bold}{green}=== SCENE PLAN: {plan.title} ==={reset}")
            print(f"Total Duration: {plan.total_duration:.1f}s | Resolution: {plan.width}x{plan.height} (16:9)")
            if plan.description:
                print(f"Overview: {plan.description}")

            for scene in plan.scenes:
                print(f"\n  {bold}Scene {scene.id}: {scene.title}{reset} ({scene.duration:.1f}s)")
                print(f"    Drawables ({len(scene.drawables)}):")
                for d in scene.drawables:
                    print(f"      - [{d.type}] id='{d.id}'")
                print(f"    Animations ({len(scene.animations)}):")
                for a in scene.animations:
                    print(f"      - {a.type} on '{a.drawable_id}' (t={a.start_time:.1f}s, dur={a.duration:.1f}s)")

    def generate_code_from_plan(self):
        """Compile plan into Python and execute."""
        if not self.current_plan:
            print("No plan available to generate code.")
            return

        self.log("TASK 3/4", "Compiling ScenePlan into Python code...")
        out_path = os.path.join(self.output_dir, "output.mp4")
        code = plan_to_python(self.current_plan, output_path=out_path)
        self.current_code = code

        # AST Lint check
        self.log("TASK 3.5", "Running static AST linter & guardrails...")
        diag = check_code(code)
        if not diag.is_valid:
            self.log("WARN", f"Linter detected issues: {diag.errors}", color="\033[93m")

        if HAS_RICH and self.console:
            lines = code.splitlines()
            preview = "\n".join(lines[:25])
            self.console.print(
                Panel(
                    Syntax(preview, "python", theme="monokai", line_numbers=True),
                    title=f"🐍 Generated Code Preview (Showing 25 of {len(lines)} lines)",
                    border_style="cyan",
                )
            )
        else:
            print("\nGenerated Code Preview (first 25 lines):")
            dim = "\033[2m"
            reset = "\033[0m"
            preview_lines = code.splitlines()[:25]
            print(f"{dim}" + "\n".join(preview_lines) + f"\n... ({len(code.splitlines()) - 25} more lines){reset}")

        self.execute_and_verify(code, out_path)

    def execute_and_verify(self, code: str, output_path: str):
        """Run code in subprocess and report live results."""
        self.log("TASK 4/4", f"Rendering animation to '{output_path}'...")
        print("Rendering frames (this may take a few seconds)...")
        res = self.executor.execute(code, expected_output=output_path)

        if res.success:
            if HAS_RICH and self.console:
                self.console.print(
                    Panel(
                        f"[bold green]SUCCESS![/bold green] Animation rendered in [bold]{res.execution_time:.2f}s[/bold]!\n"
                        f"Saved to: [bold underline]{os.path.abspath(output_path)}[/bold underline]",
                        title="🎉 Render Complete",
                        border_style="green",
                    )
                )
            else:
                green = "\033[92m"
                bold = "\033[1m"
                reset = "\033[0m"
                print(f"\n{bold}{green}SUCCESS! Animation rendered in {res.execution_time:.2f}s!{reset}")
                print(f"Output saved to: {os.path.abspath(output_path)}")

            if sys.stdin.isatty():
                next_action = self.prompt_choice(
                    "What would you like to do next?",
                    choices=[
                        "🎬 Plan and create another animation",
                        "❌ Exit",
                    ],
                )
                if "another animation" in next_action:
                    self.current_plan = None
                    self.current_code = None
                    topic = self.prompt_text("What whiteboard animation would you like to create?")
                    if topic:
                        self.handle_topic_turn(topic)
        else:
            if HAS_RICH and self.console:
                self.console.print(
                    Panel(
                        f"[bold red]Execution Error (exit code {res.returncode}):[/bold red]\n\n"
                        f"{res.error_summary or res.stderr}",
                        title="❌ Rendering Failed",
                        border_style="red",
                    )
                )
            else:
                red = "\033[91m"
                reset = "\033[0m"
                print(f"\n{red}Execution Error (exit code {res.returncode}):{reset}")
                print(res.error_summary or res.stderr)

            if sys.stdin.isatty():
                choice = self.prompt_choice(
                    "How would you like to resolve this error?",
                    choices=[
                        "🛠️  Ask model to fix the code automatically",
                        "✏️  Adjust the plan and recompile",
                        "📄 View full generated code",
                        "❌ Exit",
                    ],
                )
                if "fix the code" in choice or "🛠️" in choice:
                    self.auto_repair_code(code, res.error_summary or res.stderr, output_path)
                elif "Adjust the plan" in choice or "✏️" in choice:
                    changes = self.prompt_text("What would you like to adjust in the plan?")
                    if changes:
                        self.refine_plan(changes)
                        self.generate_code_from_plan()
                elif "View full generated code" in choice or "📄" in choice:
                    if HAS_RICH and self.console:
                        self.console.print(Syntax(code, "python", theme="monokai", line_numbers=True))
                    else:
                        print(code)

    def auto_repair_code(self, broken_code: str, error_message: str, output_path: str):
        """Ask model to repair broken Python script."""
        self.log("TASK", "Requesting model to fix execution error...")
        repair_prompt = (
            f"The following handanim Python script produced an error:\n```python\n{broken_code}\n```\n\n"
            f"Error traceback:\n{error_message}\n\n"
            f"Fix the error and return ONLY the complete corrected Python code enclosed in ```python ``` code blocks."
        )
        self.log_prompt("You are a Python debugging expert for handanim animations.", repair_prompt)
        resp = self.model.invoke(
            messages=[{"role": "user", "content": repair_prompt}],
            system_message="You are a Python debugging expert for handanim animations. Output only the corrected code block.",
        )
        code_match = re.search(r"```python\s*(.*?)\s*```", resp, re.DOTALL)
        fixed_code = code_match.group(1) if code_match else resp.strip()
        self.current_code = fixed_code
        self.execute_and_verify(fixed_code, output_path)
