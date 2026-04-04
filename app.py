from __future__ import annotations

import io
import shutil
import tempfile
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

from flask import Flask, jsonify

app = Flask(__name__)


@contextmanager
def _isolated_demo_database():
    """
    Run the CLI demo against a temporary copy of data.json.

    Vercel functions can read bundled files but should not mutate them directly,
    so the demo uses an isolated writable copy instead of the repo file.
    """
    import database

    source = Path(__file__).with_name("data.json")
    temp_dir = Path(tempfile.mkdtemp(prefix="mentor-demo-"))
    temp_file = temp_dir / "data.json"
    shutil.copy2(source, temp_file)

    original_data_file = database.DATA_FILE
    database.DATA_FILE = str(temp_file)
    try:
        yield
    finally:
        database.DATA_FILE = original_data_file
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/")
def root():
    return jsonify(
        {
            "name": "Mentor Mentee System",
            "deployment": "vercel",
            "mode": "api",
            "note": "Desktop Tkinter GUI is not available on Vercel. Use local run for GUI.",
            "endpoints": ["/", "/health", "/demo"],
        }
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/demo")
def demo():
    from main import run_demo

    buffer = io.StringIO()
    with _isolated_demo_database(), redirect_stdout(buffer):
        run_demo()

    return jsonify({"output": buffer.getvalue()})
