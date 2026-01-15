import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from browser import WebBrowser

if __name__ == "__main__":
    # Setup logging for debugging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Set environment variables for Widevine and proprietary codecs
    widevine_path = r"C:\Program Files\Google\Chrome\Application\139.0.7258.155\WidevineCdm\_platform_specific\win_x64\widevinecdm.dll"
    flags = f'--enable-proprietary-codecs --enable-widevine --widevine-path="{widevine_path}"'
    
    if os.path.exists(widevine_path):
        logger.debug(f"Widevine CDM found at {widevine_path}")
    else:
        logger.error(f"Widevine CDM not found at {widevine_path}")
    
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = flags
    logger.debug(f"QTWEBENGINE_CHROMIUM_FLAGS set to: {flags}")
    
    app = QApplication(sys.argv)
    window = WebBrowser()
    window.show()
    sys.exit(app.exec())