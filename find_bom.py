import os

bom_files = []
root = r'c:\Users\Administrador\Documents\APi'

for dirpath, dirnames, filenames in os.walk(root):
    # Skip .venv, .git, __pycache__
    dirnames[:] = [d for d in dirnames if d not in ('.venv', '.git', '__pycache__', 'instance')]
    for f in filenames:
        if f.endswith(('.py', '.html', '.js', '.css')):
            path = os.path.join(dirpath, f)
            try:
                with open(path, 'rb') as fh:
                    head = fh.read(3)
                    if head == b'\xef\xbb\xbf':
                        bom_files.append(path)
            except:
                pass

print(f'Found {len(bom_files)} files with UTF-8 BOM:')
for f in bom_files:
    print(f'  {f}')
