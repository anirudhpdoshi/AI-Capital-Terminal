# Passcode gate — mandatory for every hosted copy of this dashboard

- Lock screen only on load: title + single passcode field. Dashboard content must NOT load or render (nothing in the DOM) until the correct passcode is entered — render-on-unlock, never a hidden overlay over loaded data.
- Encryption: the published page holds only ciphertext. Dashboard markup, data and script are AES-256-GCM encrypted with a key derived from the passcode (PBKDF2-SHA256, 600,000 iterations, fresh salt + IV each build) by `tools/encrypt_page.py`; the browser decrypts with Web Crypto. Wrong passcode = decryption fails, so the page needs no hash. No passcode hash is stored anywhere in this repo. The build tool can typo-check against an optional local, git-ignored `src/passcode.sha256`. The plaintext passcode is never stored in this repo, in the page, or in any file — it exists only in the owner's hands.
- Wrong passcode rejected; dashboard stays unloaded. Unlock is session-scoped (the derived key in sessionStorage); closing the tab re-locks. A Lock button (bottom-right) re-locks instantly and unloads the content.
- No owner controls: no change-passcode UI, no gate toggle, no setup flow. The gate is permanently ON in code.
- Changing the passcode = re-run `tools/encrypt_page.py` with the new passcode (and update your local `src/passcode.sha256`), then commit the new `index.html`.
- Layout: this repo is public and serves GitHub Pages. The readable page lives only on the owner's machine in `src/` (git-ignored, never committed); only the encrypted `index.html` is committed. Engine, data CSVs and specs in this repo are public.
- Honest limit: the encryption is only as strong as the passcode — use 12+ characters, not a dictionary phrase. Anyone holding the passcode can read everything.
