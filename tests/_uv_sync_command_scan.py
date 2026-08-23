"""Detection of literal `uv sync` shell commands inside markdown documents.

Shared by `tests/test_markdown_install_instructions_all_packages.py` (the
repository-wide guard) and `tests/test_contribution_governance_docs.py`
(which pins `CONTRIBUTING.md` specifically, for GH-19's AC4). Both need the
same notion of "this line shows a runnable `uv sync` command", and keeping
that notion in one place is what stops the two from drifting apart -- they
previously carried a copy each of the line-anchored regex
`r"^\\s*\\$?\\s*uv sync\\b"`, and both copies shared the same blind spot:
neither saw a chained command such as `cd frontend && uv sync`, even though
both modules' documentation claimed to cover any runnable `uv sync` command.

What counts as a command
------------------------

A `uv sync` invocation is recognized in two positions:

1. **At the start of a line, anywhere in the document** -- optionally behind
   a copy-pasted shell prompt (`$ `) and leading indentation. A line that
   *begins* with `uv sync` reads as a copy-pasteable command wherever it
   sits, so this position is honoured inside and outside fenced code blocks
   alike. This is exactly what the two previous per-module regexes matched,
   so nothing that was guarded before is guarded less now.
2. **After a shell separator (`&&`, `||`, `;`, `|`)** -- but only inside a
   fenced code block, where the line is unambiguously shell. Outside a
   fence those same characters are ordinary punctuation, and splitting on
   them would invent commands that do not exist: a Markdown table row
   (`| uv sync | installs everything |`) would read as a shell pipeline, and
   an ordinary sentence's semicolon as a command chain.

Prose that merely *mentions* the command ("run `uv sync --all-packages` to
install") matches neither position: the mention sits mid-sentence rather
than at the start of a line or segment, and its opening backtick keeps it
from starting one.

Splitting on separators is quote-aware, which it has to be: `README.md`'s
PowerShell block opens with `$env:Path = "$env:USERPROFILE\\.local\\bin;$env:Path"`,
whose `;` sits inside a string literal. A naive `str.split(";")` would tear
that line in half. `_split_shell_segments` tracks quoting and leaves it
whole.
"""

from __future__ import annotations

import re
import shlex
from typing import NamedTuple

# An opening or closing fenced-code-block delimiter. CommonMark allows up to
# three leading spaces, and a fence may use backticks or tildes.
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")

# A `uv sync` invocation at the very start of a shell segment, optionally
# behind indentation and a copy-pasted prompt (`$ `). Group 1 is the command
# itself with that prompt and indentation removed, so callers tokenize the
# command rather than whatever preceded it on the line.
_UV_SYNC_COMMAND_RE = re.compile(r"^\s*\$?\s*(uv\s+sync\b.*)$")

# Characters that begin a shell separator. A maximal run of them is treated
# as one boundary, which covers `;`, `|`, `&&`, `||` and `|&` alike without
# enumerating the operators individually.
_SEPARATOR_CHARS = ";&|"

_QUOTE_CHARS = "'\""


class UvSyncCommand(NamedTuple):
    """One literal `uv sync` invocation found in a markdown document.

    `line` is the whole source line, stripped, for use in failure messages
    so a reader sees the command in the context it was written in.
    `command` is just the `uv sync ...` segment, with any shell prompt and
    any preceding chained command removed, so that tokenizing it inspects
    the flags of *this* invocation -- in `uv sync --all-packages && uv sync`
    the second invocation is bare, and checking the full line would let it
    borrow the first one's flag.
    """

    line_number: int
    line: str
    command: str


def _fenced_code_block_line_numbers(markdown_text: str) -> set[int]:
    """Return the 1-indexed numbers of every line of `markdown_text` that
    sits inside a fenced code block, excluding the fence delimiters
    themselves. A fence is closed only by a delimiter using the same
    character it was opened with, so a ``` block containing ~~~ stays open.
    """
    inside: set[int] = set()
    fence_char: str | None = None
    for number, line in enumerate(markdown_text.splitlines(), start=1):
        match = _FENCE_RE.match(line)
        if fence_char is None:
            if match:
                fence_char = match.group(1)[0]
            continue
        if match and match.group(1)[0] == fence_char:
            fence_char = None
            continue
        inside.add(number)
    return inside


def _split_shell_segments(line: str) -> list[str]:
    """Split `line` into command segments on unquoted shell separators
    (`;`, `|`, `&&`, `||`).

    Quoting is honoured: a separator inside single or double quotes is
    ordinary text and does not split (see this module's docstring for the
    real `README.md` line that depends on this). Backslash escapes the next
    character outside quotes and inside double quotes, matching POSIX
    shells closely enough for the purpose here, which is only to find where
    one command ends and the next begins.

    The first element is always the part of the line before any separator,
    so a caller that checks every segment also checks the start of the line.
    """
    segments: list[str] = []
    current: list[str] = []
    quote: str | None = None
    index = 0
    length = len(line)

    while index < length:
        char = line[index]

        if quote is not None:
            current.append(char)
            if char == "\\" and quote == '"' and index + 1 < length:
                current.append(line[index + 1])
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue

        if char == "\\" and index + 1 < length:
            current.append(char)
            current.append(line[index + 1])
            index += 2
            continue

        if char in _QUOTE_CHARS:
            quote = char
            current.append(char)
            index += 1
            continue

        if char in _SEPARATOR_CHARS:
            while index < length and line[index] in _SEPARATOR_CHARS:
                index += 1
            segments.append("".join(current))
            current = []
            continue

        current.append(char)
        index += 1

    segments.append("".join(current))
    return segments


def find_uv_sync_commands(markdown_text: str) -> list[UvSyncCommand]:
    """Return every literal `uv sync` invocation in `markdown_text`, in
    document order.

    See this module's docstring for the two positions an invocation is
    recognized in and why the second one is restricted to fenced code
    blocks.
    """
    fenced_line_numbers = _fenced_code_block_line_numbers(markdown_text)
    found: list[UvSyncCommand] = []

    for number, line in enumerate(markdown_text.splitlines(), start=1):
        segments = _split_shell_segments(line) if number in fenced_line_numbers else [line]
        for segment in segments:
            match = _UV_SYNC_COMMAND_RE.match(segment)
            if match:
                found.append(UvSyncCommand(number, line.strip(), match.group(1).strip()))

    return found


def command_tokens(command: str) -> list[str]:
    """Return the shell tokens of `command`.

    Falls back to a whitespace split when `shlex` refuses the string --
    `README.md` already contains shell lines `shlex` rejects (a `psql`
    example ends in a bare backslash line-continuation), and a `uv sync`
    command that cannot be tokenized must still be inspected rather than
    silently skipped or raised through the caller as a `ValueError`. The
    fallback is safe for the only thing callers look for here: `uv` flags
    such as `--all-packages` are bare, unquoted tokens, so whitespace
    splitting finds them exactly where `shlex` would.
    """
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()
