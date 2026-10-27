#!/usr/bin/env python3
"""
Encrypt the AI Capital Terminal page so the published index.html holds only
ciphertext. Nothing readable (no figures, no markup, no dashboard JS, no
passcode hash) is in the published file; it decrypts in the browser only
with the correct passcode.

  Plaintext source (git-ignored, local only):  src/terminal.src.html
  Optional typo guard (git-ignored):          src/passcode.sha256
  Published output (safe to commit):   index.html

Usage (run from the repo root, on your own machine):
  pip install cryptography
  python tools/encrypt_page.py

You are prompted for the passcode twice. If src/passcode.sha256 exists, the
passcode is also checked against it before anything is written.

Crypto: PBKDF2-HMAC-SHA256 (600,000 iterations, random 16-byte salt) derives
a 256-bit AES-GCM key; random 12-byte IV; payload gzip-compressed before
encryption. A fresh salt and IV are generated on every run. Wrong passcode =
GCM authentication failure, so no hash is needed in the page and guesses
must pay the full PBKDF2 cost. Protection is only as strong as the passcode:
use 12+ characters that are not a dictionary phrase.
"""
import argparse, base64, getpass, gzip, hashlib, json, os, re, sys

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
except ImportError:
    sys.exit("Missing dependency: run  pip install cryptography")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "terminal.src.html")
OUT = os.path.join(ROOT, "index.html")
HASHFILE = os.path.join(ROOT, "src", "passcode.sha256")
ITERATIONS = 600_000
JS_START = "function initDashboard(){"
JS_END = "// ---- Passcode gate"


def expected_hash():
    """Optional local typo guard; None when absent. Never published."""
    if not os.path.exists(HASHFILE):
        return None
    m = re.search(r"[0-9a-f]{64}", open(HASHFILE, encoding="utf-8").read().lower())
    if not m:
        sys.exit(f"{HASHFILE} exists but holds no SHA-256 hex digest")
    return m.group(0)


def extract(src):
    """Split the plaintext build into head CSS, app markup and app JS."""
    title = re.search(r"<title>(.*?)</title>", src, re.S).group(1)
    head_links = "\n".join(re.findall(r'<link[^>]+>', src.split("</head>")[0]))
    css = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
    html = re.search(r'<template id="appTpl">(.*?)</template>', src, re.S)
    if not html:
        sys.exit('No <template id="appTpl"> found in the source page')
    i, j = src.find(JS_START), src.find(JS_END)
    if i < 0 or j < 0 or j < i:
        sys.exit("Could not locate the dashboard script (initDashboard) in the source page")
    return title, head_links, css, html.group(1), src[i:j]


LOADER = r"""
(function(){
var P = __PAYLOAD__;
var KEY_FLAG = 'aiCapitalTerminalKey';
function b64d(s){ var b=atob(s), u=new Uint8Array(b.length); for(var i=0;i<b.length;i++) u[i]=b.charCodeAt(i); return u; }
function b64e(u){ var s=''; for(var i=0;i<u.length;i++) s+=String.fromCharCode(u[i]); return btoa(s); }
function deriveKey(pass){
  return crypto.subtle.importKey('raw', new TextEncoder().encode(pass), 'PBKDF2', false, ['deriveKey'])
    .then(function(base){ return crypto.subtle.deriveKey(
      {name:'PBKDF2', salt:b64d(P.salt), iterations:P.iter, hash:'SHA-256'},
      base, {name:'AES-GCM', length:256}, true, ['decrypt']); });
}
function gunzip(buf){
  var ds = new DecompressionStream('gzip');
  return new Response(new Blob([buf]).stream().pipeThrough(ds)).text();
}
function decryptWith(key){
  return crypto.subtle.decrypt({name:'AES-GCM', iv:b64d(P.iv)}, key, b64d(P.ct))
    .then(gunzip).then(JSON.parse);
}
function render(app, key){
  document.getElementById('appHolder').innerHTML = app.html;
  var s = document.createElement('script');
  s.textContent = app.js + '\ninitDashboard();';
  document.body.appendChild(s);
  document.getElementById('lockScreen').style.display = 'none';
  document.getElementById('lockBtn').style.display = 'block';
  if (location.hash) { var t=document.getElementById(location.hash.slice(1)); if(t) t.scrollIntoView(); }
  return crypto.subtle.exportKey('raw', key).then(function(raw){
    try { sessionStorage.setItem(KEY_FLAG, b64e(new Uint8Array(raw))); } catch(e){}
  });
}
function fail(msg){
  var err=document.getElementById('lockErr'), inp=document.getElementById('lockInput'), go=document.getElementById('lockGo');
  err.textContent=msg; err.style.display='block'; go.disabled=false; go.textContent='Unlock';
  inp.value=''; inp.focus();
}
var supported = !!(window.crypto && crypto.subtle && window.DecompressionStream);
document.getElementById('lockForm').addEventListener('submit', function(ev){
  ev.preventDefault();
  if (!supported) { fail('This browser cannot decrypt the terminal. Use a current Chrome, Edge, Safari or Firefox.'); return; }
  var go=document.getElementById('lockGo'); go.disabled=true; go.textContent='Decrypting…';
  document.getElementById('lockErr').style.display='none';
  var pass=document.getElementById('lockInput').value, k;
  deriveKey(pass).then(function(key){ k=key; return decryptWith(key); })
    .then(function(app){ return render(app, k); })
    .catch(function(){ fail('Incorrect passcode'); });
});
document.getElementById('lockBtn').addEventListener('click', function(){
  try { sessionStorage.removeItem(KEY_FLAG); } catch(e){}
  window.location.reload();
});
try {
  var saved = sessionStorage.getItem(KEY_FLAG);
  if (saved && supported) {
    crypto.subtle.importKey('raw', b64d(saved), {name:'AES-GCM'}, true, ['decrypt'])
      .then(function(key){ return decryptWith(key).then(function(app){ return render(app, key); }); })
      .catch(function(){ try { sessionStorage.removeItem(KEY_FLAG); } catch(e){} });
  }
} catch(e){}
})();
"""

SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<meta name="color-scheme" content="light dark" />
<meta name="robots" content="noindex, nofollow" />
<title>__TITLE__</title>
__LINKS__
<style>__CSS__</style>
</head>
<body>
<div id="lockScreen" role="main">
  <form class="lock-card" id="lockForm" autocomplete="off">
    <p class="lock-kicker">Private terminal · static baseline</p>
    <h1>__TITLE__</h1>
    <p class="lock-sub">Enter the passcode to decrypt and load the terminal. This page contains only encrypted data until the passcode is entered.</p>
    <label for="lockInput">Passcode</label>
    <input type="password" id="lockInput" autocomplete="off" autocapitalize="off" spellcheck="false" />
    <button type="submit" id="lockGo">Unlock</button>
    <p id="lockErr" role="alert">Incorrect passcode</p>
  </form>
</div>
<button id="lockBtn" type="button" title="Lock the terminal">Lock</button>
<div id="appHolder"></div>
<script>__LOADER__</script>
</body>
</html>
"""


def encrypt(payload: bytes, passcode: str):
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=ITERATIONS).derive(passcode.encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, gzip.compress(payload, 9), None)
    b = lambda x: base64.b64encode(x).decode()
    return {"v": 1, "iter": ITERATIONS, "salt": b(salt), "iv": b(iv), "ct": b(ct)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--test-passcode", help=argparse.SUPPRESS)  # tests only; skips the interactive prompt and hash check
    a = ap.parse_args()

    if not os.path.exists(a.src):
        sys.exit(f"Plaintext source not found: {a.src}\n"
                 "Put the readable dashboard there (it is git-ignored and never published).")
    src = open(a.src, encoding="utf-8").read()
    if "<template id=\"appTpl\">" not in src:
        sys.exit("Source does not look like the plaintext dashboard (no appTpl template). "
                 "Did you point --src at an already-encrypted index.html?")

    if a.test_passcode:
        passcode = a.test_passcode
    else:
        passcode = getpass.getpass("Passcode: ")
        if getpass.getpass("Repeat passcode: ") != passcode:
            sys.exit("Passcodes do not match. Nothing written.")
        want = expected_hash()
        if want and hashlib.sha256(passcode.encode("utf-8")).hexdigest() != want:
            sys.exit("Passcode does not match src/passcode.sha256. Nothing written.")
        if len(passcode) < 12:
            print("Warning: passcode is under 12 characters; the encryption is only as strong as it.")

    title, links, css, html, js = extract(src)
    blob = encrypt(json.dumps({"html": html, "js": js}).encode("utf-8"), passcode)
    shell = SHELL.replace("__TITLE__", title).replace("__LINKS__", links).replace("__CSS__", css)
    page = shell.replace("__LOADER__", LOADER.replace("__PAYLOAD__", json.dumps(blob)))

    # Safety net: nothing readable from the dashboard, and not the passcode hash,
    # may appear in the published file outside the ciphertext.
    for probe in ("appTpl", "function initDashboard", "Executive summary"):
        if probe in shell or probe in LOADER:
            sys.exit(f"Refusing to write: plaintext marker {probe!r} leaked into the output.")

    open(a.out, "w", encoding="utf-8").write(page)
    print(f"Wrote {a.out}  ({len(page):,} bytes, ciphertext {len(blob['ct']):,} chars)")


if __name__ == "__main__":
    main()
