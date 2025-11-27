import fitz

def extract_pdf(path):
    doc = fitz.open(path)
    extracted = []

    current_heading = None
    current_subheading = None

    for page in doc:
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                text = " ".join(span["text"] for span in line["spans"]).strip()
                if not text:
                    continue

                size = line["spans"][0]["size"]

                if size > 14:
                    current_heading = text
                elif 12 < size <= 14:
                    current_subheading = text
                else:
                    extracted.append({
                        "heading": current_heading,
                        "subheading": current_subheading,
                        "content": text,
                        "source": "pdf",
                        "file": path
                    })

    return extracted
