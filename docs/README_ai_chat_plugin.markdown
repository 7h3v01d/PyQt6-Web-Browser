# AI Chat Plugin (xAI Grok 3)

## Overview
The `ai_chat_plugin.py` integrates xAI’s Grok 3 AI into the PyQt6 web browser, enabling an interactive chat interface within the browser. It supports context-aware conversations using the current webpage, file analysis (images and PDFs), code generation, and anonymous API calls via Tor.

### Features
- **Chat Interface**: Send queries to Grok 3 and view responses in a dialog.
- **Context-Aware**: Uses the current webpage’s content for relevant answers (e.g., summarize a page).
- **File Analysis**: Upload images (PNG/JPG) or PDFs for analysis (e.g., describe images, extract PDF text).
- **Code Generation**: Generate code snippets (e.g., Python) in markdown format.
- **Anonymity**: Route API calls through Tor when Anonymous mode and Tor proxy are enabled.
- **History**: Save conversations to `chat_history.json` in `E:\Projects\_webbrowser\src`.

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
   - Place `ai_chat_plugin.py` in `E:\Projects\_webbrowser\src\plugins`.
   - Ensure other files (`browser.py`, `vault.py`, `interceptors.py`, etc.) are unchanged.

2. **Obtain xAI API Key**:
   - Visit `https://x.ai/api` to get a Grok 3 API key (e.g., `sk_1234567890abcdef`).

3. **Add API Key**:
   - **Option 1: Via Plugin Prompt**:
     - Run the browser:
       ```bash
       cd /d E:\Projects\_webbrowser\src
       python main.py
       ```
     - Open `Plugins > ai_chat_plugin > AI Chat`.
     - Enter the master password for `credentials.vault` (set during browser initialization).
     - When prompted, enter the xAI API key. It will be saved to `settings.json` as `xai_api_key`.
   - **Option 2: Manual `settings.json`**:
     - Open `E:\Projects\_webbrowser\src\settings.json`.
     - Add:
       ```json
       {
         "homepage": "https://duckduckgo.com/",
         "ad_blocker_enabled": false,
         "tor_enabled": false,
         "autofill_enabled": true,
         "xai_api_key": "YOUR_XAI_API_KEY"
       }
       ```
     - Replace `YOUR_XAI_API_KEY` with your key.
   - **Option 3: Reset Vault** (if using `vault.py` for future updates):
     - Delete `credentials.vault`:
       ```bash
       del E:\Projects\_webbrowser\src\credentials.vault
       ```
     - Run the browser to create a new vault with a master password.
     - Use the plugin to enter the API key.

4. **Clear Cached Bytecode**:
   - Remove cached files to avoid import issues:
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
   - Navigate to `Plugins > ai_chat_plugin > AI Chat` to open the dialog.

2. **Basic Chat**:
   - Enter a query (e.g., “What is the capital of France?”) in the input field.
   - Press Enter or click “Send Message”.
   - View the response in the chat history. Conversations are saved to `chat_history.json`.

3. **Context-Aware Chat**:
   - Open a webpage (e.g., `https://en.wikipedia.org/wiki/Python_(programming_language)`).
   - Type “Summarize this page” in the dialog.
   - The response uses the page’s content, shown in the preview window.

4. **File Analysis**:
   - Click “Upload File” and select an image (PNG/JPG) or PDF.
   - For images, Grok describes the content (e.g., “This image shows a landscape...”).
   - For PDFs, Grok extracts and analyzes text (requires `PyPDF2`).
   - Temporary files are stored in `E:\Projects\_webbrowser\src\temp`.

5. **Code Generation**:
   - Type “Write a Python function to reverse a string”.
   - The response is formatted as a markdown code block (e.g., ```python def reverse_string(s): return s[::-1] ```).

6. **Anonymity**:
   - Enable Anonymous mode (`Anonymous: On`) and Tor proxy (`Settings > Enable Tor Proxy`).
   - API calls route through Tor (Socks5 proxy at `127.0.0.1:9050`).
   - Verify “Tor proxy enabled” in the status bar.

7. **Clear History**:
   - Click “Clear History” to reset `chat_history.json`.

## Troubleshooting
- **Plugin Fails to Load**:
  - Check console for errors (e.g., `Failed to import PyQt6 modules`).
  - Reinstall dependencies:
    ```bash
    pip install --upgrade PyQt6 PyQt6-WebEngine requests Pillow PyPDF2 cryptography
    ```
- **API Key Prompt Reappears**:
  - Verify `settings.json` contains `xai_api_key` or check `credentials.vault` with the correct master password.
  - Test the key:
    ```bash
    curl -H "Authorization: Bearer YOUR_API_KEY" https://api.x.ai/v1/chat/completions
    ```
- **API Call Fails**:
  - Ensure Tor is running if enabled (`netstat -an | findstr 9050`).
  - Check xAI API quotas at `https://x.ai/grok`.
- **File Analysis Errors**:
  - Confirm `PyPDF2` is installed for PDFs.
  - Ensure uploaded files are valid (PNG/JPG for images, readable PDFs).
- **General Issues**:
  - Share console output and `settings.json` (redact API key) for debugging.

## Notes
- **Legal Use**: Comply with xAI’s API terms (`https://x.ai/api`). Avoid illegal queries or copyrighted content analysis.
- **Security**: Keep `settings.json` and `credentials.vault` secure. Do not share API keys publicly.
- **Performance**: Tor may slow API calls; disable it for faster responses if anonymity isn’t needed.
- **Quotas**: Grok 3 has usage limits (free or SuperGrok plans). Check `https://x.ai/grok` for details.