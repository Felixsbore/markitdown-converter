"""
MarkItDown Converter — turn Office/PDF files into lean, Claude-friendly Markdown.

Run locally:
    streamlit run app.py

Deploy: push this folder to a GitHub repo and deploy on share.streamlit.io
(see README.md for step-by-step PowerShell + deployment instructions).
"""

import re
import tempfile
from pathlib import Path

import streamlit as st
from markitdown import MarkItDown

# --------------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="MarkItDown → Claude-ready Markdown",
    page_icon="📄",
    layout="centered",
)

# --------------------------------------------------------------------------
# Translations
# --------------------------------------------------------------------------
TEXT = {
    "en": {
        "title": "📄 → 📝 MarkItDown Converter",
        "caption": (
            "Drop in a PDF, Word, PowerPoint, or Excel file and get back clean, "
            "compact Markdown — ready to paste into Claude with minimal wasted tokens."
        ),
        "supported_expander": "Supported file types",
        "uploader_label": "Choose a file",
        "optimize_toggle": "Optimize for token savings",
        "optimize_help": (
            "Strips redundant whitespace, blank lines, and formatting noise while "
            "keeping headings, lists, and tables intact."
        ),
        "file_info": "**File:** {name}  ·  **Size:** {size:.1f} KB",
        "convert_button": "Convert to Markdown",
        "converting_spinner": "Converting…",
        "conversion_failed": "Conversion failed: {error}",
        "done": "Done!",
        "metric_raw": "Raw tokens (est.)",
        "metric_final": "Final tokens (est.)",
        "metric_saved": "Saved",
        "preview_subheader": "Preview",
        "preview_label": "Markdown output",
        "download_button": "⬇️ Download .md file",
        "copy_expander": "Copy-paste plain text (no download needed)",
        "upload_prompt": "Upload a file above to get started.",
        "footer": (
            "Runs entirely on this server session — files aren't stored permanently. "
            "Built with [MarkItDown](https://github.com/microsoft/markitdown) + Streamlit."
        ),
        "lang_name": "English",
    },
    "no": {
        "title": "📄 → 📝 MarkItDown-konverterer",
        "caption": (
            "Last opp en PDF-, Word-, PowerPoint- eller Excel-fil, og få en ren og solid "
            "Markdown-tekst tilbake — klar til å limes rett inn i Claude, med minimal "
            "sløsing av tokens og en mer effektiv arbeidsflyt."
        ),
        "supported_expander": "Støttede filtyper",
        "uploader_label": "Velg en fil",
        "optimize_toggle": "Optimaliser for å spare tokens",
        "optimize_help": (
            "Fjerner unødvendige mellomrom, tomme linjer og formateringsstøy, "
            "samtidig som overskrifter, lister og tabeller beholdes."
        ),
        "file_info": "**Fil:** {name}  ·  **Størrelse:** {size:.1f} KB",
        "convert_button": "Konverter til Markdown",
        "converting_spinner": "Konverterer…",
        "conversion_failed": "Konvertering feilet: {error}",
        "done": "Ferdig!",
        "metric_raw": "Rå tokens (est.)",
        "metric_final": "Endelige tokens (est.)",
        "metric_saved": "Spart",
        "preview_subheader": "Forhåndsvisning",
        "preview_label": "Markdown-resultat",
        "download_button": "⬇️ Last ned .md-fil",
        "copy_expander": "Kopier ren tekst (ingen nedlasting nødvendig)",
        "upload_prompt": "Last opp en fil over for å komme i gang.",
        "footer": (
            "Alt kjører lokalt i denne økten — ingen filer blir lagret permanent. "
            "Bygget med [MarkItDown](https://github.com/microsoft/markitdown) og Streamlit."
        ),
        "lang_name": "Norsk",
    },
}

SUPPORTED = {
    "en": {
        "PDF": [".pdf"],
        "Word": [".docx", ".doc"],
        "PowerPoint": [".pptx", ".ppt"],
        "Excel": [".xlsx", ".xls", ".csv"],
        "Images (OCR)": [".png", ".jpg", ".jpeg"],
        "HTML": [".html", ".htm"],
        "Audio (transcript)": [".mp3", ".wav"],
        "Other text-ish": [".json", ".xml", ".txt"],
    },
    "no": {
        "PDF": [".pdf"],
        "Word": [".docx", ".doc"],
        "PowerPoint": [".pptx", ".ppt"],
        "Excel": [".xlsx", ".xls", ".csv"],
        "Bilder (OCR)": [".png", ".jpg", ".jpeg"],
        "HTML": [".html", ".htm"],
        "Lyd (transkripsjon)": [".mp3", ".wav"],
        "Annet tekstlignende": [".json", ".xml", ".txt"],
    },
}
ALL_EXTS = sorted({e for exts in SUPPORTED["en"].values() for e in exts})


