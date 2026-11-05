"""Prompt template registry and versioning manager."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class PromptTemplate:
    """A versioned prompt specification."""

    name: str
    version: str
    description: str
    system_message: str
    template: str

    def format(self, **kwargs: Any) -> tuple[str, str]:
        """Format the prompt template with arguments.

        Returns:
            A tuple of (system_message, formatted_user_message).
        """
        # Safely interpolate missing keys by leaving them or empty
        user_message = self.template
        for k, v in kwargs.items():
            user_message = user_message.replace(f"{{{k}}}", str(v))
        return self.system_message, user_message


class PromptManager:
    """Manages prompt template loading and version discovery."""

    def __init__(self, prompts_dir: Path | None = None):
        self.prompts_dir = prompts_dir or Path(__file__).resolve().parent

    def get(self, name: str, version: str = "v1") -> PromptTemplate:
        """Load a prompt template by name and version (e.g. name='big_picture', version='v1')."""
        yaml_path = self.prompts_dir / version / f"{name}.yaml"
        if not yaml_path.exists():
            # Fallback check for legacy .txt file
            txt_path = self.prompts_dir / f"{name}.txt"
            if txt_path.exists():
                content = txt_path.read_text(encoding="utf-8")
                return PromptTemplate(
                    name=name,
                    version="legacy",
                    description="Legacy text prompt",
                    system_message="",
                    template=content,
                )
            raise FileNotFoundError(f"Prompt template '{name}' not found under version '{version}' ({yaml_path}).")

        raw_text = yaml_path.read_text(encoding="utf-8")
        if yaml is not None:
            data = yaml.safe_load(raw_text) or {}
        else:
            # Minimal fallback parser if yaml is absent
            data = self._simple_yaml_parse(raw_text)

        return PromptTemplate(
            name=name,
            version=str(data.get("version", version)),
            description=str(data.get("description", "")),
            system_message=str(data.get("system_message", "")).strip(),
            template=str(data.get("template", "")).strip(),
        )

    def list_prompts(self) -> list[dict[str, str]]:
        """List all discovered prompt templates across version directories."""
        results = []
        for version_dir in sorted(self.prompts_dir.glob("v*")):
            if version_dir.is_dir():
                for yaml_file in sorted(version_dir.glob("*.yaml")):
                    prompt = self.get(yaml_file.stem, version=version_dir.name)
                    results.append(
                        {
                            "name": prompt.name,
                            "version": prompt.version,
                            "path": str(yaml_file),
                            "description": prompt.description,
                        }
                    )
        return results

    @staticmethod
    def _simple_yaml_parse(text: str) -> dict[str, str]:
        """Lightweight key-value and multiline block string parser."""
        data: dict[str, str] = {}
        current_key: str | None = None
        current_lines: list[str] = []

        for line in text.splitlines():
            if ":" in line and not line.startswith(" ") and not line.startswith("\t"):
                if current_key is not None:
                    data[current_key] = "\n".join(current_lines).strip()
                    current_lines = []
                key, rest = line.split(":", 1)
                current_key = key.strip()
                rest = rest.strip()
                if rest and rest != "|":
                    current_lines.append(rest.strip("\"'"))
            elif current_key is not None:
                current_lines.append(line)

        if current_key is not None:
            data[current_key] = "\n".join(current_lines).strip()

        return data
