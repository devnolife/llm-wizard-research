"""Teks sumber tiap jurnal, disusun ulang dari chunk berurutan.

Menjawab pertanyaan "teks apa yang sebenarnya dibaca sistem dari PDF ini?".
Batas antar chunk sengaja tetap terlihat supaya asal tiap potongan bisa dilacak
ke seksi dan nomor halamannya.
"""

import streamlit as st

from research_common import fetch_fulltext, render_timeline, require_job

st.title("📖 Teks Sumber Jurnal")
st.caption("Hasil ekstraksi PDF yang benar-benar masuk ke tahap berikutnya")

job_id = require_job()
if job_id:
    render_timeline(job_id)
    st.divider()

    daftar = fetch_fulltext(job_id)
    if daftar.get("error"):
        st.warning(daftar["error"])
        st.stop()

    journals = daftar.get("journals") or []
    if not journals:
        st.info("Job ini belum punya hasil chunking.")
        st.stop()

    st.caption(f"**{len(journals)}** jurnal · "
               f"**{sum(j.get('chunks', 0) for j in journals)}** chunk total")

    labels = {f"{j['source']} — {(j.get('title') or '?')[:60]} ({j.get('chunks')} chunk)": j["source"]
              for j in journals}
    pilihan = st.selectbox("Pilih jurnal", list(labels))
    source = labels[pilihan]

    detail = fetch_fulltext(job_id, source)
    if detail.get("error"):
        st.warning(detail["error"])
        st.stop()

    meta = detail.get("journal") or {}
    chunks = detail.get("chunks") or []
    kolom = st.columns(4)
    kolom[0].metric("chunk", len(chunks))
    kolom[1].metric("tahun", meta.get("year") or "—")
    kolom[2].metric("bahasa", meta.get("language") or "—")
    kolom[3].metric("kualitas ekstraksi", meta.get("extraction_quality") or "—")
    if meta.get("title"):
        st.markdown(f"**Judul terdeteksi:** {meta['title']}")

    gabung = st.toggle("Tampilkan sebagai teks menyatu", value=False,
                       help="Chunk bertumpang tindih (overlap), jadi mode ini "
                            "mengulang sebagian kalimat di batas antar chunk.")

    if gabung:
        st.text_area("teks", "\n\n".join(c.get("text", "") for c in chunks),
                     height=600, disabled=True)
    else:
        for c in chunks:
            tanda = " · 📚 referensi" if c.get("is_reference") else ""
            st.markdown(
                f"**#{c.get('chunk_index')}** · `{c.get('section_normalized')}` · "
                f"{c.get('token_count')} token · hlm {c.get('page_start')}{tanda}")
            st.markdown(f"> {c.get('text', '')}".replace("\n", "\n> "))
            st.caption(f"`{c.get('chunk_id')}` · seksi asli: {c.get('section_raw')}")
            st.divider()

    st.download_button(
        "⬇️ Unduh teks jurnal ini (.txt)",
        "\n\n".join(f"[#{c.get('chunk_index')} {c.get('section_normalized')}]\n{c.get('text', '')}"
                    for c in chunks),
        file_name=f"{source}.txt", mime="text/plain")
