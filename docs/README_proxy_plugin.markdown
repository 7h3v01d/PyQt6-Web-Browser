# Proxy Plugin

## Overview
The `proxy_plugin.py` manages proxy settings for the PyQt6 web browser, enabling HTTP, HTTPS, or Socks5 proxies (including Tor) for anonymous browsing. It integrates with `browser.py`’s `tor_enabled` and `anonymous_mode` settings and stores proxy configurations in `settings.json`.

### Features
- **Proxy Configuration**: Set up HTTP, HTTPS, or Socks5 proxies (e.g., Tor at `127.0.0.1:9050`).
- **Toggle Proxy**: Enable/disable proxies via a dialog.
- **Integration**: Updates `settings.json` with proxy settings (`proxy_enabled`, `proxy_host`, `proxy_port`).
- **Anonymity**: Supports Tor for anonymous browsing, aligning with `browser.py`’s anonymity features.
- **Validation**: Checks proxy connectivity before applying settings.

## Dependencies
- **Python**: 3.11.5
- **PyQt6**: 6.7.0
- **PyQt6-WebEngine**: 6.7.0
- **requests**: For proxy connectivity tests
- **cryptography**: For vault integration (optional, if credentials are stored)

Install dependencies:
```bash
E:\Projects\venv_importmapper\Scripts\activate
pip install PyQt6==6.7.0 PyQt6-WebEngine==6.7.0 requests cryptography
```

## Setup
1. **Save the Plugin**:
   - Place `proxy_plugin.py` in `E:\Projects\_webbrowser\src\plugins`.
   - Ensure other files (`browser.py`, `settings.json`, `interceptors.py`, etc.) are unchanged.

2. **Configure Proxy**:
   - **Option 1: Via Plugin Dialog** (Recommended):
     - Run the browser:
       ```bash
       cd /d E:\Projects\_webbrowser\src
       python main.py
       ```
     - Open `Plugins > proxy_plugin > Proxy Settings`.
     - Enter proxy details (e.g., Host: `127.0.0.1`, Port: `9050`, Type: `Socks5` for Tor).
     - Click “Apply” to save to `settings.json` as:
       ```json
       {
         "homepage": "https://duckduckgo.com/",
         "ad_blocker_enabled": false,
         "tor_enabled": true,
         "autofill_enabled": true,
         "proxy_enabled": true,
         "proxy_host": "127.0.0.1",
         "proxy_port": 9050,
         "proxy_type": "socks5"
       }
       ```
   - **Option 2: Manual `settings.json`**:
     - Open `E:\Projects\_webbrowser\src\settings.json`.
     - Add proxy fields as shown above.
   - **Tor Setup** (Optional):
     - Install Tor (`https://www.torproject.org/download/`).
     - Ensure Tor runs on `127.0.0.1:9050` (`netstat -an | findstr 9050`).

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
   - Navigate to `Plugins > proxy_plugin > Proxy Settings`.

2. **Configure Proxy**:
   - Enter proxy host (e.g., `127.0.0.1` for Tor), port (e.g., `9050`), and type (HTTP, HTTPS, Socks5).
   - Click “Test Connection” to verify proxy (e.g., pings `https://check.torproject.org`).
   - Click “Apply” to enable the proxy and update `settings.json`.

3. **Enable Anonymity**:
   - Set `Anonymous: On` and `Settings > Enable Tor Proxy` to use Tor.
   - Verify “Tor proxy enabled” in the status bar.
   - Browse a site (e.g., `https://duckduckgo.com`) to confirm proxy routing.

4. **Disable Proxy**:
   - Open the dialog and uncheck “Enable Proxy” or set `proxy_enabled: false` in `settings.json`.

## Troubleshooting
- **Plugin Fails to Load**:
  - Check console for errors (e.g., `Failed to import PyQt6 modules`).
  - Reinstall dependencies:
    ```bash
    pip install --upgrade PyQt6 PyQt6-WebEngine requests cryptography
    ```
- **Proxy Connection Fails**:
  - Verify proxy server is running (`netstat -an | findstr 9050` for Tor).
  - Test connectivity:
    ```bash
    curl --proxy socks5h://127.0.0.1:9050 https://check.torproject.org
    ```
  - Ensure `settings.json` has correct `proxy_host`, `proxy_port`, and `proxy_type`.
- **Tor Issues**:
  - Install Tor and verify it listens on `127.0.0.1:9050`.
  - Check firewall settings to allow outbound connections.
- **General Issues**:
  - Share console output and `settings.json` (redact sensitive data) for debugging.

## Notes
- **Legal Use**: Ensure proxy usage complies with your ISP and service provider terms. Avoid using proxies for illegal activities.[](https://github.com/ab77/netflix-proxy/blob/master/README.md)
- **Security**: Do not share `settings.json` publicly, as it contains proxy settings.
- **Performance**: Proxies (especially Tor) may slow browsing. Disable when not needed.
- **DNS Risks**: Tor proxies may enable DNS recursion, posing risks for amplification attacks. Ensure firewall rules are in place.[](https://github.com/ab77/netflix-proxy/blob/master/README.md)