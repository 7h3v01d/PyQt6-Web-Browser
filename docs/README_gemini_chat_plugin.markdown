# Gemini Chat Plugin (Google Gemini)

## Overview
The `gemini_chat_plugin.py` integrates Google’s Gemini AI into the PyQt6 web browser, providing a chat interface for natural language queries, file analysis, and code generation. It leverages the browser’s current webpage for context and supports anonymous API calls via Tor. API keys are securely stored in `credentials.vault` using the password manager (`vault.py`).

### Features
- **Chat Interface**: Interact with Gemini for queries and responses.
- **Context-Aware**: Uses webpage content for relevant answers (e.g., summarize a page).
- **File Analysis**: Analyze uploaded images (PNG/JPG) or PDFs (text extraction).
- **Code Generation**: Generate code snippets (e.g., Python) in markdown format.
- **Anonymity**: Route API calls through Tor when enabled.
- **History**: Save conversations to `gemini_chat_history.json` in `E:\Projects\_webbrowser\src`.
- **Secure Storage**: Store API key in `credentials.vault` using `vault.py`.

## Dependencies
- **Python**: 3.11.5
- **PyQt6**: 6.7.0
- **PyQt6-WebEngine**: 6.7.0
- **requests**: For API calls
- **Pillow**: For image processing
- **PyPDF2**: For PDF text extraction
- **cryptography**: For vault encryption (via `vault.py`)

Install dependencies:
```bash
E:\Projects\venv_importmapper\Scripts\activate
pip install PyQt6==6.7.0 PyQt6-WebEngine==6.7.0 requests Pillow PyPDF2 cryptography
```

## Setup
1. **Save the Plugin**:
   - Place `gemini_chat_plugin.py` in `E:\Projects\_webbrowser\src\plugins`.
   - Ensure other files (`browser.py`, `vault.py`, `interceptors.py`, etc.) are unchanged.

2. **Obtain Gemini API Key**:
   - Visit `https://console.cloud.google.com/`.
   - Enable the “Generative Language API” and create an API key (e.g., `AIzaSy1234567890abcdef`).

3. **Add API Key**:
   - **Option 1: Via Plugin Prompt** (Recommended):
     - Run the browser:
       ```bash
       cd /d E:\Projects\_webbrowser\src
       python main.py
       ```
     - Open `Plugins > gemini_chat_plugin > Gemini Chat`.
     - Enter the master password for `credentials.vault` (set during browser initialization).
     - When prompted, enter the Gemini API key. It will be saved to `credentials.vault` under `api_keys` as `{"service": "gemini", "key": "YOUR_API_KEY"}`.
   - **Option 2: Reset Vault**:
     - Delete `credentials.vault` (backup first):
       ```bash
       del E:\Projects\_webbrowser\src\credentials.vault
       ```
     - Run the browser to create a new vault with a master password.
     - Use the plugin to enter the API key.
   - **Option 3: Manual `settings.json`** (Less Secure):
     - Open `E:\Projects\_webbrowser\src\settings.json`.
     - Add:
       ```json
       {
         "homepage": "https://duckduckgo.com/",
         "ad_blocker_enabled": false,
         "tor_enabled": false,
         "autofill_enabled": true,
         "gemini_api_key": "YOUR_GEMINI_API_KEY"
       }
       ```
     - Update `gemini_chat_plugin.py` to use `settings.json` (see alternative version in conversation history).

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
   - Navigate to `Plugins > gemini_chat_plugin > Gemini Chat`.

2. **Basic Chat**:
   - Enter a query (e.g., “What is the capital of France?”) in the input field.
   - Press Enter or click “Send Message”.
   - View the response in the chat history. Conversations are saved to `gemini_chat_history.json`.

3. **Context-Aware Chat**:
   - Open a webpage (e.g., `https://duckduckgo.com`).
   - Type “Summarize this page” in the dialog.
   - The response uses the page’s content, shown in the preview window.

4. **File Analysis**:
   - Click “Upload File” and select an image (PNG/JPG) or PDF.
   - For images, Gemini describes the content (e.g., “This image shows a mountain...”).
   - For PDFs, Gemini extracts and analyzes text (requires `PyPDF2`).
   - Temporary files are stored in `E:\Projects\_webbrowser\src\temp`.

5. **Code Generation**:
   - Type “Write a Python function to reverse a string”.
   - The response is formatted as a markdown code block (e.g., ```python def reverse_string(s): return s[::-1] ```).

6. **Anonymity**:
   - Enable Anonymous mode (`Anonymous: On`) and Tor proxy (`Settings > Enable Tor Proxy`).
   - API calls route through Tor (Socks5 proxy at `127.0.0.1:9050`).
   - Verify “Tor proxy enabled” in the status bar.

7. **Clear History**:
   - Click “Clear History” to reset `gemini_chat_history.json`.

## Troubleshooting
- **Plugin Fails to Load**:
  - Check console for errors (e.g., `Failed to import PyQt6 modules`).
  - Reinstall dependencies:
    ```bash
    pip install --upgrade PyQt6 PyQt6-WebEngine requests Pillow PyPDF2 cryptography
    ```
- **API Key Prompt Reappears**:
  - Verify `credentials.vault` and the master password.
  - Check console for `Invalid master password` or `Failed to save API key`.
- **API Call Fails**:
  - Test the API key:
    ```bash
    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_API_KEY" -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
    ```
  - Check Google Cloud Console for quota limits.
  - Ensure Tor is running if enabled (`netstat -an | findstr 9050`).
- **File Analysis Errors**:
  - Confirm `PyPDF2` is installed for PDFs.
  - Ensure uploaded files are valid.
- **General Issues**:
  - Share console output and `credentials.vault` size (not content) for debugging.

## Notes
- **Legal Use**: Comply with Google’s API terms (`https://cloud.google.com/terms`). Avoid analyzing copyrighted content without permission.
- **Security**: Keep `credentials.vault` secure. Do not share the master password or API key.
- **Performance**: Tor may slow API calls; disable it if anonymity isn’t needed.
- **Quotas**: Gemini API has usage limits. Check Google Cloud Console for details.