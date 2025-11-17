#!/bin/bash
# Download Research Papers from arXiv

DOWNLOAD_DIR="research_papers"
mkdir -p "$DOWNLOAD_DIR"

echo "📥 Downloading research papers from arXiv..."

# Machine Learning papers
papers=(
    # Attention is All You Need (Transformers)
    "https://arxiv.org/pdf/1706.03762.pdf"
    
    # BERT
    "https://arxiv.org/pdf/1810.04805.pdf"
    
    # ResNet
    "https://arxiv.org/pdf/1512.03385.pdf"
    
    # GANs
    "https://arxiv.org/pdf/1406.2661.pdf"
    
    # YOLO
    "https://arxiv.org/pdf/1506.02640.pdf"
)

filenames=(
    "attention_is_all_you_need.pdf"
    "bert_paper.pdf"
    "resnet_paper.pdf"
    "gan_paper.pdf"
    "yolo_paper.pdf"
)

for i in "${!papers[@]}"; do
    url="${papers[$i]}"
    filename="${filenames[$i]}"
    output="$DOWNLOAD_DIR/$filename"
    
    if [ -f "$output" ]; then
        echo "⏭️  Skipping (exists): $filename"
    else
        echo "📥 Downloading: $filename"
        wget -q --timeout=30 -O "$output" "$url"
        
        if [ $? -eq 0 ] && [ -f "$output" ]; then
            size=$(du -h "$output" | cut -f1)
            echo "   ✅ Downloaded: $filename ($size)"
        else
            echo "   ❌ Failed: $filename"
            rm -f "$output"
        fi
    fi
done

echo ""
echo "📊 Summary:"
echo "   Location: $DOWNLOAD_DIR/"
echo "   Files: $(ls -1 $DOWNLOAD_DIR/*.pdf 2>/dev/null | wc -l) PDFs"
echo ""
echo "🚀 Next: Upload papers with bulk_upload.sh"
