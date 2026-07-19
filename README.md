# MarkItDown Converter (for Claude)

A one-click Streamlit app: upload a PDF / Word / PowerPoint / Excel file →
get back clean, token-lean Markdown you can paste straight into Claude.

## Files in this folder

- `app.py` — the Streamlit app
- `requirements.txt` — Python dependencies
- `README.md` — this file

---

## 1. Run it locally (Windows PowerShell)

Open PowerShell in the folder containing these files (e.g. after unzipping
to `C:\Users\you\markitdown-app`), then:

```powershell
cd C:\Users\you\markitdown-app

# Create an isolated environment (only needed once)
python -m venv venv

# Activate it (do this every new terminal session)
.\venv\Scripts\Activate.ps1

# If PowerShell blocks the activation script, run this once as admin
# then retry the line above:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install dependencies
pip install -r requirements.txt

# Launch the app
streamlit run app.py
```

Streamlit will open `http://localhost:8501` in your browser. That's the app —
drag in a file, hit Convert, download the `.md`.

To stop it, go back to the PowerShell window and press `Ctrl + C`.

---

## 2. Share it with friends (deploy to a `*.streamlit.app` subdomain)

The easiest free option is **Streamlit Community Cloud**. Steps:

### a) Put the code on GitHub

```powershell
cd C:\Users\you\markitdown-app
git init
git add .
git commit -m "MarkItDown converter for Claude"
```

Create a new empty repo on github.com (no README/license, you already have
one), then:

```powershell
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

### b) Deploy

1. Go to **https://share.streamlit.io** and sign in with GitHub.
2. Click **"New app"**.
3. Pick your repo, branch (`main`), and set the main file path to `app.py`.
4. Click **Deploy**.

Streamlit Cloud installs `requirements.txt` automatically and gives you a
public URL like:

```
https://<your-app-name>.streamlit.app
```

Send that link to your friends — no install needed on their end, it just
runs in their browser.

### c) Updating later

Any time you `git push` new changes to `main`, the deployed app
auto-redeploys within a minute or two.

---

## Notes on the "token optimization" step

The app's optimizer (toggle in the UI) does the following to the raw
MarkItDown output before you download/copy it:

- Collapses multiple blank lines into one
- Strips trailing whitespace and excessive inline spacing
- Removes empty/stray table-separator rows some extractors leave behind
- Strips leftover HTML comments
- Collapses repeated slide/section separator lines

It intentionally **keeps** headings, lists, and tables intact, since those
give Claude useful structure — the goal is cutting noise, not content.

The token counter is a fast estimate (~4 characters per token), which is a
standard rule of thumb for English text and close enough to gauge savings;
it isn't the exact tokenizer Claude uses.

## Extending it

- Want batch conversion of multiple files at once? Change the
  `file_uploader` call to `accept_multiple_files=True` and loop over
  `uploaded_file` (now a list).
- Want to chain straight into the Claude API after conversion? You can add
  an `anthropic` client call in `app.py` and pass `final_md` as context —
  ask if you'd like that wired in.
