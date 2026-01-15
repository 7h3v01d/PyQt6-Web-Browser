# Netflix Downloader Plugin

## Overview
The `netflix_downloader_plugin.py` integrates Netflix video downloading into the PyQt6 web browser, allowing users to download movies or series for offline viewing. It uses `yt_dlp` to handle Netflix’s DRM-protected content (via Widevine) and supports video quality selection, subtitle language options, and secure credential storage through `vault.py`.

### Features
- **Video Download**: Download Netflix videos (single episodes, movies, or playlists) to `E:\Projects\_webbrowser\src\downloads`.
- **Quality Selection**: Choose resolutions (e.g., 720p, 1080p, 4K) or best available.
- **Subtitles**: Download subtitles in multiple languages (e.g., English, Spanish).
- **Credential Management**: Store Netflix email/password or authentication key in `credentials.vault` using `vault.py`.
- **Progress Tracking**: Display download progress via a progress bar.
- **Integration**: Accessible via `Plugins > netflix_downloader_plugin > Netflix Downloader`.

## Dependencies
- **Python**: 3.11.5
- **PyQt6**: 6.7.0
- **PyQt6-WebEngine**: 6.7.0
- **yt_dlp**: For downloading Netflix content
- **requests**: For API authentication
- **cryptography**: For vault encryption (via `vault.py`)

Install dependencies:
```bash
E:\Projects\venv_importmapper\Scripts\activate
pip install PyQt6==6.7.0 PyQt6-WebEngine==6.7.0 yt_dlp requests cryptography
```

## Setup
1. **Save the Plugin**:
   - Place `netflix_downloader_plugin.py` in `E:\Projects\_webbrowser\src\plugins`.
   - Ensure other files (`browser.py`, `vault.py`, `interceptors.py`, etc.) are unchanged.

2. **Obtain Netflix Credentials**:
   - Use your Netflix account email and password, or an authentication key (see [CastagnaIT/plugin.video.netflix Wiki](https://github.com/CastagnaIT/plugin.video.netflix/wiki) for generating an authentication key).[](https://github.com/CastagnaIT/plugin.video.netflix/wiki/Login-with-Authentication-key)
   - Example authentication key: Generated via `NFAuthenticationKey.py` script.

3. **Add Credentials**:
   - **Option 1: Via Plugin Prompt** (Recommended):
     - Run the browser:
       ```bash
       cd /d E:\Projects\_webbrowser\src
       python main.py
       ```
     - Open `Plugins > netflix_downloader_plugin > Netflix Downloader`.
     - Enter the master password for `credentials.vault` (set during browser initialization).
     - When prompted, enter your Netflix email/password or authentication key. These are saved to `credentials.vault` under `logins` or `api_keys`.
   - **Option 2: Reset Vault**:
     - Delete `credentials.vault` (backup first):
       ```bash
       del E:\Projects\_webbrowser\src\credentials.vault
       ```
     - Run the browser to create a new vault with a master password.
     - Use the plugin to enter credentials.
   - **Note**: Due to Netflix’s DRM (Widevine), you may need to install the Widevine library. See [CastagnaIT/plugin.video.netflix](https://github.com/CastagnaIT/plugin.video.netflix) for instructions.[](https://github.com/asciidisco/plugin.video.netflix/blob/master/README.md)

4. **Clear Cached Bytecode**:
   - Remove cached files:
     ```bash
     rmdir /s /q E:\Projects\_webbrowser\src\__pycache__
     rmdir /s /q E:\Projects\_webbrowser\src\plugins\__pycache__
     ```

## Usage
1. **Open the Plugin**:
   - Start the browser:
     ```bash
     cd /d E:\Projects\_webbrowser\src
     python main.py
     ```
   - Navigate to `Plugins > netflix_downloader_plugin > Netflix Downloader`.

2. **Enter URLs**:
   - In the dialog, enter Netflix video URLs (e.g., `https://www.netflix.com/watch/12345678`) in the text area (one per line for multiple downloads).
   - URLs must be from `www.netflix.com`.

3. **Select Options**:
   - Choose format (e.g., Video MP4, Audio MP3).
   - Select video quality (e.g., 720p, 1080p, 4K, Best Available).
   - Choose subtitle language (e.g., English, Spanish, None).

4. **Download**:
   - Click “Download Video(s)”.
   - Monitor progress via the progress bar.
   - Downloads are saved to `E:\Projects\_webbrowser\src\downloads` as `<title>.mp4` or `<title>.mp3`.

5. **Anonymity**:
   - Enable Anonymous mode (`Anonymous: On`) and Tor proxy (`Settings > Enable Tor Proxy`) for anonymous downloads.
   - Verify “Tor proxy enabled” in the status bar.

## Troubleshooting
- **Plugin Fails to Load**:
  - Check console for errors (e.g., `Failed to import yt_dlp`).
  - Reinstall dependencies:
    ```bash
    pip install --upgrade PyQt6 PyQt6-WebEngine yt_dlp requests cryptography
    ```
- **Download Fails**:
  - Verify Netflix credentials in `credentials.vault`.
  - Test URLs (must start with `https://www.netflix.com/`).
  - Check Widevine installation (see [CastagnaIT/plugin.video.netflix](https://github.com/CastagnaIT/plugin.video.netflix)).[](https://github.com/asciidisco/plugin.video.netflix/blob/master/README.md)
  - If “title is not available in your Netflix region,” try a VPN or update cookies (delete `configs\Cookies\cookies_nf.txt`).[](https://github.com/Kiko023/Netflix-DL)
- **Credential Prompt Reappears**:
  - Verify `credentials.vault` and master password.
  - Check console for `Invalid master password` or `Failed to save API key`.
- **General Issues**:
  - Share console output and `credentials.vault` size (not content) for debugging.

## Notes
- **Legal Use**: Downloading Netflix content may violate Netflix’s terms of service. Use responsibly and only for personal use. Comply with copyright laws and Netflix’s DRM policies.[](https://www.vdocipher.com/blog/2022/05/netflix-drm/)
- **Security**: Keep `credentials.vault` secure. Do not share the master password or Netflix credentials.
- **Performance**: Tor may slow downloads; disable it if anonymity isn’t needed.
- **DRM**: Netflix uses Widevine DRM, requiring specific setup. See plugin documentation for details.[](https://github.com/asciidisco/plugin.video.netflix/blob/master/README.md)