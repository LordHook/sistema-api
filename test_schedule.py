import urllib.request
import urllib.parse
import json
from http.cookiejar import CookieJar

cj = CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cj),
    urllib.request.HTTPRedirectHandler()
)

# Login
data = urllib.parse.urlencode({'username':'admin','password':'123'}).encode('utf-8')
req = urllib.request.Request('http://localhost:5000/login', data=data)
try:
    resp = opener.open(req)
    print('Login response URL:', resp.url)
    print('Login status:', resp.status)
    print('Cookies:', [(c.name, c.value) for c in cj])
except Exception as e:
    print('Login exception:', e)

# GET schedule
try:
    resp = opener.open('http://localhost:5000/api/schedule?year=2026&month=3')
    ct = resp.headers.get('Content-Type', '')
    print('\nGET /api/schedule')
    print('  Status:', resp.status)
    print('  Content-Type:', ct)
    body = resp.read()
    print('  First 200 bytes:', body[:200])
    
    if b'json' in ct.encode() or body[:1] == b'{':
        data = json.loads(body.decode('utf-8'))
        print('  JSON parsed OK, sections:', len(data.get('sections', [])))
    else:
        print('  NOT JSON! Likely login redirect.')
except Exception as e:
    print('GET schedule error:', e)

# POST generate
try:
    gen_data = json.dumps({'year': 2026, 'month': 3}).encode('utf-8')
    req = urllib.request.Request(
        'http://localhost:5000/api/schedule/generate',
        data=gen_data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    resp = opener.open(req)
    ct = resp.headers.get('Content-Type', '')
    print('\nPOST /api/schedule/generate')
    print('  Status:', resp.status)
    print('  Content-Type:', ct)
    body = resp.read()
    print('  First 300 bytes:', body[:300])
except urllib.error.HTTPError as e:
    print('\nPOST generate error:', e.code)
    print('  Body:', e.read()[:500])
except Exception as e:
    print('\nPOST generate exception:', e)
