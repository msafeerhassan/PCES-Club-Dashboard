import re, pathlib, sys
TOKEN = '<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">'
form_re = re.compile(r'(<form\b[^>]*\bmethod\s*=\s*["\']post["\'][^>]*>)', re.I)
root = pathlib.Path(sys.argv[1])
patched = 0
for p in sorted(root.rglob("*.html")):
    s = p.read_text(encoding="utf-8")
    if "csrf_token" in s:
        continue
    new, n = form_re.subn(lambda m: m.group(1) + "\n  " + TOKEN, s)
    if n:
        p.write_text(new, encoding="utf-8")
        patched += n
        print(f"patched {n} form(s): {p}")
print("TOTAL forms patched:", patched)