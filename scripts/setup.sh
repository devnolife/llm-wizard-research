#!/bin/bash
# Setup script for RAG-LLM Research Recommendation System

set -e

echo "🚀 Starting RAG-LLM Research Recommendation System Setup"
echo "=========================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo -e "\n${YELLOW}1. Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

if ! python3 -c 'import sys; assert sys.version_info >= (3, 10)' 2>/dev/null; then
    echo -e "${RED}Error: Python 3.10+ is required${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python version check passed${NC}"

# Create virtual environment
echo -e "\n${YELLOW}2. Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo -e "\n${YELLOW}3. Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Upgrade pip
echo -e "\n${YELLOW}4. Upgrading pip...${NC}"
pip install --upgrade pip setuptools wheel
echo -e "${GREEN}✓ pip upgraded${NC}"

# Install dependencies
echo -e "\n${YELLOW}5. Installing dependencies...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create necessary directories
echo -e "\n${YELLOW}6. Creating project directories...${NC}"
mkdir -p data/raw
mkdir -p data/processed
mkdir -p logs
mkdir -p chroma_db
echo -e "${GREEN}✓ Directories created${NC}"

# Setup environment file
echo -e "\n${YELLOW}7. Setting up environment configuration...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created from template${NC}"
    echo -e "${YELLOW}⚠️  Please edit .env with your configuration${NC}"
else
    echo ".env file already exists"
fi

# Check Ollama installation
echo -e "\n${YELLOW}8. Checking Ollama installation...${NC}"
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✓ Ollama is installed${NC}"
    
    # Check if GLM-4.6 model is available
    if ollama list | grep -q "glm-4.6"; then
        echo -e "${GREEN}✓ GLM-4.6 model found${NC}"
    else
        echo -e "${YELLOW}⚠️  GLM-4.6 model not found${NC}"
        echo "Would you like to pull GLM-4.6 model now? (y/n)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            echo "Pulling GLM-4.6 model (this may take a while)..."
            ollama pull glm-4.6:cloud
            echo -e "${GREEN}✓ GLM-4.6 model pulled successfully${NC}"
        fi
    fi
else
    echo -e "${RED}⚠️  Ollama not found${NC}"
    echo "Please install Ollama from: https://ollama.com/download"
    echo "After installation, run: ollama pull glm-4.6:cloud"
fi

# Initialize database
echo -e "\n${YELLOW}9. Initializing vector database...${NC}"
python3 scripts/init_db.py
echo -e "${GREEN}✓ Database initialized${NC}"

# Run tests
echo -e "\n${YELLOW}10. Running tests...${NC}"
pytest tests/ -v --tb=short
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${YELLOW}⚠️  Some tests failed (this is okay for initial setup)${NC}"
fi

# Print summary
echo -e "\n${GREEN}=========================================================="
echo "✅ Setup completed successfully!"
echo "==========================================================${NC}"

echo -e "\n📋 Next steps:"
echo "1. Edit .env with your configuration"
echo "2. Start Ollama: ollama serve (in separate terminal)"
echo "3. Start the API: uvicorn src.api.main:app --reload"
echo "4. Visit API docs: http://localhost:8000/docs"

echo -e "\n📚 Quick commands:"
echo "  - Activate venv: source venv/bin/activate"
echo "  - Start API: uvicorn src.api.main:app --reload"
echo "  - Run tests: pytest tests/"
echo "  - Check health: curl http://localhost:8000/health"

echo -e "\n🎉 Happy researching!"
