"""Entry point — delegates to scripts/verify_buffer_auth.py."""
import runpy, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
runpy.run_path(str(pathlib.Path(__file__).parent / "scripts" / "verify_buffer_auth.py"), run_name="__main__")
