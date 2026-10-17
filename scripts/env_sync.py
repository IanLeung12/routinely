#!/usr/bin/env python3
"""Bring your .env up to date with .env.example, keeping every value you already set.

  python3 scripts/env_sync.py          # rewrites .env (backup in .env.bak), prints what changed

Layout and comments come from .env.example; your values win; keys that only exist in
your .env are kept at the bottom. Values are never printed.
"""
import os, re, shutil, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ex, env = os.path.join(root, ".env.example"), os.path.join(root, ".env")
KEY = re.compile(r"^([A-Z_][A-Z0-9_]*)=(.*)$")
cur = {}
if os.path.exists(env):
    for line in open(env, encoding="utf-8", errors="replace"):
        m = KEY.match(line.rstrip("\n"))
        if m:
            cur[m.group(1)] = m.group(2)
    shutil.copy(env, env + ".bak")
out, seen = [], set()
for line in open(ex, encoding="utf-8"):
    line = line.rstrip("\n")
    m = KEY.match(line)
    if m:
        seen.add(m.group(1))
        out.append(f"{m.group(1)}={cur[m.group(1)]}" if m.group(1) in cur else line)
    else:
        out.append(line)
extra = [k for k in cur if k not in seen]
if extra:
    out += ["", "# --- only in your .env (not in .env.example) ---"] + [f"{k}={cur[k]}" for k in extra]
with open(env, "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
added = sorted(seen - set(cur))
print("added (defaults):", ", ".join(added) or "none")
print("kept (not in example):", ", ".join(extra) or "none")
sys.exit(0)
