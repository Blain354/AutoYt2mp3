# Auto Get Tunes 🎵

An automated system for searching and downloading music from text files containing song names.

## 📋 Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Simple Method (Recommended)](#simple-method-recommended)
  - [Individual Scripts Usage](#individual-scripts-usage)
- [Database](#database)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)

## ✨ Features

- **Automatic YouTube Search**: Automatically finds song URLs on YouTube
- **Smart Duplicate Detection**: Prevents duplicate downloads based on YouTube video ID
- **Centralized Database**: Manages all entries in a persistent JSON file
- **Automatic Download**: Converts and downloads songs in MP3 format
- **Progress Bar**: Real-time progress display with remaining time estimation
- **Project Management**: Organizes downloads by project folder
- **Simple Interface**: Windows batch script for easy use

## 🔧 Prerequisites

### Required Software
- **Python 3.7+** (tested with Python 3.9+)
- **Google Chrome** (for web automation)
- **Windows** (for batch script, but Python scripts work on Linux/Mac)

### Recommended Knowledge
- Basic command line usage
- Understanding of text and JSON files

## 🚀 Installation

### 1. Clone the project
```bash
git clone https://github.com/your-username/auto-get-tunes.git
cd auto-get-tunes
```

### 2. Install Python and pip
Download Python from [python.org](https://python.org) if not already installed.

### 3. Install Python dependencies
```bash
pip install selenium webdriver-manager tqdm
```

### 4. Verify Chrome installation
Make sure Google Chrome is installed on your system. The script will automatically download the appropriate ChromeDriver.

## 📁 Project Structure

```
auto-get-tunes/
├── code/
│   ├── update_db_from_txt.py    # YouTube search and DB update
│   ├── conversion.py            # Download and conversion
│   └── tunes_database.json      # Centralized database
├── example/
│   ├── tunes.txt               # Example input file
│   └── downloads/              # Example downloads folder
├── process_tunes.bat           # Main script (Windows)
├── manage_database.py          # Database management utility
└── README.md                   # This file
```

## ⚙️ Configuration

### Modifiable parameters in `code/conversion.py`:
- `BASE_URL`: Conversion site (default: y2mate.nu)
- `HEADLESS`: Headless mode for Chrome (default: True)
- `PAGE_LOAD_TIMEOUT`: Page loading timeout

### Modifiable parameters in `code/update_db_from_txt.py`:
- `Config.timeout`: Timeout for YouTube searches
- `Config.pause_between_queries`: Delay between searches

## 🎯 Usage

### Simple Method (Recommended)

#### 1. Prepare your songs file
Create a text file (e.g., `my_songs.txt`) with one song per line:
```
Shape of You, Ed Sheeran
Blinding Lights, The Weeknd
Watermelon Sugar, Harry Styles
```

#### 2. Run the main script
```cmd
process_tunes.bat "my_songs.txt" "C:\Music\MyProject"
```

The script will:
1. Search each song on YouTube
2. Detect and report duplicates
3. Automatically download new songs
4. Organize files in the specified folder

### Individual Scripts Usage

#### YouTube search only
```bash
cd code
python update_db_from_txt.py "my_songs.txt"
```

#### Download only
```bash
cd code
python conversion.py "C:\Music\MyProject"
```

## 🗄️ Database

The database (`code/tunes_database.json`) stores:
- **title**: Song name
- **url**: YouTube URL found
- **done**: Download status (true/false/"timeout")
- **download_path**: Download folder used
- **project**: Project name (to be filled manually)

### Example entry:
```json
{
  "title": "Shape of You, Ed Sheeran",
  "url": "https://www.youtube.com/watch?v=JGwWNGJdvx8",
  "done": true,
  "download_path": "C:\\Music\\MyProject",
  "project": "Summer Playlist 2025"
}
```

## 📝 Examples

### Example 1: First project
```cmd
# Create my_songs.txt file with your favorite songs
process_tunes.bat "my_songs.txt" "C:\Music\Favorites"
```

### Example 2: Add songs to existing project
```cmd
# Create new_songs.txt with new songs
process_tunes.bat "new_songs.txt" "C:\Music\Favorites"
# Duplicates will be automatically detected
```

### Example 3: Specific project
```cmd
process_tunes.bat "workout_playlist.txt" "C:\Music\Workout"
```

## 🔧 Troubleshooting

### Common Issues

**Chrome/ChromeDriver**
- Script automatically downloads ChromeDriver
- If issues: verify Chrome is installed and up to date

**YouTube Timeouts**
- Some searches may fail (marked as "timeout")
- Re-run the script: only unprocessed entries will be retried

**File Permissions**
- Check write permissions in destination folder
- Run as administrator if necessary

**Python Dependencies**
```bash
# Reinstall dependencies
pip install --upgrade selenium webdriver-manager tqdm
```

### Frequent Error Messages

- `[ERROR] File 'xxx' does not exist`: Check input file path
- `Timeout: 'Download' button not found`: Network issue or site temporarily unavailable
- `Empty database`: Normal on first run, DB will be created automatically

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Possible Improvement Areas
- Support for other platforms (Spotify, SoundCloud)
- Graphical user interface
- Linux/Mac support for main script
- Playlist management
- Audio quality filters

## ⚠️ Legal Disclaimers

- Respect copyright and terms of use of platforms
- Use only for personal purposes
- Downloading copyrighted content may be illegal in your jurisdiction
- Authors are not responsible for the use of this tool

## 📄 Disclaimer

This project was primarily developed by **Claude Sonnet 4** (Anthropic's AI assistant) under the coordination and supervision of **Guillaume Blain**.

The code was generated, tested, and refined through human-machine collaboration, demonstrating current AI capabilities for software development. All features were designed and validated by Guillaume Blain to meet real automation needs.

---

**Development**: Claude Sonnet 4 (Anthropic)  
**Coordination & Supervision**: Guillaume Blain  
**Version**: 1.0  
**Last Update**: September 2025
