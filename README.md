# PyQt6 Web Browser
A feature-rich, extensible web browser built with Python and the PyQt6 framework. This project goes beyond a simple web viewer, incorporating advanced features like a secure password manager, a powerful plugin system, and enhanced privacy tools.

⚠️ **LICENSE & USAGE NOTICE — READ FIRST**

This repository is **source-available for private technical evaluation and testing only**.

- ❌ No commercial use  
- ❌ No production use  
- ❌ No academic, institutional, or government use  
- ❌ No research, benchmarking, or publication  
- ❌ No redistribution, sublicensing, or derivative works  
- ❌ No independent development based on this code  

All rights remain exclusively with the author.  
Use of this software constitutes acceptance of the terms defined in **LICENSE.txt**.

---

## 🚀 Features

- Modern Tabbed Browsing: A familiar and intuitive multi-tab interface.
- Secure Credential Vault: An encrypted, master-password-protected vault for storing website logins and API keys.
- Automatic Password Management:
- Autofill: Automatically fills login credentials on recognized websites.
- Password Capture: Prompts to save credentials after a successful login.
- Extensible Plugin System: Easily add new functionality through custom plugins. Comes with several pre-built plugins:
- AI Chat (xAI & Gemini)
- Netflix & YouTube Downloaders
- Anonymity Tools (Tor Proxy)
- Web Developer Tools (Proxy & Repeater)
- And more!

## Privacy Focused:

- Anonymous Mode: Rotates user agents and disables history tracking.
- Tor Integration: Route traffic through the Tor network for enhanced anonymity.
- Ad Blocker: Integrated ad-blocking functionality using the EasyList standard.
- Standard Browser Features: Includes bookmarks, history, developer tools, dark mode, and download management.

## 🛠️ Getting Started
Follow these instructions to get the project running on your local machine.

Prerequisites
You will need Python 3 and pip installed.

Installation & Setup
Clone the repository (or download the source code).

Navigate to the src directory:
```bash
cd path/to/your/project/src
```
Install the required dependencies:
```bash
pip install PyQt6 PyQt6-WebEngine cryptography requests
```
Note: Some plugins may have additional dependencies like yt-dlp or PyPDF2.

Run the application:
```bash
python main.py
```
First-Time Setup: On the first launch, you will be prompted to create a master password. This password encrypts your vault and is required every time you start the browser to access your saved logins and API keys.

## 🔐 Password & API Key Management
The browser's core security feature is its encrypted vault (credentials.vault).

Adding Credentials: Go to Settings -> Password Manager. From there, you can add website logins or API keys for services like Gemini and xAI.

Revealing Secrets: For security, passwords and keys are masked. To view one, select the entry and click the "Reveal" button. You will be asked to re-enter your master password to confirm your identity.

Autofill & Capture: When you log into a website, the browser will ask if you want to save the password. If you agree, it will automatically fill in those details the next time you visit the site. This feature can be toggled in the Settings menu.

## 🔌 Plugin System
The browser is designed to be modular. You can create your own Python plugins and place them in the src/plugins directory. The browser will automatically discover and load them on startup.

A valid plugin is a Python file that contains a class named Plugin which inherits from the base Plugin class in interceptors.py.

## Contribution Policy

Feedback, bug reports, and suggestions are welcome.

You may submit:

- Issues
- Design feedback
- Pull requests for review

However:

- Contributions do not grant any license or ownership rights
- The author retains full discretion over acceptance and future use
- Contributors receive no rights to reuse, redistribute, or derive from this code

---

## License
This project is not open-source.

It is licensed under a private evaluation-only license.
See LICENSE.txt for full terms.
