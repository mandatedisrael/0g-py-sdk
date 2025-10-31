"""
Pedersen hash generator bases for Baby JubJub.

These are precomputed generator points extracted from circomlibjs.
They must be initialized before using PedersenHash.hash().

To extract these bases from circomlibjs:
1. Run: node extract_pedersen_bases.mjs
2. Copy the output to this file

For now, we provide a loader function that can initialize from:
- circomlibjs subprocess call (as fallback)
- Hardcoded bases (once extracted)
- External file (in production)
"""

import subprocess
import json
import tempfile
import os
from pathlib import Path


def load_bases_from_circomlibjs():
    """
    Load Pedersen bases directly from circomlibjs via subprocess.

    This is a temporary solution while we work on extracting/hardcoding
    the bases. Once we have the bases hardcoded, this function can be removed.

    Returns:
        List of (x, y) points on Baby JubJub curve
    """
    script = """
    const circomlibjs = require('circomlibjs');
    (async () => {
        try {
            const h = await circomlibjs.buildPedersenHash();

            // The bases might be in different locations depending on circomlibjs version
            let bases = h.bases;
            if (!bases || bases.length === 0) {
                bases = h._bases;
            }
            if (!bases || bases.length === 0) {
                // Try to get from babyJub
                const bj = h.babyJub;
                bases = bj.bases;
            }

            if (!bases || bases.length === 0) {
                console.error('ERROR: Could not locate Pedersen bases');
                process.exit(1);
            }

            // Convert to JSON-serializable format
            const result = bases.map(base => ({
                x: base[0].toString(),
                y: base[1].toString()
            }));

            console.log(JSON.stringify(result));
        } catch (e) {
            console.error('ERROR:', e.message);
            process.exit(1);
        }
    })();
    """

    try:
        # Write script to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(script)
            script_path = f.name

        # Execute
        result = subprocess.run(
            ['node', script_path],
            capture_output=True,
            text=True,
            timeout=10,
            check=True
        )

        os.unlink(script_path)

        # Parse result
        bases_data = json.loads(result.stdout)

        # Convert to integer tuples
        bases = []
        for base in bases_data:
            x = int(base['x'])
            y = int(base['y'])
            bases.append((x, y))

        return bases

    except Exception as e:
        raise RuntimeError(f"Failed to load Pedersen bases from circomlibjs: {e}")


def load_bases_from_file(filepath):
    """
    Load Pedersen bases from JSON file.

    File format:
    {
        "bases": [
            {"x": "0x...", "y": "0x..."},
            ...
        ]
    }

    Args:
        filepath: Path to JSON file with bases

    Returns:
        List of (x, y) points
    """
    with open(filepath, 'r') as f:
        data = json.load(f)

    bases = []
    for base in data.get('bases', []):
        # Handle both hex strings and decimal strings
        if isinstance(base['x'], str) and base['x'].startswith('0x'):
            x = int(base['x'], 16)
        else:
            x = int(base['x'])

        if isinstance(base['y'], str) and base['y'].startswith('0x'):
            y = int(base['y'], 16)
        else:
            y = int(base['y'])

        bases.append((x, y))

    return bases


# Placeholder: Will be loaded at runtime
HARDCODED_BASES = None

def get_pedersen_bases():
    """
    Get Pedersen hash generator bases.

    Returns bases in this priority order:
    1. Hardcoded bases (if available)
    2. From file (if exists)
    3. From circomlibjs (subprocess)

    Returns:
        List of (x, y) Baby JubJub points
    """
    # Try hardcoded first
    if HARDCODED_BASES is not None:
        return HARDCODED_BASES

    # Try file
    bases_file = Path(__file__).parent / 'pedersen_bases.json'
    if bases_file.exists():
        try:
            return load_bases_from_file(str(bases_file))
        except Exception as e:
            print(f"Warning: Could not load bases from file: {e}")

    # Fall back to circomlibjs
    print("⚠️  Loading Pedersen bases from circomlibjs... (this requires Node.js)")
    return load_bases_from_circomlibjs()
