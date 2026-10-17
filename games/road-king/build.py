"""Build the standalone single-player game ZIP."""
from pathlib import Path
import sys
import zipfile

source = Path(__file__).resolve().parent
output = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/road-king-frappe.zip')
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(source.rglob('*')):
        if path.is_file() and (path.relative_to(source).parts[0] == 'assets' or path.suffix == '.html'):
            archive.write(path, path.relative_to(source).as_posix())
print(output)
