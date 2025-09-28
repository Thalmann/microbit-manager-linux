#!/usr/bin/env python3
"""
Microbit Manager - A TUI for managing microbit .hex files
Detects microbit USB connection, mounts/unmounts automatically, and provides
an interface to browse and copy .hex files from Downloads folder.
"""

import os
import sys
import subprocess
import time
import glob
from pathlib import Path
from datetime import datetime
import curses
import json


class MicrobitManager:
    def __init__(self):
        self.microbit_vendor_id = "0d28"
        self.microbit_product_id = "0204"
        self.mount_point = "/mnt/microbit"
        
        # Handle Downloads directory when running with sudo
        if os.environ.get('SUDO_USER'):
            # Running with sudo, use the original user's home directory
            original_user = os.environ['SUDO_USER']
            self.downloads_dir = Path(f"/home/{original_user}/Downloads")
        else:
            self.downloads_dir = Path.home() / "Downloads"
        
        self.is_mounted = False
        self.microbit_device = None
        self.status_message = ""
        self.selected_file_idx = 0
        self.manual_unmount = False  # Flag to prevent auto-mounting after manual unmount
        self.show_info_area = False  # Flag to show/hide firmware info area
        
    def run_command(self, command, check=True, capture_output=True):
        """Run a shell command and return the result."""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=capture_output, 
                text=True, 
                check=check
            )
            return result.stdout.strip() if capture_output else ""
        except subprocess.CalledProcessError as e:
            if capture_output:
                return ""
            return None
    
    def run_command_with_error(self, command):
        """Run a command and return success status and error message."""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                check=True
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else f"Command failed with exit code {e.returncode}"
            return False, error_msg

    def detect_microbit(self):
        """Detect if microbit is connected via USB."""
        lsusb_output = self.run_command("lsusb")
        for line in lsusb_output.split('\n'):
            if self.microbit_vendor_id in line and self.microbit_product_id in line:
                # Extract device path
                parts = line.split()
                if len(parts) >= 4:
                    bus = parts[1]
                    device = parts[3].rstrip(':')
                    return True, f"Bus {bus} Device {device}"
        return False, None

    def get_microbit_block_device(self):
        """Find the block device for the microbit."""
        # Check for removable devices
        lsblk_output = self.run_command("lsblk -J")
        try:
            data = json.loads(lsblk_output)
            for device in data.get('blockdevices', []):
                if device.get('rm', False):  # Removable device
                    size = device.get('size', '')
                    if '8.1M' in size or '8M' in size:  # Typical microbit size
                        return f"/dev/{device['name']}"
        except json.JSONDecodeError:
            pass
        
        # Fallback: check common device names
        for device in ['/dev/sda', '/dev/sdb', '/dev/sdc']:
            if os.path.exists(device):
                size_output = self.run_command(f"lsblk -b {device} | tail -1")
                if size_output and '8' in size_output:  # Rough size check
                    return device
        return None

    def is_microbit_mounted(self):
        """Check if microbit is currently mounted."""
        mount_output = self.run_command("mount")
        return self.mount_point in mount_output

    def mount_microbit(self):
        """Mount the microbit with comprehensive error handling."""
        device = self.get_microbit_block_device()
        if not device:
            return False, "No microbit block device found"
        
        # Check if already mounted
        if self.is_microbit_mounted():
            self.is_mounted = True
            self.microbit_device = device
            return True, f"Already mounted {device} to {self.mount_point}"
        
        # Create mount point if it doesn't exist
        success, result = self.run_command_with_error(f"sudo mkdir -p {self.mount_point}")
        if not success:
            return False, f"Failed to create mount point: {result}"
        
        # Mount the device
        success, result = self.run_command_with_error(f"sudo mount {device} {self.mount_point}")
        if success:
            self.is_mounted = True
            self.microbit_device = device
            return True, f"Mounted {device} to {self.mount_point}"
        else:
            # Parse common mount errors
            error_lower = result.lower()
            if "already mounted" in error_lower:
                self.is_mounted = True
                self.microbit_device = device
                return True, f"Already mounted {device}"
            elif "permission denied" in error_lower:
                return False, "Permission denied - run with sudo"
            elif "no such file or directory" in error_lower:
                return False, f"Device {device} not found - microbit may have been disconnected"
            elif "wrong fs type" in error_lower or "invalid argument" in error_lower:
                return False, f"Cannot mount {device} - unsupported filesystem or corrupted device"
            else:
                return False, f"Mount failed: {result}"

    def unmount_microbit(self):
        """Unmount the microbit with comprehensive error handling."""
        if not self.is_mounted and not self.is_microbit_mounted():
            return True, "Microbit not mounted"
        
        success, result = self.run_command_with_error(f"sudo umount {self.mount_point}")
        if success:
            self.is_mounted = False
            self.microbit_device = None
            return True, "Microbit unmounted successfully"
        else:
            # Parse common unmount errors
            error_lower = result.lower()
            if "not mounted" in error_lower:
                self.is_mounted = False
                self.microbit_device = None
                return True, "Microbit was not mounted"
            elif "device is busy" in error_lower or "target is busy" in error_lower:
                return False, "Cannot unmount - device is busy (close any files or programs using it)"
            elif "permission denied" in error_lower:
                return False, "Permission denied - run with sudo"
            elif "no such file or directory" in error_lower:
                # Mount point doesn't exist, consider it unmounted
                self.is_mounted = False
                self.microbit_device = None
                return True, "Mount point not found - considering unmounted"
            else:
                return False, f"Unmount failed: {result}"

    def get_hex_files(self):
        """Get list of .hex files in Downloads directory."""
        hex_files = []
        if self.downloads_dir.exists():
            for hex_file in self.downloads_dir.glob("*.hex"):
                stat = hex_file.stat()
                hex_files.append({
                    'name': hex_file.name,
                    'path': str(hex_file),
                    'size': stat.st_size,
                    'mtime': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                })
        return sorted(hex_files, key=lambda x: x['mtime'], reverse=True)
    
    def validate_hex_file(self, hex_file_path):
        """Validate that a file appears to be a valid Intel HEX file."""
        try:
            with open(hex_file_path, 'r') as f:
                lines = f.readlines(100)  # Check first 100 lines
                
                if not lines:
                    return False, "File is empty"
                
                # Check if it looks like an Intel HEX file
                hex_line_count = 0
                for line in lines[:10]:  # Check first 10 lines
                    line = line.strip()
                    if line.startswith(':') and len(line) >= 11:
                        # Basic Intel HEX format check
                        try:
                            # Try to parse the hex data after the colon
                            hex_data = line[1:]
                            int(hex_data, 16)  # This will fail if not valid hex
                            hex_line_count += 1
                        except ValueError:
                            continue
                
                if hex_line_count == 0:
                    return False, "File does not appear to be in Intel HEX format"
                
                return True, "Valid HEX file"
                
        except Exception as e:
            return False, f"Cannot validate file: {str(e)}"

    def copy_hex_file(self, hex_file_path):
        """Copy a hex file to the microbit with comprehensive error handling."""
        if not self.is_mounted:
            return False, "Microbit not mounted"
        
        # Check if source file exists and is readable
        if not os.path.exists(hex_file_path):
            return False, f"Source file not found: {hex_file_path}"
        
        if not os.path.isfile(hex_file_path):
            return False, f"Source is not a file: {hex_file_path}"
        
        # Validate that it's a proper HEX file
        is_valid, validation_msg = self.validate_hex_file(hex_file_path)
        if not is_valid:
            return False, f"Invalid HEX file: {validation_msg}"
        
        try:
            with open(hex_file_path, 'r') as f:
                # Try to read a small portion to verify it's accessible
                f.read(100)
        except PermissionError:
            return False, f"Permission denied reading source file"
        except Exception as e:
            return False, f"Cannot read source file: {str(e)}"
        
        filename = os.path.basename(hex_file_path)
        dest_path = f"{self.mount_point}/{filename}"
        
        # Check if mount point is still accessible
        if not os.path.exists(self.mount_point):
            return False, "Mount point no longer exists - microbit may have been disconnected"
        
        # Check available space on microbit (rough check)
        try:
            statvfs = os.statvfs(self.mount_point)
            free_bytes = statvfs.f_frsize * statvfs.f_bavail
            file_size = os.path.getsize(hex_file_path)
            
            if free_bytes < file_size:
                return False, f"Not enough space on microbit ({free_bytes} bytes free, need {file_size})"
        except Exception:
            # If we can't check space, continue anyway
            pass
        
        # Perform the copy with detailed error reporting
        success, result = self.run_command_with_error(f"sudo cp '{hex_file_path}' '{dest_path}'")
        
        if success:
            # Verify the file was actually copied
            if os.path.exists(dest_path):
                try:
                    # Check if copied file has reasonable size
                    copied_size = os.path.getsize(dest_path)
                    original_size = os.path.getsize(hex_file_path)
                    
                    if copied_size != original_size:
                        return False, f"Copy incomplete: {copied_size}/{original_size} bytes"
                    
                    return True, f"Successfully copied {filename} ({copied_size:,} bytes)"
                except Exception as e:
                    return True, f"Copied {filename} (verification failed: {str(e)})"
            else:
                return False, f"Copy appeared successful but file not found on microbit"
        else:
            # Parse common error messages to provide helpful feedback
            error_lower = result.lower()
            if "no space left" in error_lower:
                return False, "No space left on microbit"
            elif "permission denied" in error_lower:
                return False, "Permission denied - microbit may be read-only or disconnected"
            elif "no such file" in error_lower:
                return False, "Microbit disconnected during copy"
            elif "input/output error" in error_lower:
                return False, "I/O error - microbit may have been disconnected"
            else:
                return False, f"Copy failed: {result}"

    def get_microbit_files(self):
        """Get list of files on the mounted microbit."""
        if not self.is_mounted or not os.path.exists(self.mount_point):
            return None
        
        try:
            files = []
            for item in os.listdir(self.mount_point):
                item_path = os.path.join(self.mount_point, item)
                if os.path.isfile(item_path):
                    try:
                        stat = os.stat(item_path)
                        files.append({
                            'name': item,
                            'size': stat.st_size,
                            'mtime': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                        })
                    except Exception:
                        # If we can't get stats, still show the file
                        files.append({
                            'name': item,
                            'size': 0,
                            'mtime': 'unknown'
                        })
            return sorted(files, key=lambda x: x['name'])
        except Exception:
            return None

    def get_microbit_info(self):
        """Get microbit information if mounted."""
        if not self.is_mounted:
            return None
        
        details_path = f"{self.mount_point}/DETAILS.TXT"
        if os.path.exists(details_path):
            try:
                with open(details_path, 'r') as f:
                    return f.read()
            except Exception:
                pass
        return None

    def get_firmware_version(self):
        """Extract firmware version from DETAILS.TXT file."""
        info = self.get_microbit_info()
        if not info:
            return None
        
        # Parse DETAILS.TXT to find Interface Version
        # Format: "Interface Version: 0255"
        lines = info.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('Interface Version:'):
                parts = line.split(':', 1)
                if len(parts) > 1:
                    version = parts[1].strip()
                    return version
        
        return None

    def get_microbit_details(self):
        """Extract key details from DETAILS.TXT for display."""
        info = self.get_microbit_info()
        if not info:
            return {}
        
        details = {}
        lines = info.split('\n')
        
        # Extract key fields that are commonly present
        for line in lines:
            line = line.strip()
            if ':' in line and not line.startswith('#'):
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Store commonly useful fields
                if key in ['Interface Version', 'Bootloader Version', 'Unique ID', 
                          'HIC ID', 'Daplink Mode', 'USB Interfaces', 'URL']:
                    details[key] = value
        
        return details

    def draw_header(self, stdscr):
        """Draw the header of the TUI."""
        height, width = stdscr.getmaxyx()
        title = "=== MICROBIT MANAGER ==="
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        
        # Status line with color coding
        connected, device_info = self.detect_microbit()
        
        # Determine color based on connection and mount status
        if not connected or not self.is_mounted:
            color_attr = curses.color_pair(1) | curses.A_BOLD  # Red
        else:
            color_attr = curses.color_pair(2) | curses.A_BOLD  # Green
        
        status = "CONNECTED" if connected else "DISCONNECTED"
        mount_status = "MOUNTED" if self.is_mounted else "NOT MOUNTED"
        
        status_line = f"USB: {status} | Mount: {mount_status}"
        if device_info:
            status_line += f" | {device_info}"
        
        # Add firmware version if available
        if self.is_mounted:
            firmware_version = self.get_firmware_version()
            if firmware_version:
                status_line += f" | FW: {firmware_version}"
        
        stdscr.addstr(1, 0, status_line[:width-1], color_attr)
        
        if self.status_message:
            stdscr.addstr(2, 0, f"Status: {self.status_message}"[:width-1], curses.A_REVERSE)
            
        return 3 if self.status_message else 2

    def draw_controls(self, stdscr, start_y):
        """Draw control instructions."""
        height, width = stdscr.getmaxyx()
        controls = [
            "Controls:",
            "↑/↓ or j/k - Navigate files",
            "ENTER - Copy selected file to microbit",
            "m - Mount/Unmount microbit",
            "r - Refresh file list",
            "i - Toggle firmware info area",
            "q - Quit"
        ]
        
        for i, control in enumerate(controls):
            if start_y + i < height - 1:
                attr = curses.A_BOLD if i == 0 else curses.A_NORMAL
                stdscr.addstr(start_y + i, 0, control[:width-1], attr)
        
        return start_y + len(controls)

    def draw_file_list(self, stdscr, start_y, hex_files):
        """Draw the list of hex files."""
        height, width = stdscr.getmaxyx()
        
        if not hex_files:
            stdscr.addstr(start_y, 0, "No .hex files found in Downloads folder", curses.A_DIM)
            return start_y + 2
        
        stdscr.addstr(start_y, 0, f"Hex files in {self.downloads_dir}:", curses.A_BOLD)
        start_y += 1
        
        # Header
        header = f"{'Name':<30} {'Size':<10} {'Modified':<16}"
        stdscr.addstr(start_y, 0, header[:width-1], curses.A_UNDERLINE)
        start_y += 1
        
        # File list
        for i, file_info in enumerate(hex_files):
            if start_y + i >= height - 1:
                break
                
            name = file_info['name'][:28]
            size = f"{file_info['size']:,}B"
            mtime = file_info['mtime']
            
            line = f"{name:<30} {size:<10} {mtime:<16}"
            
            attr = curses.A_REVERSE if i == self.selected_file_idx else curses.A_NORMAL
            stdscr.addstr(start_y + i, 0, line[:width-1], attr)
        
        return start_y + len(hex_files)
    
    def draw_microbit_files(self, stdscr, start_y):
        """Draw the list of files on the microbit."""
        height, width = stdscr.getmaxyx()
        
        stdscr.addstr(start_y, 0, "Files on microbit:", curses.A_BOLD)
        start_y += 1
        
        microbit_files = self.get_microbit_files()
        
        if microbit_files is None:
            stdscr.addstr(start_y, 0, "Not mounted", curses.color_pair(1) | curses.A_BOLD)  # Red
            return start_y + 2
        
        if not microbit_files:
            stdscr.addstr(start_y, 0, "No files found on microbit", curses.A_DIM)
            return start_y + 2
        
        # Header
        header = f"{'Name':<30} {'Size':<10} {'Modified':<16}"
        stdscr.addstr(start_y, 0, header[:width-1], curses.A_UNDERLINE)
        start_y += 1
        
        # File list (limit to prevent screen overflow)
        max_files = min(len(microbit_files), (height - start_y - 3))
        for i in range(max_files):
            if start_y + i >= height - 1:
                break
                
            file_info = microbit_files[i]
            name = file_info['name'][:28]
            size = f"{file_info['size']:,}B" if file_info['size'] > 0 else "unknown"
            mtime = file_info['mtime']
            
            line = f"{name:<30} {size:<10} {mtime:<16}"
            stdscr.addstr(start_y + i, 0, line[:width-1], curses.A_NORMAL)
        
        return start_y + max_files

    def draw_info_area(self, stdscr, start_y):
        """Draw the firmware info area at the bottom."""
        height, width = stdscr.getmaxyx()
        
        if not self.show_info_area or not self.is_mounted:
            return start_y
        
        details = self.get_microbit_details()
        if not details:
            stdscr.addstr(start_y, 0, "--- FIRMWARE INFO ---", curses.A_BOLD)
            stdscr.addstr(start_y + 1, 0, "Could not read microbit info", curses.color_pair(1))
            return start_y + 2
        
        # Draw separator
        stdscr.addstr(start_y, 0, "--- FIRMWARE INFO ---", curses.A_BOLD)
        y = start_y + 1
        
        # Display key firmware information in a compact format
        info_lines = []
        for key, value in details.items():
            if key in ['Interface Version', 'Bootloader Version', 'Daplink Mode']:
                info_lines.append(f"{key}: {value}")
        
        # Add additional useful info
        if 'Unique ID' in details:
            # Show first part of unique ID (board info)
            unique_id = details['Unique ID']
            if len(unique_id) >= 4:
                board_id = unique_id[:4]
                board_type = {
                    '9900': 'v1.3',
                    '9901': 'v1.5', 
                    '9903': 'v2.0',
                    '9904': 'v2.0'
                }.get(board_id, f'Unknown ({board_id})')
                info_lines.append(f"Board: {board_type}")
        
        if 'USB Interfaces' in details:
            info_lines.append(f"USB: {details['USB Interfaces']}")
        
        # Display info lines, wrapping if necessary
        for line in info_lines:
            if y < height - 1:
                stdscr.addstr(y, 0, line[:width-1], curses.A_NORMAL)
                y += 1
            else:
                break
        
        return y

    def main_loop(self, stdscr):
        """Main TUI loop."""
        curses.curs_set(0)  # Hide cursor
        stdscr.timeout(1000)  # 1 second timeout for getch()
        
        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)  # Red text
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Green text
        
        while True:
            stdscr.clear()
            height, width = stdscr.getmaxyx()
            
            # Draw header
            y_pos = self.draw_header(stdscr)
            y_pos += 1
            
            # Check microbit status
            connected, _ = self.detect_microbit()
            if connected and not self.is_mounted and not self.manual_unmount:
                # Auto-mount if connected but not mounted (unless manually unmounted)
                success, msg = self.mount_microbit()
                if success:
                    self.status_message = msg
            elif not connected and self.is_mounted:
                # Auto-unmount if disconnected and reset manual unmount flag
                self.unmount_microbit()
                self.manual_unmount = False  # Reset flag when disconnected
                self.status_message = "Microbit disconnected and unmounted"
            elif not connected:
                # Reset manual unmount flag when disconnected
                self.manual_unmount = False
            
            # Get hex files
            hex_files = self.get_hex_files()
            
            # Adjust selected index if necessary
            if hex_files:
                self.selected_file_idx = min(self.selected_file_idx, len(hex_files) - 1)
            else:
                self.selected_file_idx = 0
            
            # Draw file list
            y_pos = self.draw_file_list(stdscr, y_pos, hex_files)
            y_pos += 1
            
            # Draw microbit files
            y_pos = self.draw_microbit_files(stdscr, y_pos)
            y_pos += 1
            
            # Draw firmware info area if enabled
            y_pos = self.draw_info_area(stdscr, y_pos)
            if self.show_info_area:
                y_pos += 1
            
            # Draw controls
            self.draw_controls(stdscr, y_pos)
            
            stdscr.refresh()
            
            # Handle input
            key = stdscr.getch()
            
            if key == ord('q'):
                break
            elif key == curses.KEY_UP or key == ord('k'):
                if hex_files and self.selected_file_idx > 0:
                    self.selected_file_idx -= 1
            elif key == curses.KEY_DOWN or key == ord('j'):
                if hex_files and self.selected_file_idx < len(hex_files) - 1:
                    self.selected_file_idx += 1
            elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:
                if hex_files and self.is_mounted:
                    selected_file = hex_files[self.selected_file_idx]
                    success, msg = self.copy_hex_file(selected_file['path'])
                    self.status_message = msg
                elif not self.is_mounted:
                    self.status_message = "Microbit not mounted - press 'm' to mount"
                else:
                    self.status_message = "No hex files to copy"
            elif key == ord('m'):
                if self.is_mounted:
                    success, msg = self.unmount_microbit()
                    if success:
                        self.manual_unmount = True  # Set flag to prevent auto-mounting
                else:
                    success, msg = self.mount_microbit()
                    if success:
                        self.manual_unmount = False  # Clear flag when manually mounting
                self.status_message = msg
            elif key == ord('r'):
                self.status_message = "File list refreshed"
            elif key == ord('i'):
                if self.is_mounted:
                    self.show_info_area = not self.show_info_area  # Toggle info area
                    self.status_message = f"Firmware info {'shown' if self.show_info_area else 'hidden'}"
                else:
                    self.status_message = "Microbit not mounted"
            
            # Clear status message after a while
            if self.status_message:
                time.sleep(0.1)  # Brief pause to show message

    def run(self):
        """Run the TUI application."""
        try:
            curses.wrapper(self.main_loop)
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            # Clean up: unmount if mounted
            if self.is_mounted:
                self.unmount_microbit()


def main():
    if os.geteuid() != 0:
        print("This script needs sudo privileges to mount/unmount devices.")
        print("Please run with: sudo python3 microbit_manager.py")
        sys.exit(1)
    
    manager = MicrobitManager()
    manager.run()


if __name__ == "__main__":
    main()