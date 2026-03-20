import os

bom_files = [
    r'c:\Users\Administrador\Documents\APi\app\config.py',
    r'c:\Users\Administrador\Documents\APi\app\static\js\app.js',
    r'c:\Users\Administrador\Documents\APi\app\static\js\personnel.js',
    r'c:\Users\Administrador\Documents\APi\app\templates\dashboard.html',
    r'c:\Users\Administrador\Documents\APi\app\templates\login.html',
    r'c:\Users\Administrador\Documents\APi\app\templates\personnel.html',
]

for path in bom_files:
    with open(path, 'rb') as f:
        content = f.read()
    if content[:3] == b'\xef\xbb\xbf':
        with open(path, 'wb') as f:
            f.write(content[3:])
        print(f'  FIXED: {path}')
    else:
        print(f'  OK:    {path}')

print('\nDone! All BOM bytes stripped.')
