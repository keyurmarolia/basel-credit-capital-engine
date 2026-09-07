"""Execute the existing notebook sources in chronological order."""

import argparse
import sys
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, help="Optional separate execution-output directory."
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output_dir or root / "notebooks"
    output.mkdir(parents=True, exist_ok=True)
    for path in sorted((root / "notebooks").glob("*.ipynb")):
        notebook = nbformat.read(path, as_version=4)
        manager = KernelManager(kernel_name="python3")
        manager.kernel_spec.argv = [
            sys.executable,
            "-m",
            "ipykernel_launcher",
            "-f",
            "{connection_file}",
        ]
        client = NotebookClient(
            notebook, km=manager, timeout=300, resources={"metadata": {"path": str(root)}}
        )
        client.execute(cleanup_kc=True)
        nbformat.write(notebook, output / path.name)
        print(f"Executed {path.name}", flush=True)


if __name__ == "__main__":
    main()
