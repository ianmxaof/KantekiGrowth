## Webhook Server & ngrok Setup

To enable Telegram webhooks and test locally, follow these steps:

### 1. Prerequisites

- Ensure you have Python 3.8+ installed.
- Download [ngrok](https://ngrok.com/download) and add it to your system PATH, or place `ngrok.exe` in the `Telegram_Bots` folder.

### 2. Launch the Webhook Server and ngrok

From the `Telegram_Bots` directory, run:

```bat
launch_webhook.bat
```

This will:

- Start the webhook server (`Webhooks/webhook_server.py`) in a new terminal window.
- Start ngrok on port 5000 in another terminal window.
- Show logs and errors in their respective windows.

### 3. Get Your Public ngrok URL

- After running the script, copy the HTTPS forwarding URL from the ngrok window (e.g., `https://xxxx.ngrok.io`).
- Use this URL to set your Telegram webhook.

### 4. Troubleshooting

- **ngrok not found:** Download ngrok and add it to your PATH, or place `ngrok.exe` in this folder.
- **Python not found:** Ensure Python is installed and added to your PATH.
- **Port 5000 in use:** Change the port in both the batch script and your webhook server if needed.
- **Script not launching:** Run the batch file as administrator if you encounter permission issues.

---