# --------------------------------------------------------------------------
# Language selection (flag buttons)
# --------------------------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "en"

brand_col, flag_col1, flag_col2 = st.columns([4, 1, 1])
with brand_col:
    st.markdown(
        "<div style='color:gray; font-size:0.8em; padding-top:0.6em;'>"
        "Ferula Labs Etb. 2024</div>",
        unsafe_allow_html=True,
    )
with flag_col1:
    if st.button("English", help="Switch to English", use_container_width=True):
        st.session_state.lang = "en"
with flag_col2:
    if st.button("Norsk", help="Bytt til norsk", use_container_width=True):
        st.session_state.lang = "no"

lang = st.session_state.lang
t = TEXT[lang]
supported = SUPPORTED[lang]


# --------------------------------------------------------------------------
# Token-saving cleanup
# --------------------------------------------------------------------------
def optimize_markdown(text: str) -> str:
    """
    Trim the raw MarkItDown output down to something leaner for LLM context,
    without throwing away structure (headings, tables, lists) that Claude
    actually benefits from.
    """
    if not text:
        return text

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"(?<=\S)[ \t]{3,}", " ", text)
    text = re.sub(r"\n\|[\s|]*\|\n", "\n", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"(\n[-=_]{3,}\n){2,}", "\n---\n", text)

    return text.strip() + "\n"


def estimate_tokens(text: str) -> int:
    """
    Fast, dependency-free token estimate (~4 chars/token, the standard
    rule-of-thumb for English text with modern BPE tokenizers).
    """
    if not text:
        return 0
    return max(1, round(len(text) / 4))


# --------------------------------------------------------------------------
# Conversion
# --------------------------------------------------------------------------
@st.cache_resource
def get_converter() -> MarkItDown:
    return MarkItDown()


def convert_file(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    converter = get_converter()
    result = converter.convert(tmp_path)
    return result.text_content


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
st.title(t["title"])
st.caption(t["caption"])

with st.expander(t["supported_expander"], expanded=False):
    for label, exts in supported.items():
        st.markdown(f"- **{label}**: `{'`, `'.join(exts)}`")

uploaded_file = st.file_uploader(
    t["uploader_label"],
    type=[e.lstrip(".") for e in ALL_EXTS],
    accept_multiple_files=False,
)

optimize = st.toggle(t["optimize_toggle"], value=True, help=t["optimize_help"])

if uploaded_file is not None:
    file_size_kb = len(uploaded_file.getbuffer()) / 1024
    st.write(t["file_info"].format(name=uploaded_file.name, size=file_size_kb))

    if st.button(t["convert_button"], type="primary", use_container_width=True):
        with st.spinner(t["converting_spinner"]):
            try:
                raw_md = convert_file(uploaded_file)
            except Exception as e:
                st.error(t["conversion_failed"].format(error=e))
                st.stop()

            final_md = optimize_markdown(raw_md) if optimize else raw_md

            raw_tokens = estimate_tokens(raw_md)
            final_tokens = estimate_tokens(final_md)
            saved_pct = (
                round(100 * (1 - final_tokens / raw_tokens), 1)
                if raw_tokens else 0
            )

        st.success(t["done"])

        col1, col2, col3 = st.columns(3)
        col1.metric(t["metric_raw"], f"{raw_tokens:,}")
        col2.metric(t["metric_final"], f"{final_tokens:,}")
        col3.metric(t["metric_saved"], f"{saved_pct}%")

        st.subheader(t["preview_subheader"])
        st.text_area(t["preview_label"], final_md, height=400)

        out_name = Path(uploaded_file.name).stem + ".md"
        st.download_button(
            t["download_button"],
            data=final_md.encode("utf-8"),
            file_name=out_name,
            mime="text/markdown",
            use_container_width=True,
        )

        with st.expander(t["copy_expander"]):
            st.code(final_md, language="markdown")
else:
    st.info(t["upload_prompt"])

st.divider()
st.caption(t["footer"])