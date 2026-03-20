import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('172.16.10.70', 22, 'root', 'soporte12#$', timeout=5)

py_script = """
import urllib.request, urllib.parse, json
from http.cookiejar import CookieJar

cj = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
data = urllib.parse.urlencode({'username':'admin','password':'123'}).encode('utf-8')
try:
    opener.open('http://127.0.0.1:5000/login', data=data)
    gen_data = json.dumps({'year': 2026, 'month': 4}).encode('utf-8')
    req = urllib.request.Request(
        'http://127.0.0.1:5000/api/schedule/generate',
        data=gen_data,
        headers={'Content-Type': 'application/json'}
    )
    resp = opener.open(req)
    print("SUCCESS")
except Exception as e:
    import urllib.error
    if isinstance(e, urllib.error.HTTPError):
        print("HTTP_ERROR:", e.code, e.read().decode(errors='replace'))
    else:
        print("ERROR:", e)
"""
stdin, stdout, stderr = ssh.exec_command(f"cat << 'INLINE_EOF' > /tmp/test_gen.py\n{py_script}\nINLINE_EOF\npython3 /tmp/test_gen.py")
out = stdout.read().decode(errors='replace')
err = stderr.read().decode(errors='replace')
print(out.encode('ascii', 'replace').decode('ascii'))
if err: print("ERR:", err.encode('ascii', 'replace').decode('ascii'))
ssh.close()
