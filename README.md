# Microbit Manager for Linux

A Terminal User Interface (TUI) for managing microbit .hex files. This tool automatically detects when your microbit is connected, mounts it, and provides an easy interface to browse and copy .hex files from your Downloads folder.

## Features

- **Automatic Detection**: Detects when microbit is plugged in or unplugged
- **Auto-mounting**: Automatically mounts the microbit when connected
- **File Browser**: Lists all .hex files in your Downloads folder with size and modification date
- **Easy Copying**: Navigate and copy .hex files to your microbit with simple keystrokes
- **Device Info**: View microbit device information
- **Safe Unmounting**: Properly unmounts the device when done
- **Comprehensive Error Handling**: Detailed error messages for common issues
- **File Validation**: Validates .hex files before copying
- **Space Checking**: Verifies available space before copying

## Files

- `microbit_manager.py` - Main Python TUI application
- `run_microbit_manager.sh` - Convenient shell wrapper script
- `README.md` - This file

## Requirements

- Python 3 with curses support (included in most Linux distributions)
- sudo privileges (required for mounting/unmounting devices)
- microbit with data-capable USB cable

### Microbit Compatibility

**Tested with**: microbit v1.3B  
**Expected to work with**: All microbit versions (v1.0, v1.3, v1.5, v2.0, v2.2)

This tool has been developed and tested with a microbit v1.3B, but should work with all microbit versions as it uses standard USB device detection and mounting. If you encounter issues with other versions, please report them in the GitHub issues.

## Installation

1. Clone this repository:
```bash
git clone https://github.com/Thalmann/microbit-manager-linux.git
cd microbit-manager-linux
```

2. Make the runner script executable:
```bash
chmod +x run_microbit_manager.sh
```

## Usage

### Quick Start
```bash
cd microbit-manager-linux
./run_microbit_manager.sh
```

### Direct Python Execution
```bash
cd microbit-manager-linux
sudo python3 microbit_manager.py
```

## Controls

| Key | Action |
|-----|--------|
| ↑/↓ or j/k | Navigate through .hex files |
| ENTER | Copy selected file to microbit |
| m | Mount/Unmount microbit manually |
| r | Refresh file list |
| i | Show microbit device information |
| q | Quit the application |

## How It Works

1. **Detection**: The app continuously monitors for microbit USB connections (VendorID: 0d28, ProductID: 0204)
2. **Mounting**: When a microbit is detected, it's automatically mounted to `/mnt/microbit`
3. **File Listing**: Scans your Downloads folder for .hex files and displays them sorted by modification date
4. **Copying**: When you select a file and press ENTER, it copies the .hex file to the microbit
5. **Auto-restart**: The microbit automatically restarts and runs your program after copying

## Troubleshooting

### Microbit Not Detected
- Ensure you're using a data-capable USB cable (not just power-only)
- Try a different USB port
- Check if the microbit LED is showing activity when plugged in

### Permission Issues
- The script requires sudo privileges to mount/unmount devices
- Make sure to run with `sudo` or use the provided shell wrapper

### No .hex Files Shown
- Make sure your .hex files are in the Downloads folder (`~/Downloads/`)
- Press 'r' to refresh the file list

### Mounting Issues
- If auto-mounting fails, try pressing 'm' to manually mount/unmount
- Check that `/mnt/microbit` directory exists and is accessible

### Copy Errors
The script provides detailed error messages for copy failures:
- **"No space left on microbit"**: The microbit is full - remove old files first
- **"Invalid HEX file"**: The file is not a valid Intel HEX format
- **"I/O error"**: Microbit may have been disconnected during copy
- **"Permission denied"**: Run the script with sudo privileges
- **"Copy incomplete"**: File didn't copy fully - try again

### Connection Issues
- **"Device is busy"**: Close any file managers or programs accessing the microbit
- **"Mount point no longer exists"**: Microbit was disconnected - replug it
- **"Unsupported filesystem"**: Microbit may need to be reset or reflashed

## Technical Details

- **Mount Point**: `/mnt/microbit`
- **Microbit Device IDs**: Vendor ID 0d28, Product ID 0204
- **File Location**: Scans `~/Downloads/` for .hex files
- **Auto-refresh**: Checks connection status every second

## Example Workflow

1. Plug in your microbit with a data cable
2. Run `./run_microbit_manager.sh`
3. The interface shows "USB: CONNECTED | Mount: MOUNTED"
4. Navigate to your desired .hex file with arrow keys
5. Press ENTER to copy the file to microbit
6. The microbit will automatically restart and run your program
7. Press 'q' to quit when done

The microbit will be safely unmounted when you exit the application.