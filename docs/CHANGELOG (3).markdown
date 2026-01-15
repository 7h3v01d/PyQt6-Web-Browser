# Changelog

All notable changes to the Ib browser project (`E:\Projects\_webbrowser\src`) are documented in this file. Changes are listed in reverse chronological order.

## [Unreleased]

### 2025-08-27
**Added**
- **Portmaster Plugin** (`portmaster_plugin.py`, artifact_id: 8a9f7b3c-9e4e-4f7b-9a1d-5c2e7f8b6d9c):
  - Created plugin integrating `cli.py` and `gui.py` for network management.
  - Features: List connections, check/block/unblock ports, kill processes, start/stop servers, reserve/release ports, CLI interface.
  - Uses `core.py` (`PortManagerCore`) in `E:\Projects\_webbrowser\src\core`.
  - Integrated with browser’s plugin menu (`Plugins > portmaster_plugin > Portmaster`).
  - Supports Tor for anonymous operations and stores data in `port_reservations.json` and `port_logs.txt`.
- **Portmaster Plugin Documentation** (`README_portmaster_plugin.md`, artifact_id: 4b8c2a9d-3f2e-4c9a-a7b2-6d1f8e7c4a3e):
  - Created `README.md` for `portmaster_plugin.py`.
  - Detailed setup (including `core.py` placement), usage (GUI and CLI tabs), and troubleshooting.
  - Noted dependencies (`psutil`, `pyzmq`) and admin privilege requirements.
- **YouTube Downloader Plugin Documentation** (`README_youtube_downloader_plugin.md`, artifact_id: c3419dc9-b205-4656-b0f1-9b7fed0fa68d):
  - Created `README.md` for `youtube_downloader_plugin.py`.
  - Detailed setup, usage (downloading videos/audio, quality/subtitle options), and troubleshooting.
  - Noted integration with `yt_dlp`, Tor support, and optional credential storage in `credentials.vault`.
- **Whitelist Plugin Documentation** (`README_whitelist_plugin.md`, artifact_id: 34e45cf3-a3da-44b8-9393-9b47f62ed2f1):
  - Created `README.md` for `whitelist_plugin.py`.
  - Described whitelist management, request filtering via `interceptors.py`, and configuration in `settings.json` or `whitelist.json`.
- **Netflix Downloader Plugin Documentation** (`README_netflix_downloader_plugin.md`, artifact_id: 83488fed-13e4-4e22-9bf1-32aa2c63dc37):
  - Created `README.md` for `netflix_downloader_plugin.py`.
  - Outlined setup with `yt_dlp` and Widevine DRM, credential storage in `credentials.vault`, and usage.
- **Proxy Plugin Documentation** (`README_proxy_plugin.md`, artifact_id: 4357fefb-4fd9-4578-9f51-a30a0ee72ec3):
  - Created `README.md` for `proxy_plugin.py`.
  - Detailed proxy configuration (HTTP, HTTPS, Socks5, Tor) and integration with `settings.json`.
- **Repeater Plugin Documentation** (`README_repeater_plugin.md`, artifact_id: 7dcc5ff1-b953-442d-95cd-ecb350fb79ea):
  - Created `README.md` for `repeater_plugin.py`.
  - Described HTTP request capture and replay via `interceptors.py`.

### 2025-08-26
**Added**
- **AI Chat Plugin Documentation** (`README_ai_chat_plugin.md`, artifact_id: 2c065da7-7c78-446a-88ab-7ebe305274ce):
  - Created `README.md` for `ai_chat_plugin.py`.
  - Detailed setup, usage (context-aware chat, file analysis, code generation), and troubleshooting.
- **Gemini Chat Plugin Documentation** (`README_gemini_chat_plugin.md`, artifact_id: c8ff9887-8ce1-4001-a4ce-5b7f448d3ce1):
  - Created `README.md` for `gemini_chat_plugin.py`.
  - Noted secure API key storage in `credentials.vault`.

**Changed**
- **Gemini Chat Plugin** (`gemini_chat_plugin.py`, artifact_id: d5957787-0fa4-4cab-b2b0-74ba29f929c8):
  - Updated API key storage to use `credentials.vault` via `vault.py`.
  - Provided alternative version using `settings.json` (artifact_version_id: 946769c6-ec3f-4ff0-b8a7-711aa93f349e).

### 2025-08-25
**Added**
- **Gemini Chat Plugin** (`gemini_chat_plugin.py`, artifact_id: d5957787-0fa4-4cab-b2b0-74ba29f929c8):
  - Created plugin for Google Gemini integration.
  - Features: Context-aware chat, file analysis, code generation, Tor support.
  - Stores conversation history in `gemini_chat_history.json`.

**Fixed**
- **AI Chat Plugin**:
  - Addressed API key storage in `settings.json` (`xai_api_key`).

## [0.1.0] - 2025-08-24
**Added**
- **AI Chat Plugin** (`ai_chat_plugin.py`):
  - Initial creation for xAI Grok 3 integration.
  - Features: Text-based chat, context-aware responses, file analysis, code generation, Tor support.
  - Stores conversation history in `chat_history.json`.

**Notes**
- Provided setup instructions for running the browser and configuring dependencies.

## [0.0.1] - 2025-08-20
**Added**
- **Project Initialization**:
  - Created project directory `E:\Projects\_webbrowser\src`.
  - Set up Python virtual environment:
    ```bash
    python -m venv E:\Projects\venv_importmapper
    E:\Projects\venv_importmapper\Scripts\activate
    ```
  - Installed core dependencies:
    ```bash
    pip install PyQt6==6.7.0 PyQt6-WebEngine==6.7.0 requests cryptography Pillow PyPDF2 yt_dlp
    ```
- **Core Files**:
  - `browser.py`: Implemented main browser window with tabbed browsing, bookmarks, history, plugin support, and JavaScript-Python communication.
  - `vault.py`: Created secure credential storage with AES-256-GCM and PBKDF2.
  - `interceptors.py`: Added `ChainedInterceptor` and `AdBlockInterceptor`.
  - `dialogs.py`: Added dialogs for history, dev tools, and password management.
  - `main.py`: Created entry point.
  - `password_manager.js`: Added for login form detection and autofill.
  - Configuration files: Initialized `settings.json`, `bookmarks.json`, `tabs.json`, `history.json`.
- **Secure Credential Management**:
  - Implemented `vault.py` for encrypted storage in `credentials.vault`.
  - Added Password Manager UI (`Settings > Password Manager`) with master password re-authentication.
  - Migrated API keys to `credentials.vault` for plugins like `gemini_chat_plugin.py`.
- **Password Autofill and Capture**:
  - Added `password_manager.js` for login form detection.
  - Implemented password saving dialog and autofill, toggleable via `Settings > Autofill Enabled`.
- **DRM and Playback Support**:
  - Attempted Widevine CDM support for Netflix, with ongoing M7701-1003 error.
- **Plugins Directory**:
  - Created `plugins` directory with `__init__.py` and `sample_plugin.py`.

**Fixed**
- **PyQt6 Versioning Errors**:
  - Resolved `AttributeError` exceptions for script injection and settings.
- **JavaScript Injection Timing**:
  - Fixed `ReferenceError` by consolidating `password_manager.js` injection.

**Notes**
- Established secure foundation with encrypted vault and password management.
- Ongoing work needed for Netflix DRM issue (M7701-1003).