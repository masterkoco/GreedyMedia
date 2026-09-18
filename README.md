⚡ Greedy Media Utility

A feature-rich, desktop-based media management and batch-encoding suite built in Python (tkinter & FFmpeg). Designed specifically for video and anime archivists, Greedy Media Utility allows you to compress large media libraries into space-efficient formats (such as 10-bit AV1 or HEVC) while automatically organizing, renaming, and fetching canonical metadata from official databases.
✨ Key Features
🎬 Advanced Batch Video Compression

    Hardware Acceleration: Supports Nvidia NVENC (AV1/HEVC) and Intel QSV hardware encoding alongside CPU-based libsvtav1 software encoding with automatic hardware fallbacks.

    Dual Compression Strategies: Choose between targeting Exact File Sizes or using Constant Quality (CQ/RF) modes with real-time bitrate estimations.

    3-Minute Scene Preview: Test your encoding settings and file size estimations on a 3-minute clip before committing to a full batch.

    Granular Stream Control: Inspect tracks, strip unwanted audio/subtitle streams, re-encode audio to ultra-slim Opus or AAC, and scale resolutions/aspect ratios.

🌐 Smart Metadata & Renaming Suite

    Official TheTVDB v4 Integration: Automatically fetches canonical English episode titles and organizes files into clean season directories (Season 01, Season 02, etc.) on disk.

    Bulk Renaming & Folder Creator: Includes character deletion filters, prefix/suffix additions, case conversions, and bulk folder generation tools.

    Safe Undo History: Features a one-click Undo Last Disk Rename feature to instantly roll back file organization changes if needed.

🎨 Customization & Safety

    Theming Engine: Switch between multiple aesthetic themes including Greedy Occult, Cyberpunk Neon, Dracula Slate, Synthwave '84, and more.

    Queue Persistence & Safe Resume: Automatically saves your queue state and settings, with built-in duplicate handling to skip or overwrite existing output files.

    Unattended Automation: Includes completion sound notifications and an optional Auto-Shutdown PC feature for long overnight processing runs.

🛠️ Prerequisites

Before running or compiling the application, ensure you have the following installed on your system:

    Python 3.10+ (Developed and tested on Python 3.13)

    FFmpeg & FFprobe installed and added to your system PATH.

    Python Libraries:
    Bash

    pip install Pillow

🚀 Running from Source

    Clone or download the repository.

    Ensure your asset image (icon.jpeg) is placed in the same directory as greedymedia_utility.py.

    Run the script:
    Bash

    python greedymedia_utility.py

📦 Building into a Standalone Executable (.exe)

If you want to compile the project into a standalone Windows application using PyInstaller so that assets are properly bundled:
Bash

python -m PyInstaller --noconsole --onedir --name "Greedy Media Utility" --add-data "icon.jpeg;." --icon="icon.ico" greedymedia_utility.py

Your compiled standalone build will be available inside the dist/Greedy Media Utility/ folder.
💖 Support & Donations

If this tool helps you clean up and shrink your media archives, consider supporting its development:

    Donate via PayPal 💖
