"""🔎 Cari Paper — pencarian multi-sumber + unduh PDF open-access legal + analisis."""

from __future__ import annotations

import requests
import streamlit as st

from common import api_base

SOURCE_OPTIONS = {
    "arxiv": "arXiv (tanpa key)",
    "europe_pmc": "Europe PMC (tanpa key)",
    "crossref": "CrossRef (tanpa key)",
    "semantic_scholar": "Semantic Scholar",
    "core": "CORE (key gratis, banyak PDF OA)",
    "pubmed": "PubMed",
    "scopus": "Scopus (pakai ELSEVIER_API_KEY — jalan!)",
    "sciencedirect": "ScienceDirect (perlu IP kampus/insttoken)",
}
DEFAULT_SOURCES = ["arxiv", "europe_pmc", "scopus"]

SOURCE_BADGES = {
    "arxiv": "🟥 arXiv",
    "europe_pmc": "🟩 Europe PMC",
    "crossref": "🟨 CrossRef",
    "semantic_scholar": "🟦 Semantic Scholar",
    "core": "🟪 CORE",
    "pubmed": "🟫 PubMed",
    "sciencedirect": "🟧 ScienceDirect",
    "scopus": "🔶 Scopus",
}


def search_papers(query: str, sources: list[str], max_results: int,
                  year_from: int | None, year_to: int | None) -> list[dict] | None:
    payload = {
        "query": query,
        "sources": sources,
        "max_results": max_results,
        "deduplicate": True,
        "year_from": year_from,
        "year_to": year_to,
    }
    try:
        r = requests.post(f"{api_base()}/papers/search", json=payload, timeout=120)
        r.raise_for_status()
        return r.json().get("papers", [])
    except requests.RequestException as exc:
        st.session_state["last_error"] = f"Pencarian gagal: {exc}"
        return None


def download_and_analyze(papers: list[dict]) -> dict | None:
    body = {
        "papers": [
            {
                "title": p.get("title") or "paper",
                "doi": p.get("doi"),
                "pdf_url": p.get("pdf_url"),
                "source_api": p.get("source_api") or p.get("source"),
            }
            for p in papers
        ]
    }
    try:
        r = requests.post(f"{api_base()}/papers/download-and-analyze", json=body, timeout=300)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        st.session_state["last_error"] = f"Unduh & analisis gagal: {exc}"
        return None


