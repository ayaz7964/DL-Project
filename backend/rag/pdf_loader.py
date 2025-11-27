# import fitz

# def extract_pdf(path):
#     doc = fitz.open(path)
#     extracted = []

#     current_heading = None
#     current_subheading = None

#     for page in doc:
#         blocks = page.get_text("dict")["blocks"]

#         for block in blocks:
#             if "lines" not in block:
#                 continue

#             for line in block["lines"]:
#                 text = " ".join(span["text"] for span in line["spans"]).strip()
#                 if not text:
#                     continue

#                 size = line["spans"][0]["size"]

#                 if size > 14:
#                     current_heading = text
#                 elif 12 < size <= 14:
#                     current_subheading = text
#                 else:
#                     extracted.append({
#                         "heading": current_heading,
#                         "subheading": current_subheading,
#                         "content": text,
#                         "source": "pdf",
#                         "file": path
#                     })

#     return extracted


# rag/pdf_loader.py
import fitz  # pymupdf
import re

def extract_pdf_with_headings(path):
    """
    Returns list of dicts:
    [{"heading": h1, "subheading": h2, "content": paragraph, "source": "pdf", "file": path}, ...]
    """
    doc = fitz.open(path)
    results = []
    current_h1 = None
    current_h2 = None

    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if "lines" not in b:
                continue
            # compute average font size in block (approx)
            spans = []
            for line in b["lines"]:
                for span in line["spans"]:
                    spans.append(span)
            if not spans:
                continue
            avg_size = sum(s["size"] for s in spans) / len(spans)
            text = " ".join(" ".join(span["text"] for span in line["spans"]) for line in b["lines"]).strip()
            text = re.sub(r"\s+", " ", text)
            if not text:
                continue

            # Heuristic: font size > 14 => heading, 12-14 => subheading
            if avg_size >= 14:
                current_h1 = text
                current_h2 = None
                continue
            elif 12 <= avg_size < 14:
                current_h2 = text
                continue
            else:
                # paragraph content
                results.append({
                    "heading": current_h1,
                    "subheading": current_h2,
                    "content": text,
                    "source": "pdf",
                    "file": path
                })
    return results
