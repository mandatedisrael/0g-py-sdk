#!/usr/bin/env python3
"""Compare the Python storage SDK with the upstream 0G Storage TS starter kit.

The checker is intentionally dependency-free. It fetches or reuses a local
upstream checkout, extracts public API-like surface area from TypeScript and
Python sources, runs a small set of feature probes, then writes Markdown and
JSON reports that are useful for maintainer review.
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import datetime as dt
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


DEFAULT_UPSTREAM_URL = "https://github.com/0gfoundation/0g-storage-ts-starter-kit.git"
DEFAULT_REF = "master"
DEFAULT_PYTHON_ROOT = "0g_py_storage"
DEFAULT_CACHE_DIR = ".cache/storage_ts_starter_kit"
DEFAULT_REPORT_MD = "reports/storage_parity_report.md"
DEFAULT_REPORT_JSON = "reports/storage_parity_report.json"
GIT_TIMEOUT_SECONDS = 300

IGNORED_DIR_NAMES = {
    ".git",
    "node_modules",
    "lib.commonjs",
    "lib.esm",
    "types",
    "dist",
    "coverage",
    "__pycache__",
    ".pytest_cache",
    "tests",
    ".venv",
    "venv",
    "env",
    "build",
    "0g_storage_sdk.egg-info",
    "typechain",
}

TS_SDK_HINTS = ("src", "scripts", "README.md", "package.json", ".env.example")
TS_PACKAGE_HINTS = (
    "src",
    "scripts",
    "web-ui",
    "web",
    "README.md",
    "package.json",
    ".env.example",
)
PYTHON_DOC_HINTS = (
    "0g_py_storage/README.md",
    "0g_py_storage/simple_upload.py",
    "0g_py_storage/simple_download.py",
    "0g_py_storage/scripts",
)

FEATURE_PROBES = [
    {
        "id": "file_upload",
        "label": "File upload",
        "scopes": ["sdk", "package"],
        "ts": [r"uploadFile", r"Indexer", r"ZgFile\.fromFilePath"],
        "py": [r"upload", r"Indexer", r"ZgFile\.from_file_path"],
    },
    {
        "id": "file_download",
        "label": "File download",
        "scopes": ["sdk", "package"],
        "ts": [r"downloadFile", r"indexer\.download", r"downloadToBlob"],
        "py": [r"download", r"Downloader", r"download_segment"],
    },
    {
        "id": "mem_data_upload",
        "label": "In-memory data upload",
        "scopes": ["sdk", "package"],
        "ts": [r"uploadData", r"MemData"],
        "py": [r"from_bytes", r"ZgFile\.from_bytes"],
    },
    {
        "id": "batch_upload",
        "label": "Batch upload wrapper",
        "scopes": ["sdk", "package"],
        "ts": [r"batchUpload", r"batch-upload"],
        "py": [r"batch_upload", r"splitable_upload", r"Uploader"],
    },
    {
        "id": "client_side_encryption",
        "label": "Client-side encryption",
        "scopes": ["sdk", "package"],
        "ts": [r"aes256", r"ecies", r"EncryptionHeader"],
        "py": [r"aes256", r"ecies", r"EncryptionHeader"],
    },
    {
        "id": "peek_header",
        "label": "Encryption header peek",
        "scopes": ["sdk", "package"],
        "ts": [r"peekHeader", r"peek-header"],
        "py": [r"peek_header", r"EncryptionHeader"],
    },
    {
        "id": "network_modes",
        "label": "Network and storage modes",
        "scopes": ["sdk", "package"],
        "ts": [r"StorageMode", r"turbo", r"standard"],
        "py": [r"turbo", r"standard", r"indexer-storage-testnet-standard"],
    },
    {
        "id": "merkle_proofs",
        "label": "Merkle roots and proofs",
        "scopes": ["sdk", "package"],
        "ts": [r"merkleTree", r"rootHash", r"proof"],
        "py": [r"merkle_tree", r"root_hash", r"Proof"],
    },
    {
        "id": "kv_storage",
        "label": "KV storage",
        "scopes": ["sdk", "package"],
        "ts": [r"\bKV\b", r"key-value", r"stream"],
        "py": [r"KvClient", r"Batcher", r"StreamDataBuilder"],
    },
    {
        "id": "cli_scripts",
        "label": "CLI scripts",
        "scopes": ["package"],
        "ts": [r"commander", r"npm run upload", r"npm run download"],
        "py": [r"argparse", r"simple_upload", r"simple_download"],
    },
    {
        "id": "web_ui",
        "label": "Browser web UI",
        "scopes": ["package"],
        "ts": [r"MetaMask", r"wallet", r"drag-and-drop"],
        "py": [r"MetaMask", r"wallet", r"drag-and-drop"],
    },
]

ACTION_DOMAIN_HINTS = {
    "file_upload": ["upload", "network", "data", "shared"],
    "file_download": ["download", "network", "data", "shared"],
    "mem_data_upload": ["data", "upload", "shared"],
    "batch_upload": ["upload", "shared"],
    "client_side_encryption": ["encryption", "upload", "download", "shared"],
    "peek_header": ["encryption", "download", "shared"],
    "network_modes": ["config", "network"],
    "merkle_proofs": ["merkle", "data"],
    "kv_storage": ["kv_storage"],
    "cli_scripts": ["cli"],
    "web_ui": ["web_ui"],
}


@dataclasses.dataclass(frozen=True)
class SurfaceItem:
    ecosystem: str
    kind: str
    name: str
    path: str
    line: int
    domain: str
    parent: str = ""
    signature: str = ""

    @property
    def qualified_name(self) -> str:
        if self.parent:
            return f"{self.parent}.{self.name}"
        return self.name

    @property
    def canonical_name(self) -> str:
        return canonicalize(self.qualified_name)


def canonicalize(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def relpath(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def run_git(args: list[str], cwd: Path | None = None) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"git {' '.join(args)} timed out after {GIT_TIMEOUT_SECONDS}s") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout.strip()


def ensure_upstream_checkout(
    *,
    ts_path: Path | None,
    cache_dir: Path,
    upstream_url: str,
    ref: str,
    refresh: bool,
    no_fetch: bool,
) -> Path:
    if ts_path:
        if not ts_path.exists():
            raise FileNotFoundError(f"TypeScript SDK path does not exist: {ts_path}")
        return ts_path.resolve()

    cache_dir = cache_dir.resolve()
    if cache_dir.exists() and not (cache_dir / ".git").exists():
        raise RuntimeError(f"Cache path exists but is not a git checkout: {cache_dir}")

    if not cache_dir.exists():
        if no_fetch:
            raise RuntimeError("--no-fetch was set and no cached upstream checkout exists")
        cache_dir.parent.mkdir(parents=True, exist_ok=True)
        run_git(["clone", "--depth", "1", "--filter=blob:none", "--branch", ref, upstream_url, str(cache_dir)])
        return cache_dir

    if refresh and not no_fetch:
        run_git(["fetch", "--depth", "1", "origin", ref], cwd=cache_dir)
        run_git(["checkout", "FETCH_HEAD"], cwd=cache_dir)

    return cache_dir


def upstream_metadata(root: Path) -> dict[str, str]:
    metadata = {
        "path": str(root),
        "commit": "",
        "version": "",
        "package": "",
    }
    try:
        metadata["commit"] = run_git(["rev-parse", "HEAD"], cwd=root)
    except Exception:
        pass

    package_json = root / "package.json"
    if package_json.exists():
        try:
            package = json.loads(package_json.read_text(encoding="utf-8"))
            metadata["version"] = str(package.get("version", ""))
            metadata["package"] = str(package.get("name", ""))
        except json.JSONDecodeError:
            pass
    return metadata


def iter_files(root: Path, suffixes: tuple[str, ...], include_roots: tuple[str, ...] | None = None) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        parts = set(path.parts)
        if parts & IGNORED_DIR_NAMES:
            continue
        if include_roots:
            relative = relpath(path, root)
            if not any(relative == hint or relative.startswith(hint.rstrip("/") + "/") for hint in include_roots):
                continue
        yield path


def domain_for_path(path: str) -> str:
    normalized = path.replace("-", "_").lower()
    if normalized.startswith("scripts/") or "/scripts/" in normalized:
        return "cli"
    if normalized.startswith("web/") or "/web/" in normalized:
        return "web_ui"
    if "/kv/" in normalized or "storage_kv" in normalized or "stream" in normalized:
        return "kv_storage"
    if "encrypt" in normalized or "decrypt" in normalized or "header" in normalized:
        return "encryption"
    if "merkle" in normalized or "proof" in normalized:
        return "merkle"
    if "uploader" in normalized or "upload" in normalized:
        return "upload"
    if "downloader" in normalized or "download" in normalized:
        return "download"
    if "indexer" in normalized or "storage_node" in normalized or "node_selector" in normalized:
        return "network"
    if "file" in normalized or "blob" in normalized or "memdata" in normalized:
        return "data"
    if "config" in normalized:
        return "config"
    if "contract" in normalized or "flow" in normalized:
        return "contracts"
    if "utils" in normalized:
        return "utils"
    if "README" in path or path.endswith(".md"):
        return "docs"
    return "shared"


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def extract_ts_surface(root: Path, include_hints: tuple[str, ...]) -> list[SurfaceItem]:
    items: list[SurfaceItem] = []
    ts_files = list(iter_files(root, (".ts", ".tsx"), include_hints))
    for path in ts_files:
        relative = relpath(path, root)
        domain = domain_for_path(relative)
        text = path.read_text(encoding="utf-8", errors="ignore")
        items.extend(extract_ts_exports(text, relative, domain))
        items.extend(extract_ts_class_methods(text, relative, domain))
        items.extend(extract_ts_cli_commands(text, relative, domain))
    return dedupe_items(items)


def extract_ts_exports(text: str, path: str, domain: str) -> list[SurfaceItem]:
    patterns = [
        ("class", re.compile(r"^\s*export\s+(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)", re.MULTILINE)),
        ("interface", re.compile(r"^\s*export\s+interface\s+([A-Za-z_$][\w$]*)", re.MULTILINE)),
        ("type", re.compile(r"^\s*export\s+type\s+([A-Za-z_$][\w$]*)", re.MULTILINE)),
        ("enum", re.compile(r"^\s*export\s+enum\s+([A-Za-z_$][\w$]*)", re.MULTILINE)),
        ("function", re.compile(r"^\s*export\s+(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", re.MULTILINE)),
        ("constant", re.compile(r"^\s*export\s+const\s+([A-Za-z_$][\w$]*)\s*(?::|=)", re.MULTILINE)),
    ]
    items: list[SurfaceItem] = []
    for kind, pattern in patterns:
        for match in pattern.finditer(text):
            signature = text[match.start() : text.find("\n", match.start())].strip()
            items.append(SurfaceItem("typescript", kind, match.group(1), path, line_number(text, match.start()), domain, signature=signature))

    for match in re.finditer(r"^\s*export\s+\{([^}]+)\}", text, re.MULTILINE | re.DOTALL):
        for raw_name in match.group(1).split(","):
            name = raw_name.strip().split(" as ")[-1].strip()
            if name and re.match(r"^[A-Za-z_$][\w$]*$", name):
                items.append(SurfaceItem("typescript", "re_export", name, path, line_number(text, match.start()), domain))
    return items


def extract_ts_class_methods(text: str, path: str, domain: str) -> list[SurfaceItem]:
    class_pattern = re.compile(r"^\s*export\s+(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)", re.MULTILINE)
    method_pattern = re.compile(
        r"^\s*(?!(?:private|protected|constructor|if|for|while|switch|catch)\b)"
        r"(?:public\s+)?(?:async\s+)?(?:static\s+)?(?:override\s+)?"
        r"([A-Za-z_$][\w$]*)\s*(?:<[^>{}]+>)?\s*\(",
        re.MULTILINE,
    )
    items: list[SurfaceItem] = []
    for class_match in class_pattern.finditer(text):
        class_name = class_match.group(1)
        body_start = text.find("{", class_match.end())
        if body_start == -1:
            continue
        body_end = find_matching_brace(text, body_start)
        if body_end == -1:
            continue
        body = text[body_start + 1 : body_end]
        base_line = line_number(text, body_start + 1) - 1
        for method_match in method_pattern.finditer(body):
            name = method_match.group(1)
            if name.startswith("_") or name in {"super", "then", "catch", "finally"}:
                continue
            if brace_depth_before(body, method_match.start()) != 0:
                continue
            signature = body[method_match.start() : body.find("\n", method_match.start())].strip()
            items.append(
                SurfaceItem(
                    "typescript",
                    "method",
                    name,
                    path,
                    base_line + line_number(body, method_match.start()),
                    domain,
                    parent=class_name,
                    signature=signature,
                )
            )
    return items


def brace_depth_before(text: str, end: int) -> int:
    depth = 0
    in_string: str | None = None
    escaped = False
    for char in text[:end]:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            continue
        if char in {'"', "'", "`"}:
            in_string = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth = max(0, depth - 1)
    return depth


def find_matching_brace(text: str, open_index: int) -> int:
    depth = 0
    in_string: str | None = None
    escaped = False
    for index in range(open_index, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            continue
        if char in {'"', "'", "`"}:
            in_string = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return -1


def extract_ts_cli_commands(text: str, path: str, domain: str) -> list[SurfaceItem]:
    items: list[SurfaceItem] = []
    if domain != "cli":
        return items
    pattern = re.compile(r"\.command\(\s*['\"]([^'\"]+)['\"]")
    for match in pattern.finditer(text):
        command = match.group(1).split()[0]
        if command:
            items.append(SurfaceItem("typescript", "cli_command", command, path, line_number(text, match.start()), domain))
    return items


def extract_python_surface(root: Path, repo_root: Path) -> list[SurfaceItem]:
    items: list[SurfaceItem] = []
    for path in iter_files(root, (".py",)):
        relative = relpath(path, repo_root)
        domain = domain_for_path(relative)
        try:
            module = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError as exc:
            items.append(SurfaceItem("python", "parse_error", path.name, relative, exc.lineno or 1, domain, signature=str(exc)))
            continue
        items.extend(extract_python_ast(module, relative, domain))
    return dedupe_items(items)


def extract_python_ast(module: ast.Module, path: str, domain: str) -> list[SurfaceItem]:
    items: list[SurfaceItem] = []
    for node in module.body:
        if isinstance(node, ast.ClassDef) and is_public(node.name):
            items.append(SurfaceItem("python", "class", node.name, path, node.lineno, domain))
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and is_public_method(child.name):
                    signature = python_signature(child)
                    items.append(SurfaceItem("python", "method", child.name, path, child.lineno, domain, parent=node.name, signature=signature))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and is_public(node.name):
            items.append(SurfaceItem("python", "function", node.name, path, node.lineno, domain, signature=python_signature(node)))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    for exported in literal_string_list(node.value):
                        items.append(SurfaceItem("python", "export", exported, path, node.lineno, domain))
    return items


def is_public(name: str) -> bool:
    return not name.startswith("_")


def is_public_method(name: str) -> bool:
    return name != "__init__" and not name.startswith("_")


def python_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    args = [arg.arg for arg in node.args.args]
    return f"{prefix}{node.name}({', '.join(args)})"


def literal_string_list(node: ast.AST) -> list[str]:
    if isinstance(node, (ast.List, ast.Tuple)):
        values = []
        for element in node.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                values.append(element.value)
        return values
    return []


def dedupe_items(items: list[SurfaceItem]) -> list[SurfaceItem]:
    seen: set[tuple[str, str, str, str, str]] = set()
    unique: list[SurfaceItem] = []
    for item in items:
        key = (item.ecosystem, item.kind, item.qualified_name, item.path, item.domain)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return sorted(unique, key=lambda item: (item.domain, item.kind, item.qualified_name, item.path, item.line))


def load_text_corpus(root: Path, hints: tuple[str, ...]) -> str:
    chunks: list[str] = []
    for hint in hints:
        path = root / hint
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
        elif path.is_dir():
            for suffix in (".ts", ".tsx", ".js", ".mjs", ".md", ".py", ".json"):
                for child in iter_files(path, (suffix,)):
                    chunks.append(child.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def run_feature_probes(ts_root: Path, py_repo_root: Path, include_hints: tuple[str, ...], scope: str) -> list[dict[str, Any]]:
    ts_corpus = load_text_corpus(ts_root, include_hints)
    py_corpus = load_text_corpus(py_repo_root, PYTHON_DOC_HINTS + (DEFAULT_PYTHON_ROOT,))
    results = []
    for probe in FEATURE_PROBES:
        if scope not in probe.get("scopes", ["sdk", "package"]):
            continue
        ts_hits = pattern_hits(ts_corpus, probe["ts"])
        py_hits = pattern_hits(py_corpus, probe["py"])
        status = "matched"
        if ts_hits and not py_hits:
            status = "missing_in_python"
        elif ts_hits and py_hits and len(py_hits) < len(ts_hits):
            status = "needs_review"
        elif not ts_hits and py_hits:
            status = "python_only"
        results.append(
            {
                "id": probe["id"],
                "label": probe["label"],
                "status": status,
                "ts_hits": ts_hits,
                "python_hits": py_hits,
            }
        )
    return results


def pattern_hits(corpus: str, patterns: list[str]) -> list[str]:
    hits = []
    for pattern in patterns:
        if re.search(pattern, corpus, flags=re.IGNORECASE | re.MULTILINE):
            hits.append(pattern)
    return hits


def compare_surfaces(ts_items: list[SurfaceItem], py_items: list[SurfaceItem]) -> dict[str, Any]:
    ts_by_key = defaultdict(list)
    py_by_key = defaultdict(list)
    ts_by_name = defaultdict(list)
    py_by_name = defaultdict(list)

    for item in ts_items:
        ts_by_key[(item.domain, item.canonical_name)].append(item)
        ts_by_name[item.canonical_name].append(item)
    for item in py_items:
        py_by_key[(item.domain, item.canonical_name)].append(item)
        py_by_name[item.canonical_name].append(item)

    matched: list[dict[str, Any]] = []
    needs_review: list[dict[str, Any]] = []
    ts_only: list[SurfaceItem] = []
    py_only: list[SurfaceItem] = []

    for key, ts_group in ts_by_key.items():
        py_group = py_by_key.get(key, [])
        if py_group:
            matched.append(pair_summary(ts_group[0], py_group[0], "domain_and_name"))
            continue
        candidates = py_by_name.get(key[1], [])
        if candidates:
            needs_review.append(pair_summary(ts_group[0], candidates[0], "name_only"))
        else:
            ts_only.extend(ts_group)

    for key, py_group in py_by_key.items():
        if key not in ts_by_key and key[1] not in ts_by_name:
            py_only.extend(py_group)

    return {
        "matched": matched,
        "needs_review": [item_to_dict(item) if isinstance(item, SurfaceItem) else item for item in needs_review],
        "ts_only": [item_to_dict(item) for item in rank_missing_items(ts_only)],
        "python_only": [item_to_dict(item) for item in sorted(py_only, key=lambda item: (item.domain, item.kind, item.qualified_name))],
    }


def pair_summary(ts_item: SurfaceItem, py_item: SurfaceItem, match_type: str) -> dict[str, Any]:
    return {
        "match_type": match_type,
        "typescript": item_to_dict(ts_item),
        "python": item_to_dict(py_item),
    }


def item_to_dict(item: SurfaceItem) -> dict[str, Any]:
    return {
        "ecosystem": item.ecosystem,
        "kind": item.kind,
        "name": item.name,
        "qualified_name": item.qualified_name,
        "path": item.path,
        "line": item.line,
        "domain": item.domain,
        "signature": item.signature,
    }


def rank_missing_items(items: list[SurfaceItem]) -> list[SurfaceItem]:
    weight_by_kind = {
        "class": 0,
        "function": 1,
        "method": 2,
        "interface": 3,
        "type": 4,
        "enum": 5,
        "cli_command": 6,
        "constant": 7,
        "re_export": 8,
    }
    return sorted(items, key=lambda item: (item.domain, weight_by_kind.get(item.kind, 99), item.qualified_name, item.path))


def build_action_items(feature_probes: list[dict[str, Any]], comparison: dict[str, Any]) -> list[dict[str, Any]]:
    action_items: list[dict[str, Any]] = []
    actionable_statuses = {"missing_in_python", "needs_review"}
    for probe in feature_probes:
        if probe["status"] not in actionable_statuses:
            continue

        priority = "P1" if probe["status"] == "missing_in_python" else "P2"
        domain_hints = ACTION_DOMAIN_HINTS.get(probe["id"], [])
        upstream_refs = related_refs(comparison["ts_only"], domain_hints, probe["ts_hits"], limit=8)
        python_refs = related_refs(comparison["python_only"], domain_hints, probe["python_hits"], limit=8)
        review_refs = related_review_refs(comparison["needs_review"], domain_hints, limit=5)

        action_items.append(
            {
                "priority": priority,
                "feature_id": probe["id"],
                "title": probe["label"],
                "status": probe["status"],
                "why": action_why(probe["status"]),
                "upstream_evidence_patterns": probe["ts_hits"],
                "python_evidence_patterns": probe["python_hits"],
                "upstream_refs": upstream_refs,
                "python_refs": python_refs,
                "review_refs": review_refs,
                "suggested_next_step": suggested_next_step(probe["status"], probe["label"]),
                "acceptance_criteria": [
                    "Confirm whether the upstream behavior is a real Python SDK parity requirement.",
                    "If porting, implement the Python API or behavior with tests and docs/examples where user-facing.",
                    "If already covered or intentionally different, update the parity tracker with the decision and rationale.",
                    "Rerun this parity checker and the relevant Python test suite after changes.",
                ],
            }
        )
    return action_items


def action_why(status: str) -> str:
    if status == "missing_in_python":
        return "Upstream evidence was found, but the checker found no matching Python evidence."
    return "Both sides have some evidence, but the match is incomplete or name-only and needs source review."


def suggested_next_step(status: str, label: str) -> str:
    if status == "missing_in_python":
        return f"Start by reading the upstream implementation for {label}, then decide whether to port it into Python."
    return f"Compare the upstream and Python implementations for {label}; decide whether the Python behavior is complete."


def related_refs(
    items: list[dict[str, Any]],
    domain_hints: list[str],
    patterns: list[str],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    pattern_terms = [canonicalize(pattern) for pattern in patterns if pattern]
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in items:
        score = 0
        if item["domain"] in domain_hints:
            score += 4
        text = canonicalize(" ".join([item["qualified_name"], item["path"], item.get("signature", "")]))
        if any(term and term in text for term in pattern_terms):
            score += 3
        if item["kind"] in {"class", "function", "method"}:
            score += 1
        if score:
            scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["domain"], pair[1]["kind"], pair[1]["qualified_name"]))
    return [item for _, item in scored[:limit]]


def related_review_refs(
    pairs: list[dict[str, Any]],
    domain_hints: list[str],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    refs = []
    for pair in pairs:
        ts_item = pair["typescript"]
        py_item = pair["python"]
        if ts_item["domain"] in domain_hints or py_item["domain"] in domain_hints:
            refs.append(pair)
    return refs[:limit]


def build_report(
    *,
    upstream: dict[str, str],
    ts_items: list[SurfaceItem],
    py_items: list[SurfaceItem],
    comparison: dict[str, Any],
    feature_probes: list[dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    missing_features = [probe for probe in feature_probes if probe["status"] == "missing_in_python"]
    review_features = [probe for probe in feature_probes if probe["status"] == "needs_review"]
    action_items = build_action_items(feature_probes, comparison)
    return {
        "generated_at": generated_at,
        "upstream": upstream,
        "config": {
            "upstream_url": args.upstream_url,
            "ref": args.ref,
            "scope": args.scope,
            "git_timeout": args.git_timeout,
            "python_root": str(args.python_root),
            "ts_path": str(args.ts_path) if args.ts_path else "",
        },
        "summary": {
            "typescript_surface_count": len(ts_items),
            "python_surface_count": len(py_items),
            "matched_count": len(comparison["matched"]),
            "needs_review_count": len(comparison["needs_review"]),
            "ts_only_count": len(comparison["ts_only"]),
            "python_only_count": len(comparison["python_only"]),
            "missing_feature_count": len(missing_features),
            "review_feature_count": len(review_features),
        },
        "action_items": action_items,
        "feature_probes": feature_probes,
        "comparison": comparison,
    }


def render_markdown(report: dict[str, Any], max_items: int) -> str:
    upstream = report["upstream"]
    summary = report["summary"]
    comparison = report["comparison"]
    lines = [
        "# Storage SDK Parity Report",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Upstream: `{upstream.get('package') or 'unknown'}` `{upstream.get('version') or 'unknown version'}`",
        f"Commit: `{upstream.get('commit') or 'unknown'}`",
        f"Source path: `{upstream.get('path')}`",
        f"Scope: `{report['config']['scope']}`",
        "",
        "## Summary",
        "",
        f"- TypeScript surface items: `{summary['typescript_surface_count']}`",
        f"- Python surface items: `{summary['python_surface_count']}`",
        f"- Matched items: `{summary['matched_count']}`",
        f"- Needs review: `{summary['needs_review_count']}`",
        f"- Present in TS only: `{summary['ts_only_count']}`",
        f"- Present in Python only: `{summary['python_only_count']}`",
        f"- Missing feature probes: `{summary['missing_feature_count']}`",
        "",
        "## Feature Probes",
        "",
        "| Status | Feature | TS Evidence | Python Evidence |",
        "| --- | --- | --- | --- |",
    ]

    for probe in report["feature_probes"]:
        lines.append(
            "| {status} | {label} | `{ts}` | `{py}` |".format(
                status=probe["status"],
                label=probe["label"],
                ts=", ".join(probe["ts_hits"]) or "-",
                py=", ".join(probe["python_hits"]) or "-",
            )
        )

    append_agent_brief(lines, report)

    lines.extend(["", "## TypeScript Only", ""])
    append_item_table(lines, comparison["ts_only"][:max_items])
    if len(comparison["ts_only"]) > max_items:
        lines.append(f"\nShowing first `{max_items}` of `{len(comparison['ts_only'])}` items. See JSON for the full list.")

    lines.extend(["", "## Needs Manual Review", ""])
    if comparison["needs_review"]:
        lines.extend(["| TypeScript | Python | Reason |", "| --- | --- | --- |"])
        for pair in comparison["needs_review"][:max_items]:
            lines.append(
                f"| {format_item_ref(pair['typescript'])} | {format_item_ref(pair['python'])} | `{pair['match_type']}` |"
            )
    else:
        lines.append("No name-only matches found.")

    lines.extend(["", "## Python Only", ""])
    append_item_table(lines, comparison["python_only"][:max_items])
    if len(comparison["python_only"]) > max_items:
        lines.append(f"\nShowing first `{max_items}` of `{len(comparison['python_only'])}` items. See JSON for the full list.")

    lines.extend(
        [
            "",
            "## Maintainer Notes",
            "",
            "- Treat `missing_in_python` feature probes and `TypeScript Only` classes/functions/methods as triage candidates.",
            "- A match here means the public names look aligned; it does not prove behavior parity.",
            "- For high-risk areas like upload/download semantics, encryption wire format, network config, and proof verification, follow up with source-level review and parity tests.",
            "",
        ]
    )
    return "\n".join(lines)


def append_agent_brief(lines: list[str], report: dict[str, Any]) -> None:
    action_items = report.get("action_items", [])
    lines.extend(
        [
            "",
            "## Coding Agent Brief",
            "",
            "Use this section as the handoff for implementation or review work.",
            "",
            f"- Upstream commit: `{report['upstream'].get('commit') or 'unknown'}`",
            f"- Upstream package: `{report['upstream'].get('package') or 'unknown'}` `{report['upstream'].get('version') or 'unknown version'}`",
            f"- Compare scope: `{report['config']['scope']}`",
            f"- Python root: `{report['config']['python_root']}`",
            "- Treat every action item as a hypothesis from static analysis, then confirm from source before coding.",
            "",
            "### Prioritized Action Items",
            "",
        ]
    )

    if not action_items:
        lines.append("No missing or partial feature probes were detected. Review the TypeScript-only surface table for lower-priority drift.")
        return

    for index, item in enumerate(action_items, start=1):
        lines.extend(
            [
                f"#### {index}. {item['priority']} - {item['title']}",
                "",
                f"- Status: `{item['status']}`",
                f"- Why: {item['why']}",
                f"- Suggested next step: {item['suggested_next_step']}",
                f"- Upstream evidence patterns: `{', '.join(item['upstream_evidence_patterns']) or '-'}`",
                f"- Python evidence patterns: `{', '.join(item['python_evidence_patterns']) or '-'}`",
                "",
                "Upstream refs:",
            ]
        )
        append_compact_refs(lines, item["upstream_refs"])
        lines.append("")
        lines.append("Likely Python refs:")
        append_compact_refs(lines, item["python_refs"])
        if item["review_refs"]:
            lines.append("")
            lines.append("Name-only matches to inspect:")
            for pair in item["review_refs"]:
                lines.append(f"- TS {format_item_ref(pair['typescript'])} -> Python {format_item_ref(pair['python'])}")
        lines.extend(["", "Acceptance criteria:"])
        for criterion in item["acceptance_criteria"]:
            lines.append(f"- {criterion}")
        lines.append("")


def append_compact_refs(lines: list[str], refs: list[dict[str, Any]]) -> None:
    if not refs:
        lines.append("- No close static reference found; search by the evidence patterns above.")
        return
    for ref in refs:
        lines.append(f"- `{ref['qualified_name']}` in `{ref['path']}:{ref['line']}`")


def append_item_table(lines: list[str], items: list[dict[str, Any]]) -> None:
    if not items:
        lines.append("No items.")
        return
    lines.extend(["| Domain | Kind | Item | Location |", "| --- | --- | --- | --- |"])
    for item in items:
        lines.append(f"| `{item['domain']}` | `{item['kind']}` | `{item['qualified_name']}` | `{item['path']}:{item['line']}` |")


def format_item_ref(item: dict[str, Any]) -> str:
    return f"`{item['qualified_name']}`<br>`{item['path']}:{item['line']}`"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ts-path", type=Path, help="Local path to 0g-storage-ts-starter-kit. Skips remote fetch when provided.")
    parser.add_argument("--upstream-url", default=DEFAULT_UPSTREAM_URL, help="Git URL for the upstream TS SDK.")
    parser.add_argument("--ref", default=DEFAULT_REF, help=f"Branch, tag, or commit to compare. Defaults to {DEFAULT_REF}.")
    parser.add_argument("--cache-dir", type=Path, default=Path(DEFAULT_CACHE_DIR), help="Local checkout cache for the upstream storage starter kit.")
    parser.add_argument("--python-root", type=Path, default=Path(DEFAULT_PYTHON_ROOT), help="Python storage SDK package root.")
    parser.add_argument("--report-md", type=Path, default=Path(DEFAULT_REPORT_MD), help="Markdown report output path.")
    parser.add_argument("--report-json", type=Path, default=Path(DEFAULT_REPORT_JSON), help="JSON report output path.")
    parser.add_argument("--refresh", action="store_true", help="Fetch the latest upstream ref before comparing.")
    parser.add_argument("--no-fetch", action="store_true", help="Require an existing local TS path or cache.")
    parser.add_argument(
        "--scope",
        choices=("sdk", "package"),
        default="sdk",
        help="Compare starter-kit library/scripts by default, or the broader package including web UI.",
    )
    parser.add_argument("--max-items", type=int, default=80, help="Maximum items to show per Markdown section.")
    parser.add_argument("--git-timeout", type=int, default=GIT_TIMEOUT_SECONDS, help="Seconds before a git operation is treated as failed.")
    parser.add_argument("--fail-on-missing", action="store_true", help="Exit with status 2 when TS-only items or missing feature probes are found.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    global GIT_TIMEOUT_SECONDS
    args = parse_args(argv)
    GIT_TIMEOUT_SECONDS = args.git_timeout
    repo_root = Path.cwd().resolve()
    python_root = (repo_root / args.python_root).resolve()
    if not python_root.exists():
        raise FileNotFoundError(f"Python storage root does not exist: {python_root}")

    ts_root = ensure_upstream_checkout(
        ts_path=args.ts_path,
        cache_dir=repo_root / args.cache_dir,
        upstream_url=args.upstream_url,
        ref=args.ref,
        refresh=args.refresh,
        no_fetch=args.no_fetch,
    )

    include_hints = TS_PACKAGE_HINTS if args.scope == "package" else TS_SDK_HINTS
    ts_items = extract_ts_surface(ts_root, include_hints)
    py_items = extract_python_surface(python_root, repo_root)
    comparison = compare_surfaces(ts_items, py_items)
    feature_probes = run_feature_probes(ts_root, repo_root, include_hints, args.scope)
    report = build_report(
        upstream=upstream_metadata(ts_root),
        ts_items=ts_items,
        py_items=py_items,
        comparison=comparison,
        feature_probes=feature_probes,
        args=args,
    )

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report_md.write_text(render_markdown(report, args.max_items), encoding="utf-8")

    print(f"Wrote {args.report_md}")
    print(f"Wrote {args.report_json}")
    print(
        "Summary: "
        f"{report['summary']['ts_only_count']} TS-only, "
        f"{report['summary']['needs_review_count']} needs review, "
        f"{report['summary']['missing_feature_count']} missing feature probes"
    )

    if args.fail_on_missing and (
        report["summary"]["ts_only_count"] > 0 or report["summary"]["missing_feature_count"] > 0
    ):
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
