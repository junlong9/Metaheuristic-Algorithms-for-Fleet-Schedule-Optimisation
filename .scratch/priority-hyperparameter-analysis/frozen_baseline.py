"""Load the byte-identical algorithm version used by the completed sweeps."""
from pathlib import Path
import ast,types,sys,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
FROZEN_PRODUCTION=Path(__file__).resolve().parent/'frozen-source/savn_priority_based_selection.py'
sys.path.insert(0,str(ROOT))
tree=ast.parse(FROZEN_PRODUCTION.read_text())
tree.body=[n for n in tree.body if not (isinstance(n,ast.Import) and any(a.name=='matplotlib.pyplot' for a in n.names)) and not (isinstance(n,ast.ImportFrom) and n.module=='visualisations')]
opt=types.ModuleType('savn_priority_based_selection')
exec(compile(tree,str(FROZEN_PRODUCTION),'exec'),opt.__dict__)
sys.modules['savn_priority_based_selection']=opt
DEFAULT=[(-28,28),(-14,14),(-7,7),(-3,3)]
HALVES=[(-28,-14,14,28),(-14,-7,7,14),(-7,-3,3,7),(-3,-1,1,3)]
DENSE=[(-28,28),(-21,21),(-14,14),(-7,7),(-3,3),(-1,1)]
WIDE=[(-42,42)]+DEFAULT
CONFIGS={'Default':DEFAULT,'Half steps':HALVES,'Dense pairs':DENSE,'Wide first':WIDE}
def fingerprint(schedule):return hashlib.sha256(json.dumps(schedule,sort_keys=True).encode()).hexdigest()
