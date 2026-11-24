import re

with open('pwa/app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

with open('pwa/index.html', 'r', encoding='utf-8') as f:
    index_html = f.read()

# Find all getElementById
ids = set(re.findall(r"document\.getElementById\(['\"](.*?)['\"]\)", app_js))
html_ids = set(re.findall(r"id=['\"](.*?)['\"]", index_html))

print(f"Checking {len(ids)} unique DOM IDs...")
missing = []
for i in ids:
    if i not in html_ids and i != 'shoiToast': # shoiToast is created dynamically
        missing.append(i)

if missing:
    print('MISSING DOM IDs:', missing)
else:
    print('ALL DOM IDs MATCH PERFECTLY! (0 missing)')
