#!/bin/bash
# Bulk PDF Upload Script
# Usage: ./bulk_upload.sh /path/to/pdfs/

set -e

PDF_DIR="${1:-.}"
API_URL="${2:-http://localhost:8000/api/ingest}"

if [ ! -d "$PDF_DIR" ]; then
    echo "❌ Error: Directory not found: $PDF_DIR"
    exit 1
fi

echo "📁 Searching for PDFs in: $PDF_DIR"
PDF_FILES=($(find "$PDF_DIR" -maxdepth 1 -name "*.pdf" -type f))

if [ ${#PDF_FILES[@]} -eq 0 ]; then
    echo "❌ No PDF files found in: $PDF_DIR"
    exit 1
fi

echo "📊 Found ${#PDF_FILES[@]} PDF file(s)"
echo "🚀 Starting upload..."
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0

for pdf_file in "${PDF_FILES[@]}"; do
    filename=$(basename "$pdf_file")
    echo "⏳ Uploading: $filename"
    
    response=$(curl -s -X POST \
        -F "file=@$pdf_file" \
        "$API_URL")
    
    if echo "$response" | grep -q '"success":true' || echo "$response" | grep -q '"success": true'; then
        echo "✅ Success: $filename"
        doc_id=$(echo "$response" | grep -o '"doc_id":"[^"]*"' | cut -d'"' -f4)
        chunks=$(echo "$response" | grep -o '"chunks_created":[0-9]*' | cut -d':' -f2)
        echo "   📄 Document ID: ${doc_id:0:12}..."
        echo "   📦 Chunks created: $chunks"
        ((SUCCESS_COUNT++))
    else
        echo "❌ Failed: $filename"
        echo "   Error: $response"
        ((FAIL_COUNT++))
    fi
    echo ""
    sleep 0.5  # Avoid overwhelming the server
done

echo "================================"
echo "📊 Upload Summary"
echo "================================"
echo "✅ Successful: $SUCCESS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo "📁 Total: ${#PDF_FILES[@]}"
echo ""

if [ $SUCCESS_COUNT -gt 0 ]; then
    echo "🎉 Upload completed! Check your knowledge base."
else
    echo "⚠️  No files were uploaded successfully."
fi
