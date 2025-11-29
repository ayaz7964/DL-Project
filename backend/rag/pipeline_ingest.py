
# rag/pipeline_ingest.py
from .pdf_loader import extract_pdf_with_headings
from .scraper_web import crawl_and_collect, crawl_site, hash_docs
from .chunker import chunk_documents
from .embeddings import embed_texts
from .chroma_db import collection, add_in_batches
import json
import glob
import os
import datetime
import hashlib

# put your university pages here
UNIVERSITY_URLS = [
    "https://www.iba-suk.edu.pk/",
    "https://www.iba-suk.edu.pk/home/contact",
    "https://www.iba-suk.edu.pk/student-resources",
    "https://www.iba-suk.edu.pk/faculty/all-doctors",
    "https://www.iba-suk.edu.pk/admissions",
    "https://www.iba-suk.edu.pk/admissions/under-graduate-programs",
    "https://www.iba-suk.edu.pk/admissions/foundation-program",
    "https://www.iba-suk.edu.pk/admissions/announcements",
    "https://iba-suk.edu.pk/admissions/sample-papers",
    "http://applyadmission.iba-suk.edu.pk/",
   "https://www.iba-suk.edu.pk/faculty/all-doctors", 
    "https://www.iba-suk.edu.pk/careers/announcements",
    "https://dob.iba-suk.edu.pk/UndergradPrograms/ContactGen",
    "https://ee.iba-suk.edu.pk/contact/contactus.html",
    "https://education.iba-suk.edu.pk/home/contacts",
    "https://library.iba-suk.edu.pk/",
    "https://www.iba-suk.edu.pk/sts/announcements",
    "https://edc.iba-suk.edu.pk/contactus.html",
    "https://siam-sc.iba-suk.edu.pk/",
    "https://www.iba-suk.edu.pk/kandhkot-campus/contacts",
]

MANIFEST_PATH = os.path.join("data", ".ingest_manifest.json")
SCRAPED_SAVE_PATH = os.path.join("data", "scraped", "latest_web.json")
WEB_RESCRAPE_HOURS = float(os.getenv("WEB_RESCRAPE_HOURS", "12"))

def _file_signature(paths):
    """
    Build a dict of absolute path -> {mtime, size} for change detection.
    """
    sig = {}
    for p in paths:
        if not os.path.isfile(p):
            continue
        try:
            st = os.stat(p)
            sig[os.path.abspath(p)] = {"mtime": st.st_mtime, "size": st.st_size}
        except OSError:
            continue
    return sig

def _current_manifest(pdfs_dir="data/pdfs", send_dir="send_files"):
    pdfs = glob.glob(os.path.join(pdfs_dir, "*.pdf"))
    send_pdfs = glob.glob(os.path.join(send_dir, "*.pdf")) if os.path.isdir(send_dir) else []
    return _file_signature(pdfs + send_pdfs)

