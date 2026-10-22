"""Run new and legacy computational tests without optional plotting packages."""
import ast
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
path = ROOT / "vn_priority_based_selection.py"
tree = ast.parse(path.read_text())
tree.body = [n for n in tree.body
    if not (isinstance(n, ast.Import) and any(a.name == "matplotlib.pyplot" for a in n.names))
    and not (isinstance(n, ast.ImportFrom) and n.module == "visualisations")]
module = types.ModuleType("vn_priority_based_selection")
sys.modules[module.__name__] = module
exec(compile(tree, str(path), "exec"), module.__dict__)
def unavailable_plot(*args, **kwargs):
    raise RuntimeError("Plotting unavailable in computational test runtime")
# The legacy CLI test mocks this entry point; actual plotting is not exercised.
module.plot_comparison = unavailable_plot
suite = unittest.defaultTestLoader.loadTestsFromNames([
    "test_savn_early_d_planning", "test_vn_priority_based_selection",
    "test_savn_priority_sa", "test_savn_iteration2"])
result = unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
