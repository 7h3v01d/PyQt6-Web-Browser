# Repeater Plugin

## Overview
The `repeater_plugin.py` allows users to capture and replay HTTP requests made by the PyQt6 web browser for debugging or testing purposes. It integrates with `QWebEngineView`’s network interception capabilities (via `interceptors.py`) to log requests and resend them with customizable headers, methods, or payloads.

### Features
- **Request Capture**: Log HTTP requests (GET, POST, etc.) from the current webpage.
- **Request Replay**: Resend captured requests with modified parameters (e.g., headers, URL, data).
- **Logging**: Display request/response details in a dialog.
- **Integration**: Accessible via `Plugins > repeater_plugin > Request Repeater`.
- **Anonymity**: Supports Tor for anonymous request replays when enabled.

## Dependencies
- **Python**: 3.11.5
- **PyQt6**: 6.7.0
- **PyQt6-WebEngine**: 6.7.0
- **requests**: For sending replayed requests
- **cryptography**: For vault integration (optional, if credentials are needed)

Install dependencies:
```bash
E:\Projects\venv_importmapper\Scripts\activate
pip install PyQt6==6.7.0 PyQt6-WebEngine==6.7.0 requests cryptography
```

## Setup
1. **Save the Plugin**:
   - Place `repeater_plugin.py` in `E:\Projects\_webbrowser\src\plugins`.
   - Ensure other files (`browser.py`, `interceptors.py`, etc.) are unchanged.

2. **Configure Interceptors**:
   - Ensure `interceptors.py` supports request logging (e.g., via `ChainedInterceptor`).
   - No credentials are typically required, but if the plugin needs API keys, store them in `credentials.vault` via `vault.py`.

3. **Clear Cached Bytecode**:
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
   - Navigate to `Plugins > repeater_plugin > Request Repeater`.

2. **Capture Requests**:
   - Browse a webpage (e.g., `https://duckduckgo.com`).
   - The plugin logs HTTP requests (e.g., GET/POST) in the dialog’s request list.
   - View details like URL, method, headers, and payload.

3. **Replay Requests**:
   - Select a logged request.
   - Modify parameters (e.g., add headers, change POST data).
   - Click “Replay” to resend the request.
   - View the response in the dialog (status code, headers, body).

4. **Anonymity**:
   - Enable Anonymous mode (`Anonymous: On`) and Tor proxy (`Settings > Enable Tor Proxy`).
   - Replayed requests route through Tor (`127.0.0.1:9050`).
   - Verify “Tor proxy enabled” in the status bar.

## Troubleshooting
- **Plugin Fails to Load**:
  - Check console for errors (e.g., `Failed to import PyQt6 modules`).
  - Reinstall dependencies:
    ```bash
    pip install --upgrade PyQt6 PyQt6-WebEngine requests cryptography
    ```
- **Requests Not Captured**:
  - Verify `interceptors.py` is correctly configured for request logging.
  - Ensure the webpage is loaded in the active tab.
- **Replay Fails**:
  - Test connectivity:
    ```bash
    curl --proxy socks5h://127.0.0.1:9050 https://example.com
    ```
  - Check if the target server requires authentication (store credentials in `credentials.vault`).
- **General Issues**:
  - Share console output and request logs for debugging.

## Notes
- **Legal Use**: Replaying requests may violate service terms (e.g., sending unauthorized requests). Use for legitimate debugging only.
- **Security**: Avoid logging sensitive data (e.g., authentication tokens) in plaintext.
- **Performance**: Tor may slow replays; disable it if not needed.
- **Testing**: Use on public, non-sensitive endpoints to avoid unintended consequences.