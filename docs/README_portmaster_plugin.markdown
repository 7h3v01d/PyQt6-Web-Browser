# Portmaster Plugin

## Overview
The `portmaster_plugin.py` integrates network management into the Ib browser, providing a GUI and CLI interface to monitor and control network connections, ports, and servers. It reuses the `PortManagerCore` from `core.py` to list connections, check/block/unblock ports, kill processes, start/stop servers, and reserve/release ports. The plugin is accessible via `Plugins > portmaster_plugin > Portmaster` and supports Tor for anonymous operations.

### Features
- **Connections**: List active network connections in a sortable table and save to a file.
- **Port Management**: Check if a port is in use, block/unblock TCP/UDP ports, and kill processes by PID.
- **Server Management**: Start/stop servers on specified ports (TCP/UDP) using ZeroMQ.
- **Port Reservation**: Reserve/release ports for specific executables, stored in `port_reservations.json`.
- **CLI Interface**: Execute commands (e.g., `list`, `check-port 8080`) via a text input.
- **Anonymity**: Routes network operations through Tor when enabled (`Settings > Enable Tor Proxy`).
- **Integration**: Accessible via the browser’s plugin menu, with logs in `port_logs.txt`.

## Dependencies
- **Python**: 3.11.5
- **PyQt6**: 6.7.0
- **PyQt6-WebEngine**: 6.7.0
- **psutil**: For process and connection monitoring
- **pyzmq**: For ZeroMQ server functionality
- **requests**: For connectivity checks
- **cryptography**: For vault integration (optional)

Install dependencies:
```bash
E:\Projects\venv_importmapper\Scripts\activate
pip install PyQt6==6.7.0 PyQt6-WebEngine==6.7.0 psutil pyzmq requests cryptography
```

## Setup
1. **Save the Plugin and Core**:
   - Place `portmaster_plugin.py` in `E:\Projects\_webbrowser\src\plugins`.
   - Place `core.py` in `E:\Projects\_webbrowser\src\core`.
   - Ensure other files (`browser.py`, `vault.py`, `interceptors.py`, `settings.json`) are unchanged.
   - Create `E:\Projects\_webbrowser\src\configs` if it doesn’t exist for `port_reservations.json` and `port_logs.txt`.

2. **Integrate with Browser**:
   - Modify `browser.py` to load the plugin. Add to the plugin menu:
     ```python
     from plugins.portmaster_plugin import PortmasterPlugin
     # In BrowserWindow.__init__ or plugin initialization method
     portmaster_action = self.plugins_menu.addAction("Portmaster")
     portmaster_action.triggered.connect(lambda: PortmasterPlugin(self).exec())
     ```

3. **Clear Cached Bytecode**:
   - Remove cached files:
     ```bash
     rmdir /s /q E:\Projects\_webbrowser\src\__pycache__
     rmdir /s /q E:\Projects\_webbrowser\src\plugins\__pycache__
     rmdir /s /q E:\Projects\_webbrowser\src\core\__pycache__
     ```

## Usage
1. **Open the Plugin**:
   - Start the browser:
     ```bash
     cd /d E:\Projects\_webbrowser\src
     python main.py
     ```
   - Navigate to `Plugins > portmaster_plugin > Portmaster`.

2. **Connections Tab**:
   - Click “List Connections” to display active network connections (Protocol, Local/Remote Address, Status, PID, Process Name).
   - Enter a file path (e.g., `E:\Projects\_webbrowser\src\configs\output.txt`) and click “Save” to export connections.

3. **Port Management Tab**:
   - **Check Port**: Enter a port (e.g., `8080`) and click “Check” to see if it’s in use.
   - **Kill Process**: Enter a PID (e.g., `1234`) and click “Kill” (confirms via dialog).
   - **Block/Unblock Port**: Enter a port, select TCP/UDP, and click “Block” or “Unblock” (confirms via dialog).

4. **Server Tab**:
   - Enter a port (e.g., `5555`), select TCP/UDP, and click “Start” to run a ZeroMQ server.
   - Click “Stop” to stop the server (confirms via dialog).

5. **Reservations Tab**:
   - Enter a port (e.g., `8080`), protocol (TCP/UDP), and executable path (e.g., `C:\Program Files\app.exe`), then click “Reserve”.
   - Enter a port and click “Release” to free it.

6. **CLI Tab**:
   - Enter commands like `list`, `check-port 8080`, `kill 1234`, `block 8080 TCP`, `reserve 8080 TCP --exe-path C:\app.exe`, etc.
   - Click “Run” to execute and view output.

7. **Anonymity**:
   - Enable Anonymous mode (`Anonymous: On`) and Tor proxy (`Settings > Enable Tor Proxy`).
   - Verify “Tor proxy enabled” in the status bar for anonymous operations.

## Troubleshooting
- **Plugin Fails to Load**:
  - Check console for errors (e.g., `Failed to import psutil`).
  - Reinstall dependencies:
    ```bash
    pip install --upgrade PyQt6 PyQt6-WebEngine psutil pyzmq requests cryptography
    ```
- **Connections Not Listed**:
  - Verify `psutil` permissions (run as administrator if needed):
    ```bash
    net start | findstr "psutil"
    ```
  - Check `port_logs.txt` for errors.
- **Port Blocking Fails**:
  - Ensure `netsh` commands have admin privileges:
    ```bash
    netsh advfirewall firewall show rule name=all
    ```
  - Run the browser as administrator:
    ```bash
    cd /d E:\Projects\_webbrowser\src
    powershell -Command "Start-Process python main.py -Verb RunAs"
    ```
- **Server Issues**:
  - Verify port availability (`check-port <port>`).
  - Check `port_logs.txt` for ZeroMQ errors.
- **CLI Errors**:
  - Ensure correct command syntax (e.g., `list`, `check-port 8080`).
  - Check console for parsing errors.
- **General Issues**:
  - Clear cached bytecode:
    ```bash
    rmdir /s /q E:\Projects\_webbrowser\src\__pycache__
    rmdir /s /q E:\Projects\_webbrowser\src\plugins\__pycache__
    rmdir /s /q E:\Projects\_webbrowser\src\core\__pycache__
    ```
  - Share console output and `port_logs.txt` for debugging.

## Notes
- **Legal Use**: Ensure port blocking and process termination comply with system policies. Avoid disrupting critical services.
- **Security**: Keep `port_reservations.json` and `port_logs.txt` secure, as they may contain sensitive data.
- **Performance**: Tor may slow network operations; disable if not needed.
- **Admin Privileges**: Some operations (e.g., `netsh` for firewall rules) require admin rights.
- **File Paths**: Update `core.py` and plugin paths if your project uses a different directory structure (e.g., not `E:\Projects\_webbrowser\src\configs`).