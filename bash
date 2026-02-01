# install.sh
#!/bin/bash

echo "Installing Terabox Downloader Bot..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p downloads
mkdir -p logs

# Copy config if not exists
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Please edit .env file with your credentials"
fi

echo "Installation complete!"
echo "To run the bot:"
echo "source venv/bin/activate"
echo "python bot.py"
