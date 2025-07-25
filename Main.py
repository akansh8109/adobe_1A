import os
import json
import fitz  # PyMuPDF
from collections import Counter, defaultdict
import re

# Docker paths for input/output
INPUT_DIR = '/app/input'
OUTPUT_DIR = '/app/output'
MAX_PAGES = 50


def has_cjk(text):
    """Check if text contains CJK characters for multilingual support."""
    for c in text:
        if ('\u4e00' <= c <= '\u9fff') or ('\u3040' <= c <= '\u30ff') or ('\uac00' <= c <= '\ud7af'):
            return True
    return False


def is_valid_heading(text):
    """Filter out form fields and keep real document headings."""
    text = text.strip()
    if len(text) < 3:
        return False
    # Skip numbers and short words
    if re.match(r'^[\d\.]+$', text) or (len(text.split()) == 1 and len(text) < 4):
        return False
    # Skip form field words
    form_words = {
        'name', 'age', 'date', 'rs', 's.no', 'sno', 'signature', 'designation',
        'service', 'pay', 'si', 'npa', 'permanent', 'temporary', 'home', 'town',
        'recorded', 'book', 'wife', 'husband', 'employed', 'entitled', 'ltc',
        'concession', 'availed', 'visiting', 'block', 'india', 'place', 'visited',
        'single', 'rail', 'fare', 'bus', 'from', 'headquarters', 'shortest',
        'route', 'persons', 'respect', 'whom', 'proposed', 'relationship',
        'amount', 'advance', 'required', 'declare', 'particulars', 'furnished',
        'true', 'correct', 'knowledge', 'undertake', 'produce', 'tickets',
        'outward', 'journey', 'receipt', 'refund', 'entire', 'lump', 'sum'
    }
    words = text.lower().split()
    form_count = sum(1 for word in words if word in form_words)
    if form_count > len(words) * 0.8:
        return False
    # Skip form labels and long text
    if text.endswith(':') or len(text.split()) > 10:
        return False
    return True


def extract_title(doc):
    """Extract document title from metadata or first page."""
    # Try metadata first
    meta = doc.metadata.get('title')
    if meta and meta.strip():
        title = meta.strip()
        # Clean up common prefixes
        if title.startswith('Microsoft Word - '):
            title = title.replace('Microsoft Word - ', '')
        if title.endswith('.doc') or title.endswith('.docx'):
            title = title[:-4] if title.endswith('.docx') else title[:-3]
        return title
    # Fallback to largest bold text on first page
    page = doc[0]
    blocks = page.get_text('dict')['blocks']
    candidates = []
    for block in blocks:
        if 'lines' not in block:
            continue
        for line in block['lines']:
            for span in line['spans']:
                t = span['text'].strip()
                if t and span['size'] >= 15 and span['flags'] & 2:
                    candidates.append((span['size'], t))
    if candidates:
        return max(candidates, key=lambda x: x[0])[1]
    # Last resort: largest text
    all_texts = [(span['size'], span['text'].strip())
                 for block in blocks if 'lines' in block
                 for line in block['lines']
                 for span in line['spans'] if span['text'].strip()]
    if all_texts:
        return max(all_texts, key=lambda x: x[0])[1]
    return "Untitled PDF"


def get_heading_levels(font_sizes):
    """Determine H1, H2, H3 font sizes based on frequency."""
    counts = Counter(font_sizes)
    common = [s for s, _ in counts.most_common()]
    common = sorted(common, reverse=True)
    return (common + [0, 0, 0])[:3]


def find_repeated_elements(lines, num_pages, page_height):
    """Identify headers/footers that appear on multiple pages."""
    counter = defaultdict(int)
    for feat in lines:
        y0, y1 = feat['y0'], feat['y1']
        txt = feat['text']
        if y0 < page_height * 0.1 or y1 > page_height * 0.9:
            counter[txt] += 1
    return {t for t, c in counter.items() if c > num_pages // 2}


def extract_outline(pdf_path):
    """Main function to extract PDF outline."""
    doc = fitz.open(pdf_path)
    outline = []
    font_sizes = []
    lines = []
    num_pages = min(len(doc), MAX_PAGES)
    page_height = doc[0].rect.height if num_pages > 0 else 0

    # Collect all text lines and their properties
    for i in range(num_pages):
        page = doc[i]
        blocks = page.get_text("dict")['blocks']
        for block in blocks:
            if 'lines' not in block:
                continue
            for line in block['lines']:
                txt = ''.join([span['text'] for span in line['spans']]).strip()
                if not txt or not txt.isprintable() or len(txt.split()) > 20:
                    continue
                size = max([span['size'] for span in line['spans']])
                bold = any(span['flags'] & 2 for span in line['spans'])
                y0 = min(span['bbox'][1] for span in line['spans'])
                y1 = max(span['bbox'][3] for span in line['spans'])
                font_sizes.append(size)
                lines.append({
                    'text': txt,
                    'size': size,
                    'bold': bold,
                    'y0': y0,
                    'y1': y1,
                    'page': i + 1
                })

    # Filter out headers/footers
    repeated = find_repeated_elements(lines, num_pages, page_height)
    
    # Get heading font sizes
    h1_size, h2_size, h3_size = get_heading_levels(font_sizes)

    # Extract headings
    for feat in lines:
        txt = feat['text']
        if txt in repeated or not is_valid_heading(txt):
            continue
        size = feat['size']
        bold = feat['bold']
        page_num = feat['page']
        
        # Determine heading level
        if size == h1_size and (bold or not has_cjk(txt)):
            outline.append({"level": "H1", "text": txt, "page": page_num})
        elif size == h2_size:
            outline.append({"level": "H2", "text": txt, "page": page_num})
        elif size == h3_size:
            outline.append({"level": "H3", "text": txt, "page": page_num})

    title = extract_title(doc)
    return {"title": title, "outline": outline}


def process_pdfs():
    """Process all PDFs in input directory."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    for filename in os.listdir(INPUT_DIR):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(INPUT_DIR, filename)
            output_path = os.path.join(OUTPUT_DIR, filename[:-4] + '.json')
            
            try:
                outline_data = extract_outline(pdf_path)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(outline_data, f, ensure_ascii=False, indent=2)
                print(f"Processed {filename} -> {output_path}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")


if __name__ == "__main__":
    process_pdfs()
