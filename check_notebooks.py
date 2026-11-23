"""Static notebook check only: does not execute Spark or contact Azure."""
import ast,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
for path in sorted((root/'notebooks').glob('*.ipynb')):
    notebook=json.loads(path.read_text())
    for cell in notebook['cells']:
        if cell['cell_type']=='code':ast.parse(''.join(cell['source']),filename=str(path))
        if cell['cell_type']=='code' and cell.get('outputs'):raise ValueError('Clear outputs before committing')
    print('Notebook syntax OK:',path.name)
