"""
Setup configuration for the 0G Compute Network Python SDK.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text() if (this_directory / "README.md").exists() else ""

# Read requirements
requirements = []
if (this_directory / "requirements.txt").exists():
    with open(this_directory / "requirements.txt") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="0g-py-sdk",
    version="0.1.0",
    author="notMartin",
    author_email="https://x.com/damiclone",
    description="Python SDK for the 0G Compute Network - AI inference services on decentralized infrastructure",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mandatedisrael/0g-py-sdk",
    project_urls={
        "Documentation": "https://docs.0g.ai/developer-hub/building-on-0g/compute-network/sdk",
        "Source": "https://github.com/mandatedisrael/0g-py-sdk",
        "Bug Reports": "https://github.com/mandatedisrael/0g-py-sdk/issues",
    },
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    include_package_data=True,
    package_data={
        "og_compute_sdk": ["py.typed"],
    },
    keywords="0g blockchain ai inference decentralized llm crypto web3",
    zip_safe=False,
)