def idea_to_query(idea: str) -> dict | None:
    try:
        r = requests.post(f"{api_base()}/papers/idea-to-query", json={"idea": idea}, timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        detail = ""
        if getattr(exc, "response", None) is not None:
            try:
                detail = exc.response.json().get("detail", "")
            except Exception:
                detail = exc.response.text[:200]
        st.session_state["last_error"] = f"Gagal mengubah ide → kata kunci: {detail or exc}"
        return None


def fetch_pdf_bytes(paper: dict) -> tuple[bytes, str] | None:
    """Unduh satu PDF via backend; return (bytes, nama_file) atau None."""
    body = {
        "title": paper.get("title") or "paper",
        "doi": paper.get("doi"),
        "pdf_url": paper.get("pdf_url"),
        "source_api": paper.get("source_api") or paper.get("source"),
    }
    try:
        r = requests.post(f"{api_base()}/papers/fetch-pdf", json=body, timeout=180)
        r.raise_for_status()
        dispo = r.headers.get("Content-Disposition", "")
        name = "paper.pdf"
        if 'filename="' in dispo:
            name = dispo.split('filename="', 1)[1].rstrip('"')
        return r.content, name
    except requests.RequestException as exc:
        detail = ""
        if getattr(exc, "response", None) is not None:
            try:
                detail = exc.response.json().get("detail", "")
            except Exception:
                detail = exc.response.text[:200]
        st.session_state["last_error"] = f"Unduh PDF gagal: {detail or exc}"
        return None


def _paper_key(p: dict) -> str:
    return p.get("doi") or p.get("paper_id") or p.get("url") or p.get("title", "")


st.title("🔎 Cari Paper")
st.caption(
    "Dua cara memulai: **unggah PDF sendiri** di halaman 🔬 Proses & Hasil, atau di sini — "
    "**tulis ide penelitian / kata kunci** → jurnal relevan muncul dari 8 sumber akademik resmi → "
    "unduh PDF **per dokumen** ke laptop Anda, atau centang beberapa lalu analisis sekaligus."
)

if err := st.session_state.pop("last_error", None):
    st.error(err)

mode = st.radio(
    "Cara mencari",
    ["💡 Ide penelitian (AI ubah jadi kata kunci)", "🔑 Kata kunci langsung"],
    horizontal=True,
    label_visibility="collapsed",
    key="paper_mode",
)
idea_mode = mode.startswith("💡")

with st.form("paper_search"):
    if idea_mode:
        idea_text = st.text_area(
            "Ide penelitian (boleh Bahasa Indonesia)",
            value=st.session_state.get("paper_idea", ""),
            placeholder=(
                "contoh: Saya ingin membangun sistem ekstraksi struk belanja otomatis "
                "menggunakan OCR dan LLM untuk membantu pencatatan keuangan pribadi"
            ),
            height=100,
        )
        query = ""
    else:
        query = st.text_input(
            "Kata kunci pencarian",
            value=st.session_state.get("paper_query", ""),
            placeholder="contoh: receipt OCR information extraction deep learning",
        )
        idea_text = ""
    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
    sources = c1.multiselect(
        "Sumber", list(SOURCE_OPTIONS), default=DEFAULT_SOURCES,
        format_func=lambda s: SOURCE_OPTIONS[s],
    )
    year_from = c2.number_input("Dari tahun", 1990, 2030, 2018)
    year_to = c3.number_input("Sampai", 1990, 2030, 2026)
    max_results = c4.number_input("Maks/sumber", 1, 50, 10)
    submitted = st.form_submit_button("🔎 Cari", type="primary", width="stretch")

with st.expander("🔑 Status sumber & cara menambah API key"):
    st.markdown(
        "- **arXiv, Europe PMC, CrossRef** — langsung jalan tanpa key.\n"
        "- **Scopus** ✅ — sudah aktif dengan `ELSEVIER_API_KEY` Anda: 90+ juta record semua "
        "penerbit (termasuk konten ScienceDirect), tersortir jumlah sitasi. PDF open-access "
        "otomatis dicari via DOI (Unpaywall) saat unduh.\n"
        "- **CORE** — key sudah terpasang; server CORE kadang lambat/overload, coba lagi bila kosong.\n"
        "- **ScienceDirect** — key valid, tetapi pencariannya hanya bisa dari jaringan IP kampus "
        "pelanggan Elsevier atau dengan `ELSEVIER_INSTTOKEN` (permintaan resmi yang sedang Anda "
        "ajukan). Sementara itu pakai **Scopus** — datanya mencakup ScienceDirect.\n"
        "- Setelah mengubah `.env`, backend --reload otomatis memuat ulang."
    )

if submitted:
    if idea_mode and not idea_text.strip():
        st.warning("Tulis ide penelitian dulu.")
    elif not idea_mode and not query.strip():
        st.warning("Isi kata kunci dulu.")
    elif not sources:
        st.warning("Pilih minimal satu sumber.")
    else:
        if not idea_mode:
            st.session_state.pop("paper_generated", None)
        if idea_mode:
            st.session_state["paper_idea"] = idea_text
            with st.spinner("🤖 AI mengubah ide menjadi kata kunci akademik…"):
                converted = idea_to_query(idea_text.strip())
            if converted:
                query = converted.get("query", "")
                st.session_state["paper_generated"] = converted
            else:
                query = ""
        if query.strip():
            st.session_state["paper_query"] = query
            with st.spinner(f"Mencari '{query}' di {len(sources)} sumber…"):
                results = search_papers(query.strip(), sources, int(max_results),
                                        int(year_from), int(year_to))
            if results is not None:
                st.session_state["paper_results"] = results
                st.session_state["paper_selected"] = set()
                st.session_state["pdf_cache"] = {}

if gen := st.session_state.get("paper_generated"):
    kw = " · ".join(gen.get("keywords") or []) or gen.get("query", "")
    engine = gen.get("engine") or "AI"
    st.info(f"💡 Ide Anda diubah **{engine}** menjadi kata kunci: **{gen.get('query','')}**"
            + (f"\n\n🏷️ {kw}" if kw else ""))

results: list[dict] = st.session_state.get("paper_results", [])

if results:
    n_oa = sum(1 for p in results if p.get("pdf_url"))
    m1, m2, m3 = st.columns(3)
    m1.metric("📚 Paper ditemukan", len(results))
    m2.metric("🔓 PDF open-access langsung", n_oa)
    m3.metric("🔍 Bisa dicoba via DOI (Unpaywall)", sum(1 for p in results if not p.get("pdf_url") and p.get("doi")))
    st.caption(
        "🔓 = PDF legal tersedia langsung · 🎯 = ada DOI, dicoba resolve versi OA via Unpaywall · "
        "🔒 = berbayar, unduh manual dari publisher lalu unggah di halaman Proses & Hasil."
    )

    selected: set = st.session_state.setdefault("paper_selected", set())

    for i, paper in enumerate(results):
        key = _paper_key(paper)
        with st.container(border=True):
            head, pick = st.columns([6, 1])
            title = (paper.get("title") or "(tanpa judul)").strip()
            year = paper.get("year") or "—"
            src = paper.get("source_api") or paper.get("source") or "?"
            badge = SOURCE_BADGES.get(src, src)
            if paper.get("pdf_url"):
                access = "🔓 :green[PDF OA]"
            elif paper.get("doi"):
                access = "🎯 :orange[coba via DOI]"
            else:
                access = "🔒 :red[berbayar]"
            head.markdown(f"**{title}**")
            authors = ", ".join(paper.get("authors") or [])[:120]
            cites = paper.get("citation_count") or 0
            journal = paper.get("journal") or ""
            head.caption(
                f"{badge} · {year}"
                + (f" · {journal}" if journal else "")
                + (f" · 📖 {cites} sitasi" if cites else "")
                + (f"  \n👤 {authors}" if authors else "")
            )
            head.markdown(access)
            links = []
            if paper.get("doi"):
                links.append(f"[DOI](https://doi.org/{paper['doi']})")
            if paper.get("url"):
                links.append(f"[Halaman paper]({paper['url']})")
            if paper.get("pdf_url"):
                links.append(f"[PDF]({paper['pdf_url']})")
            if links:
                head.caption(" · ".join(links))
            if paper.get("abstract"):
                with st.expander("📄 Abstrak"):
                    st.write(paper["abstract"])

            can_try = bool(paper.get("pdf_url") or paper.get("doi"))
            checked = pick.checkbox(
                "Pilih", key=f"pick_{i}", value=key in selected,
                disabled=not can_try,
                help=None if can_try else "Tanpa PDF/DOI — tidak bisa diunduh otomatis",
            )
            if checked:
                selected.add(key)
            else:
                selected.discard(key)

            # Unduh PDF per dokumen (langsung ke laptop pengguna)
            pdf_cache: dict = st.session_state.setdefault("pdf_cache", {})
            if can_try:
                if i in pdf_cache:
                    data, fname = pdf_cache[i]
                    pick.download_button(
                        "💾 Simpan", data=data, file_name=fname,
                        mime="application/pdf", key=f"save_{i}", width="stretch",
                        help=f"PDF siap ({len(data)/1024:.0f} KB) — klik untuk simpan",
                    )
                elif pick.button(
                    "⬇️ PDF", key=f"fetch_{i}", width="stretch",
                    help="Unduh PDF open-access legal dokumen ini",
                ):
                    with st.spinner("Mengunduh PDF dokumen ini…"):
                        got = fetch_pdf_bytes(paper)
                    if got:
                        pdf_cache[i] = got
                    st.rerun()

    st.session_state["paper_selected"] = selected
    chosen = [p for p in results if _paper_key(p) in selected]

    st.divider()
    act_l, act_r = st.columns([2, 1])
    act_l.markdown(f"**{len(chosen)}** paper dipilih (maks 15)")
    if act_r.button(
        "📥 Unduh & Analisis", type="primary", width="stretch",
        disabled=not chosen or len(chosen) > 15,
    ):
        with st.spinner(f"Mengunduh {len(chosen)} PDF & mengantre analisis…"):
            outcome = download_and_analyze(chosen)
        if outcome:
            for item in outcome.get("downloaded", []):
                st.success(f"✅ {item['title']} — `{item['file']}` (via {item['via']})")
            for item in outcome.get("skipped", []):
                st.warning(f"⏭️ {item['title']} — {item['reason']}")
            if outcome.get("success") and outcome.get("job_id"):
                st.session_state["job_id"] = outcome["job_id"]
                st.toast("Analisis dimulai!", icon="🚀")
                st.switch_page("page_analysis.py")
            else:
                st.info(
                    "Tidak ada PDF legal yang berhasil diunduh. Unduh manual dari link "
                    "publisher di atas, lalu unggah di halaman **🔬 Proses & Hasil**."
                )
elif "paper_results" in st.session_state:
    st.info("Tidak ada hasil untuk pencarian terakhir — coba kata kunci atau sumber lain.")
