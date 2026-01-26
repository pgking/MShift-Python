import os
import sys
import json
import urllib.request
import zipfile
import tempfile
import subprocess
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from PyQt5.QtCore import QThread, pyqtSignal, Qt

OWNER = "pgking"
REPO = "MShift-Python"

def parse_version(v_str):
    """
    Converts a version string into a list of integers for comparison.
    Example: 'v1.2.3' -> [1, 2, 3]
    """
    v_str = v_str.lower().strip().lstrip('v')
    try:
        parts = []
        for x in v_str.split('.'):
            # Extract only digits (handles 1.1b or 1.1-alpha)
            digit_part = "".join(filter(str.isdigit, x))
            if digit_part:
                parts.append(int(digit_part))
            else:
                parts.append(0)
        while len(parts) < 3:
            parts.append(0)
        return parts[:3]
    except:
        return [0, 0, 0]

class CheckUpdateThread(QThread):
    finished = pyqtSignal(dict, str) # latest_version_info dictionary, error_message

    def run(self):
        url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'mshift-updater')
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.getcode() == 200:
                    data = json.load(response)
                    self.finished.emit(data, "")
                else:
                    self.finished.emit({}, f"Server returned code {response.getcode()}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # This usually means no releases have been created yet
                self.finished.emit({}, "no_releases")
            else:
                self.finished.emit({}, f"HTTP Error {e.code}")
        except Exception as e:
            print(f"Update check error: {e}")
            self.finished.emit({}, str(e))

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str) # Path to downloaded zip
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            temp_dir = tempfile.gettempdir()
            target_path = os.path.join(temp_dir, "mshift_update.zip")
            
            # Use build_opener to ensure User-Agent headers for asset download
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-agent', 'mshift-updater')]
            urllib.request.install_opener(opener)

            def report_hook(count, block_size, total_size):
                if total_size > 0:
                    p = int(count * block_size * 100 / total_size)
                    self.progress.emit(min(p, 100))

            urllib.request.urlretrieve(self.url, target_path, reporthook=report_hook)
            self.finished.emit(target_path)
        except Exception as e:
            self.error.emit(str(e))

class UpdateManager:
    """
    Manages the lifecycle of an update: Check -> Notify -> Download -> Install
    """
    def __init__(self, current_version, parent_window):
        self.current_version = current_version
        self.parent = parent_window
        self.check_thread = None
        self.download_thread = None
        self.latest_info = None
        self.silent = True

    def start_check(self, silent=True):
        """Checks for updates. Set silent=False for manual menu-triggered checks."""
        # Only check for updates if running as a built executable
        if not getattr(sys, 'frozen', False):
            if not silent:
                 QMessageBox.information(self.parent, "Update", "Application update is only available in the built version (.exe).")
            return

        self.silent = silent
        self.check_thread = CheckUpdateThread()
        self.check_thread.finished.connect(self._on_check_finished)
        self.check_thread.start()

    def _on_check_finished(self, data, error_msg):
        if not data:
            if error_msg == "no_releases":
                if not self.silent:
                    QMessageBox.information(self.parent, "Update", "No releases found on GitHub yet. Make sure you have created at least one release.")
                return
            
            if not self.silent:
                QMessageBox.warning(self.parent, "Update", f"Could not check for updates.\n\nError: {error_msg if error_msg else 'Unknown'}\n\nPlease check your internet connection or repository settings.")
            return

        latest_tag = data.get("tag_name", "0.0.0")
        self.latest_info = data

        if parse_version(latest_tag) > parse_version(self.current_version):
            msg = f"A new version is available: {latest_tag} (Current: {self.current_version})\n\n"
            msg += f"Changes:\n{data.get('body', 'No release notes provided.')}\n\n"
            msg += "Would you like to download and install it now?"
            
            res = QMessageBox.question(self.parent, "Update Available", msg, QMessageBox.Yes | QMessageBox.No)
            if res == QMessageBox.Yes:
                self._start_download()
        else:
            if not self.silent:
                QMessageBox.information(self.parent, "Update", f"You are up to date! (Version {self.current_version})")

    def _start_download(self):
        assets = self.latest_info.get("assets", [])
        zip_url = None
        
        # Look for a .zip file in the release assets
        for asset in assets:
            if asset.get("name", "").lower().endswith(".zip"):
                zip_url = asset.get("browser_download_url")
                break
        
        if not zip_url:
            QMessageBox.critical(self.parent, "Update Error", "No update file (ZIP) found in the latest release. Please contact support.")
            return

        self.progress_dialog = QProgressDialog("Downloading update...", None, 0, 100, self.parent)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setCancelButton(None) 
        self.progress_dialog.show()

        self.download_thread = DownloadThread(zip_url)
        self.download_thread.progress.connect(self.progress_dialog.setValue)
        self.download_thread.finished.connect(self._on_download_finished)
        self.download_thread.error.connect(self._on_download_error)
        self.download_thread.start()

    def _on_download_error(self, err):
        self.progress_dialog.close()
        QMessageBox.critical(self.parent, "Download Error", f"An error occurred during download:\n{err}")

    def _on_download_finished(self, zip_path):
        self.progress_dialog.close()
        install_dir = os.path.dirname(sys.executable)

        try:
            # Create a unique temp folder for extraction
            temp_extract = tempfile.mkdtemp()
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract)
            
            # Find the source folder (handles zips containing a folder vs zips containing files directly)
            source_dir = temp_extract
            contents = os.listdir(temp_extract)
            if len(contents) == 1 and os.path.isdir(os.path.join(temp_extract, contents[0])):
                source_dir = os.path.join(temp_extract, contents[0])

            self._apply_update(source_dir, install_dir)
        except Exception as e:
            QMessageBox.critical(self.parent, "Install Error", f"Failed to prepare update files:\n{e}")

    def _apply_update(self, source_dir, install_dir):
        """
        Creates a batch script that waits for mshift to exit, copies files, and restarts.
        """
        bat_path = os.path.join(tempfile.gettempdir(), "mshift_update_apply.bat")
        exe_path = sys.executable
        
        bat_content = f"""@echo off
title mshift Updater
echo.
echo ========================================
echo  mshift is updating to the latest version
echo ========================================
echo.
echo Waiting for application to close...
timeout /t 2 /nobreak > nul
echo Updating files...
xcopy /s /y /e "{source_dir}\\*" "{install_dir}\\"
echo Cleaning up...
rd /s /q "{os.path.dirname(source_dir)}"
echo Restarting mshift...
start "" "{exe_path}"
del "%~f0"
"""
        with open(bat_path, "w") as f:
            f.write(bat_content)

        QMessageBox.information(
            self.parent, 
            "Update Ready", 
            "The update has been downloaded and is ready to be installed.\n\n"
            "The application will now restart to apply changes."
        )

        # Launch the batch script detached
        subprocess.Popen(bat_path, shell=True)
        # Exit the application so the batch script can overwrite files
        sys.exit(0)
