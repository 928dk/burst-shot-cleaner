# Burst Shot Cleaner

> **Environment note (spec 152, 2026-10-03).** The shared `/opt/shared`
> venv pool **does not exist on localhost**. This project uses a local `./venv`; `launch.sh` self-heals it.
> `launch.sh` creates a **local** `./venv` (Python 3.14.7) on first run and
> self-heals a broken one.


A Python-based GUI tool designed to find and reduce burst shots in image directories. It identifies sequences of images taken within a short timeframe (1-2 seconds) and keeps only the first, middle, and last images, moving the others to a safe cleanup archive.

## Features
- **Intelligent Detection**: Scans for images with near-identical timestamps or sequential "BURST" naming patterns.
- **Safe Cleaning**: Instead of deleting files, it moves them to a timestamped `cleanup_archive` folder.
- **Dry Run Mode**: See exactly what will happen before committing any changes.
- **Visual Feedback**: Real-time progress tracking and space-saving statistics.
- **Modern Interface**: Built with CustomTkinter for a sleek, dark-themed experience.

## Installation & Launch
The easiest way to run Burst Shot Cleaner is through the provided launch script:

```bash
chmod +x launch.sh
./launch.sh
```

This script will automatically create a virtual environment, install the necessary dependencies (`customtkinter`, `pillow`, `pandas`), and launch the application.

## Usage
1.  Select the target directories to scan (defaults to `$HOME/Pictures` and `/run/media/$USER/DATA/Billeder`).
2.  Adjust the burst threshold if necessary (default 2 seconds).
3.  Click **Scan** to find burst sequences.
4.  Review the detected groups.
5.  Click **Run Cleanup** (or ensure 'Dry Run' is checked first to preview).
