"""
MarkItDown Converter — turn Office/PDF files into lean, Claude-friendly Markdown.

Run locally:
    streamlit run app.py

Deploy: push this folder to a GitHub repo and deploy on share.streamlit.io
(see README.md for step-by-step PowerShell + deployment instructions).
"""

import io
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

SUPPORTED = {
    "PDF": [".pdf"],
    "Word": [".docx", ".doc"],
    "PowerPoint": [".pptx", ".ppt"],
    "Excel": [".xlsx", ".xls", ".csv"],
    "Images (OCR)": [".png", ".jpg", ".jpeg"],
    "HTML": [".html", ".htm"],
    "Audio (transcript)": [".mp3", ".wav"],
    "Other text-ish": [".json", ".xml", ".txt"],
}
ALL_EXTS = sorted({e for exts in SUPPORTED.values() for e in exts})


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

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse 3+ blank lines down to a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip trailing whitespace on every line
    text = "\n".join(line.rstrip() for line in text.split("\n"))

    # Collapse runs of spaces/tabs (but keep leading indentation for code/lists
    # by only touching runs of 3+ spaces that aren't at line start)
    text = re.sub(r"(?<=\S)[ \t]{3,}", " ", text)

    # Remove empty markdown table rows / stray pipe-only lines (common noise
    # from slide/sheet extraction)
    text = re.sub(r"\n\|[\s|]*\|\n", "\n", text)

    # Drop leftover HTML comments some converters leave behind
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Collapse repeated separator lines (---, ===, ___ used as slide breaks)
    text = re.sub(r"(\n[-=_]{3,}\n){2,}", "\n---\n", text)

    return text.strip() + "\n"


def estimate_tokens(text: str) -> int:
    """
    Fast, dependency-free token estimate (~4 chars/token, the standard
    rule-of-thumb for English text with modern BPE tokenizers). Good enough
    for a "how much context will this cost" indicator.
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
st.title("📄 → 📝 MarkItDown Converter")
st.caption(
    "Drop in a PDF, Word, PowerPoint, or Excel file and get back clean, "
    "compact Markdown — ready to paste into Claude with minimal wasted tokens."
)

with st.expander("Supported file types", expanded=False):
    for label, exts in SUPPORTED.items():
        st.markdown(f"- **{label}**: `{'`, `'.join(exts)}`")

uploaded_file = st.file_uploader(
    "Choose a file",
    type=[e.lstrip(".") for e in ALL_EXTS],
    accept_multiple_files=False,
)

optimize = st.toggle("Optimize for token savings", value=True, help=(
    "Strips redundant whitespace, blank lines, and formatting noise while "
    "keeping headings, lists, and tables intact."
))

if uploaded_file is not None:
    file_size_kb = len(uploaded_file.getbuffer()) / 1024
    st.write(f"**File:** {uploaded_file.name}  ·  **Size:** {file_size_kb:.1f} KB")

    if st.button("Convert to Markdown", type="primary", use_container_width=True):
        with st.spinner("Converting…"):
            try:
                raw_md = convert_file(uploaded_file)
            except Exception as e:
                st.error(f"Conversion failed: {e}")
                st.stop()

            final_md = optimize_markdown(raw_md) if optimize else raw_md

            raw_tokens = estimate_tokens(raw_md)
            final_tokens = estimate_tokens(final_md)
            saved_pct = (
                round(100 * (1 - final_tokens / raw_tokens), 1)
                if raw_tokens else 0
            )

        st.success("Done!")

        col1, col2, col3 = st.columns(3)
        col1.metric("Raw tokens (est.)", f"{raw_tokens:,}")
        col2.metric("Final tokens (est.)", f"{final_tokens:,}")
        col3.metric("Saved", f"{saved_pct}%")

        st.subheader("Preview")
        st.text_area("Markdown output", final_md, height=400)

        out_name = Path(uploaded_file.name).stem + ".md"
        st.download_button(
            "⬇️ Download .md file",
            data=final_md.encode("utf-8"),
            file_name=out_name,
            mime="text/markdown",
            use_container_width=True,
        )

        with st.expander("Copy-paste plain text (no download needed)"):
            st.code(final_md, language="markdown")
else:
    st.info("Upload a file above to get started.")

st.divider()
st.caption(
    "Runs entirely on this server session — files aren't stored permanently. "
    "Built with [MarkItDown](https://github.com/microsoft/markitdown) + Streamlit."
)
