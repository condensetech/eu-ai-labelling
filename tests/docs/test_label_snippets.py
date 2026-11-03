"""The Labels the references tell the agent to make are well made.

Following the references faithfully must give a Label that passes the
tests' checks (`label_checks.py`). Two sources are checked:

- every `snippet` and `copy-icons` command in the references, run exactly
  as written with only its placeholders filled in, from inside a project;
- every Markdown example of a Label shown in the references.
"""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from helpers import ICONS_DIR, SKILL_DIR, fenced
from label_checks import label_problems

REFERENCES = ("text.md", "creative-work.md", "site.md")
# The references that print a phrase with `wording`.
WORDING_REFERENCES = ("creative-work.md", "site.md", "update-references.md")
MARKER = re.compile(r"<!--\s*eu-ai-labelling:\s*(generated|modified)\s*-->")
FILL = {
    "<generated|modified>": "generated",
    "<text label>": "Image generated with AI",
    "<icon name>": "AI",
    "<icon path>": "assets/ai-basic-black.svg",
    "<assets folder>": "assets",
    "<static folder>": "public",
    "<code>": "en",
}
# Pages in the document's language, declared as the tool reads it.
PAGES = {
    "html": ("page.html", '<html lang="en"><body>\n<h1>Title</h1>\n{body}\n<p>Body.</p>\n</body></html>\n'),
    "markdown": ("post.md", "---\nlang: en\n---\n\n# Title\n\n{body}\n\nBody.\n"),
}


def documented(subcommand: str, references=REFERENCES) -> list[tuple[str, str]]:
    """(reference, command line) for each `label_tool.py <subcommand>` command."""
    found = []
    for name in references:
        for block in fenced((SKILL_DIR / "references" / name).read_text()):
            for line in block.splitlines():
                if "label_tool.py" in line and f" {subcommand} " in line + " ":
                    found.append((name, line.strip()))
    return found


def argv(command: str, document: str = "post.md") -> list[str]:
    command = command.replace("<skill folder>", str(SKILL_DIR))
    command = command.replace("<document>", document).replace("<page>", document)
    for placeholder in [k for k in FILL if " " in k]:  # e.g. `<assets folder>`, whole before splitting
        command = command.replace(f'"{placeholder}"', placeholder).replace(placeholder, shlex.quote(FILL[placeholder]))
    tokens = []
    for token in shlex.split(command):
        token = FILL.get(token, token)
        assert "<" not in token, f"unfilled placeholder {token!r} in {command!r}"
        tokens.append(token)
    return tokens


def run(command: str, cwd: Path, document: str = "post.md") -> dict:
    import json

    tokens = argv(command, document)
    assert shutil.which(tokens[0]), f"{tokens[0]} must be installed"
    proc = subprocess.run(tokens, cwd=cwd, capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, f"{command}\n{proc.stdout}\n{proc.stderr}"
    return json.loads(proc.stdout)


SNIPPET_COMMANDS = documented("snippet")
COPY_COMMANDS = documented("copy-icons")
WORDING_COMMANDS = documented("wording", WORDING_REFERENCES)


def test_the_references_print_labels_and_copy_icons_with_label_tool():
    assert {name for name, _ in SNIPPET_COMMANDS} == {"text.md", "creative-work.md"}
    assert {name for name, _ in COPY_COMMANDS} == set(REFERENCES)
    assert len(SNIPPET_COMMANDS) >= 4


@pytest.mark.parametrize("reference, command", COPY_COMMANDS, ids=[f"{n}:{i}" for i, (n, _) in enumerate(COPY_COMMANDS)])
def test_a_copy_command_run_as_written_copies_the_official_icons(tmp_path, reference, command):
    project = tmp_path / "site"
    project.mkdir()

    result = run(command, project)

    assert result["copied"]
    for path in result["copied"]:
        copied = project / path if not Path(path).is_absolute() else Path(path)
        assert copied.resolve().is_relative_to(project.resolve())
        assert copied.read_bytes() == (ICONS_DIR / copied.name).read_bytes()


@pytest.mark.parametrize("reference, command", SNIPPET_COMMANDS, ids=[f"{n}:{i}" for i, (n, _) in enumerate(SNIPPET_COMMANDS)])
def test_a_snippet_command_run_as_written_prints_a_well_made_label(tmp_path, reference, command):
    project = tmp_path / "site"
    project.mkdir()
    run("uv run <skill folder>/scripts/label_tool.py copy-icons --to <assets folder>", project)
    name, template = PAGES["html" if "--format html" in command else "markdown"]
    page = project / name
    page.write_text(template.format(body=""))  # the document the Label goes into, in its language
    printed = run(command, project, name)
    snippet = printed["snippet"]
    assert printed["language"] == "en" and printed["language_from"] == "document", printed
    caption = "--as caption" in command
    if "--format html" in command:
        body = ('<img src="satire.png" alt="A cartoon">\n' if caption else "") + snippet
    else:
        body = ("![A cartoon](satire.png)\n\n" if caption else "") + snippet
    page.write_text(template.format(body=body))

    result = label_problems(page, project)

    assert result["labels"] == 1
    assert result["problems"] == [], snippet


def test_the_references_print_the_wording_with_label_tool():
    assert {name for name, _ in WORDING_COMMANDS} == set(WORDING_REFERENCES)


@pytest.mark.parametrize("reference, command", WORDING_COMMANDS, ids=[f"{n}:{i}" for i, (n, _) in enumerate(WORDING_COMMANDS)])
def test_a_wording_command_run_as_written_prints_the_phrases(tmp_path, reference, command):
    name, template = PAGES["markdown"]
    (tmp_path / name).write_text(template.format(body=""))

    result = run(command, tmp_path, name)

    assert result["language"] == "en"
    assert result["image"] in ("Image generated with AI", "Image modified with AI")
    assert result["label"] in ("Generated with AI", "Modified with AI") and result["icon_name"] == "AI"


EXAMPLES = [
    (f"{name}:{i}", body)
    for name in REFERENCES
    for i, body in enumerate(fenced((SKILL_DIR / "references" / name).read_text(), "markdown"))
    if MARKER.search(body)
]


def test_the_references_show_a_markdown_example_of_each_label():
    assert len(EXAMPLES) >= 2, [e[0] for e in EXAMPLES]


@pytest.mark.parametrize("body", [e[1] for e in EXAMPLES], ids=[e[0] for e in EXAMPLES])
def test_a_markdown_example_is_a_well_made_label(tmp_path, body):
    project = tmp_path / "site"
    (project / "assets").mkdir(parents=True)
    (project / "assets" / "ai-basic-black.svg").write_bytes((ICONS_DIR / "ai-basic-black.svg").read_bytes())
    page = project / "post.md"
    page.write_text(f"# Title\n\n{body}\nBody.\n")

    result = label_problems(page, project)

    assert result["labels"] >= 1
    assert result["problems"] == [], body
