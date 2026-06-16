import subprocess
import sys
from importlib import resources
from pathlib import Path
from zipfile import ZipFile

import zerog_py_sdk


AGENT_DOCS = [
    "docs/llms/index.md",
    "docs/llms/inference.md",
    "docs/llms/provider-discovery.md",
    "docs/llms/fine-tuning.md",
    "docs/llms/model-verification.md",
    "docs/llms/contract-errors.md",
    "docs/llms/troubleshooting.md",
]


def test_agent_docs_are_available_as_package_resources():
    package_root = resources.files("zerog_py_sdk")

    llms_index = package_root.joinpath("llms.txt")
    assert llms_index.is_file()
    assert "create_broker" in llms_index.read_text(encoding="utf-8")
    assert "Automata" in llms_index.read_text(encoding="utf-8")

    for relative_path in AGENT_DOCS:
        doc = package_root.joinpath(relative_path)
        assert doc.is_file(), f"{relative_path} missing from package resources"


def test_init_docstring_points_agents_to_real_public_api():
    docstring = zerog_py_sdk.__doc__ or ""

    assert "zerog_py_sdk/llms.txt" in docstring
    assert "create_broker" in docstring
    assert "create_read_only_broker" in docstring
    assert "ResponseVerifier" in docstring
    assert "Automata" in docstring
    assert "ZeroGInferenceClient" not in docstring
    assert "ZeroGVerifier" not in docstring


def test_built_wheel_includes_agent_documentation(tmp_path):
    package_dir = Path(__file__).resolve().parents[1]
    dist_dir = tmp_path / "dist"

    subprocess.run(
        [
            sys.executable,
            "setup.py",
            "bdist_wheel",
            "--dist-dir",
            str(dist_dir),
        ],
        cwd=package_dir,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    wheel = next(dist_dir.glob("0g_inference_sdk-*.whl"))
    with ZipFile(wheel) as archive:
        names = set(archive.namelist())

    expected = {
        "zerog_py_sdk/llms.txt",
        "zerog_py_sdk/docs/llms/index.md",
        "zerog_py_sdk/docs/llms/inference.md",
        "zerog_py_sdk/docs/llms/model-verification.md",
        "zerog_py_sdk/docs/llms/troubleshooting.md",
    }
    assert expected.issubset(names)