def _load_manifest(path=MANIFEST_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_manifest(manifest, path=MANIFEST_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

def _load_cached_web_docs(path=SCRAPED_SAVE_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
            return obj.get("docs", []), obj.get("scraped_at")
    except Exception:
        return [], None


def ingest_needed(file_sig, web_hash, web_timestamp, manifest_path=MANIFEST_PATH):
    """
    Returns (needed, snapshot, changed_files, web_changed)
    - changed_files: list of file paths that are new or modified
    - web_changed: bool if web_hash differs
    """
    previous = _load_manifest(manifest_path)
    prev_files = previous.get("files", {}) if isinstance(previous, dict) else {}
    prev_web_hash = previous.get("web_hash", "")
    prev_web_ts = previous.get("web_timestamp")

    changed_files = []
    for path, sig in file_sig.items():
        if path not in prev_files or prev_files[path] != sig:
            changed_files.append(path)

    web_changed = bool(web_hash and web_hash != prev_web_hash)
    needed = bool(changed_files or web_changed or not previous)
    current = {"files": file_sig, "web_hash": web_hash, "web_timestamp": web_timestamp}
    return needed, current, changed_files, web_changed

def ingest_all(
    pdfs_dir="data/pdfs",
    scraped_dir="data/scraped",
    send_dir="send_files",
    university_urls=None,
    pre_fetched_web=None,
    include_web=True,
    file_paths=None,
):
    """
    Full run: scrape website + facebook -> parse PDFs -> chunk -> embed -> store in Chroma.
    Optionally limit to specific file paths and/or skip web if unchanged.
    """
    final_docs = []
    university_urls = university_urls or UNIVERSITY_URLS

    # 1) website scraping (only if requested)
    web_hash = ""
    if include_web:
        try:
            web_docs = pre_fetched_web if pre_fetched_web is not None else crawl_site(university_urls)
            web_hash = hash_docs(web_docs)
            final_docs.extend(web_docs)
            # persist latest web scrape
            try:
                os.makedirs(os.path.dirname(SCRAPED_SAVE_PATH), exist_ok=True)
                with open(SCRAPED_SAVE_PATH, "w", encoding="utf-8") as f:
                    json.dump({"scraped_at": datetime.datetime.utcnow().isoformat(), "urls": university_urls, "docs": web_docs, "web_hash": web_hash}, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print("warning: could not write scraped snapshot", e)
        except Exception as e:
            print("website scrape failed", e)

    # 2) facebook (removed per request)
    fb = []

    # 3) local PDFs in data/pdfs (and send_files if you want)
    if file_paths is not None:
        target_paths = file_paths
    else:
        target_paths = glob.glob(os.path.join(pdfs_dir, "*.pdf"))
        if os.path.isdir(send_dir):
            target_paths += glob.glob(os.path.join(send_dir, "*.pdf"))

    pdf_count = 0
    for p in target_paths:
        if not os.path.isfile(p):
            continue
        try:
            pdf_docs = extract_pdf_with_headings(p)
            final_docs.extend(pdf_docs)
            pdf_count += 1
        except Exception as e:
            print("pdf parse error", p, e)

    # 4) chunking
    web_ct = len(web_docs) if include_web else 0
    fb_ct = len(fb) if "fb" in locals() else 0
    pdf_section_ct = len(final_docs) - web_ct - fb_ct
    print(f"[ingest] collected -> web_sections:{web_ct} fb_posts:{fb_ct} pdf_files:{pdf_count} pdf_sections:{pdf_section_ct}")

    chunks = chunk_documents(final_docs, chunk_size=600, overlap=100)
    total_chunks = len(chunks)
    if not total_chunks:
        print("No chunks to add.")
        return

    print(f"[ingest] chunked into {total_chunks} pieces; embedding and upserting...")

    # 5) embed and upsert to chroma
    docs = []
    metadatas = []
    ids = []
    seen_ids = set()
    for c in chunks:
        base = c["document"]
        meta = c.get("metadata", {}) or {}
        key_parts = [
            meta.get("file") or "",
            meta.get("url") or "",
            meta.get("heading") or "",
            base,
        ]
        cid = hashlib.sha1("||".join(key_parts).encode("utf-8")).hexdigest()
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        ids.append(cid)
        docs.append(base)
        metadatas.append(meta)

    embs = embed_texts(docs)
    add_in_batches(
        ids=ids,
        documents=docs,
        embeddings=embs,
        metadatas=metadatas,
        progress=True,
        upsert=True,
    )
    print(f"[ingest] completed: {len(ids)} chunks ingested/updated; collection count now {collection.count()}.")
    return web_hash


def ingest_if_changed(pdfs_dir="data/pdfs", send_dir="send_files", university_urls=None):
    """
    Run ingest_all only if local files or scraped web content changed since last snapshot.
    """
    university_urls = university_urls or UNIVERSITY_URLS
    force = os.getenv("FORCE_INGEST", "0") == "1"

    # local files signature
    file_sig = _current_manifest(pdfs_dir, send_dir)

    # determine whether to rescrape web based on last timestamp
    previous = _load_manifest()
    prev_web_ts = previous.get("web_timestamp")
    prev_web_hash = previous.get("web_hash", "")

    web_docs = []
    web_hash = prev_web_hash or ""
    web_timestamp = prev_web_ts
    should_rescrape = True

    if prev_web_ts:
        try:
            prev_dt = datetime.datetime.fromisoformat(prev_web_ts)
            age_hours = (datetime.datetime.utcnow() - prev_dt).total_seconds() / 3600
            if age_hours < WEB_RESCRAPE_HOURS:
                should_rescrape = False
        except Exception:
            should_rescrape = True

    if should_rescrape:
        try:
            web_docs = crawl_and_collect(university_urls)
            web_hash = hash_docs(web_docs)
            web_timestamp = datetime.datetime.utcnow().isoformat()
        except Exception as e:
            print("web scrape failed during change check", e)
    else:
        cached_docs, cached_ts = _load_cached_web_docs()
        web_docs = cached_docs
        web_timestamp = prev_web_ts or cached_ts

    needed, snapshot, changed_files, web_changed = ingest_needed(file_sig, web_hash, web_timestamp)
    if not needed and not force:
        print("No data changes detected; skipping ingest.")
        return False
    if force:
        print("FORCE_INGEST=1 set; running full ingest regardless of manifest.")
        changed_files = None  # process all files
        web_changed = True    # force web scrape

    if changed_files:
        print(f"Detected {len(changed_files)} changed/new files; ingesting only those.")
    else:
        print("No file changes detected.")
    if web_changed:
        print("Website content changed; refreshing web scrape.")
    else:
        print("Website content unchanged; skipping web scrape.")

    final_web_hash = ingest_all(
        pdfs_dir=pdfs_dir,
        send_dir=send_dir,
        university_urls=university_urls,
        pre_fetched_web=web_docs if web_changed else None,
        include_web=web_changed,
        file_paths=changed_files if changed_files else [],
    )
    snapshot["web_hash"] = final_web_hash or web_hash
    snapshot["web_timestamp"] = web_timestamp
    _save_manifest(snapshot)
    return True


def update_manifest_snapshot(pdfs_dir="data/pdfs", send_dir="send_files"):
    """
    Refresh manifest after manual uploads so future startups don't re-ingest unnecessarily.
    """
    previous = _load_manifest()
    snapshot = {
        "files": _current_manifest(pdfs_dir, send_dir),
        "web_hash": previous.get("web_hash", ""),
        "web_timestamp": previous.get("web_timestamp"),
    }
    _save_manifest(snapshot)
    return snapshot
