# PDF Outline Extractor

## Overview
This solution extracts structured outlines (Title, H1, H2, H3) from PDF documents and outputs them as JSON files. It processes all PDFs in the input directory and generates corresponding JSON files in the output directory.

## Approach

### Heading Detection Strategy
- **Font Size Analysis**: Analyzes all text spans to identify the three most common font sizes, mapping them to H1, H2, and H3 levels
- **Position Filtering**: Filters out headers and footers by detecting text that appears at the top/bottom of multiple pages
- **Content Filtering**: Uses heuristics to distinguish between document headings and form field labels
- **Multilingual Support**: Handles CJK (Chinese, Japanese, Korean) characters without relying on capitalization

### Title Extraction
1. **Metadata First**: Attempts to extract title from PDF metadata
2. **Bold Text Fallback**: Uses the largest bold text on the first page
3. **Size-based Fallback**: Falls back to the largest text if no bold text is found
4. **Cleanup**: Removes common file prefixes and extensions

### Key Features
- **Form Document Handling**: Intelligently filters out form fields and labels
- **Performance Optimized**: Processes up to 50 pages per PDF within time constraints
- **Robust Error Handling**: Continues processing even if individual files fail
- **Offline Operation**: No network calls or external dependencies

## Dependencies

### Core Libraries
- **PyMuPDF (fitz)**: PDF parsing and text extraction
- **Standard Library**: os, json, re, collections (Counter, defaultdict)

### System Requirements
- **Architecture**: AMD64 (x86_64)
- **Memory**: Optimized for 16GB RAM systems
- **CPU**: Designed for 8-core systems
- **Network**: No internet access required

## Build and Run Instructions

### Build Docker Image
```bash
docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier .
```

### Run Container
```bash
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none mysolutionname:somerandomidentifier
```

### Usage
1. Place PDF files in the `input` directory
2. Run the container
3. Find output JSON files in the `output` directory

## Output Format
```json
{
  "title": "Document Title",
  "outline": [
    { "level": "H1", "text": "Main Heading", "page": 1 },
    { "level": "H2", "text": "Sub Heading", "page": 2 },
    { "level": "H3", "text": "Section Heading", "page": 3 }
  ]
}
```

## Performance Characteristics
- **Execution Time**: ≤ 10 seconds for 50-page PDFs
- **Model Size**: < 200MB (PyMuPDF only)
- **Memory Usage**: Optimized for 16GB RAM
- **CPU Usage**: Efficient for 8-core systems

## Technical Notes
- Processes PDFs up to 50 pages
- Handles multilingual content (CJK scripts)
- Filters out form fields and repeated headers/footers
- No hardcoded logic for specific documents
- Fully offline operation 