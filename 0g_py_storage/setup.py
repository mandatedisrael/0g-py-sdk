from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="0g-storage-sdk",
    version="0.2.1",
    author="0G Labs",
    author_email="support@0g.ai",
    description="Official Python SDK for 0G Storage - A decentralized storage network with merkle tree verification",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/0glabs/0g-py-sdk",
    project_urls={
        "Bug Tracker": "https://github.com/0glabs/0g-py-sdk/issues",
        "Documentation": "https://docs.0g.ai",
        "Source Code": "https://github.com/0glabs/0g-py-sdk/tree/main/0g_py_storage",
    },
    packages=find_packages(exclude=["tests", "*.tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pycryptodome>=3.23.0",
        "web3>=7.14.0",
        "eth-account>=0.13.7",
        "requests>=2.32.5",
    ],
    extras_require={
        "dev": [
            "pytest>=8.4.2",
        ],
    },
    keywords="0g storage blockchain web3 merkle cryptography decentralized",
)
