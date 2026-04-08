# Ghost Auditor 👻🔎

Ghost Auditor is an AI-powered SaaS management tool that helps you automatically identify inactive (ghost) seats across your software tools, calculate wasted spend, and optimize your billing.

By leveraging a computer-use web agent ([TinyFish](https://tinyfish.ai)), Ghost Auditor autonomously navigates admin dashboards (like Slack's Workspace Administration) to securely audit member lists, extract last-active times, and generate comprehensive ROI reports without needing deep API integrations for every SaaS platform.

## Features ✨

- **Autonomous Agent Data Extraction:** Bypasses complex API limitations by browsing like a real administrator securely.
- **Wasted Spend Dashboard:** Automatically flags members inactive for over 30 days and calculates monthly/annual wasted spend.
- **Exportable Reports:** Export the audit results natively as CSV files to share with IT or Finance teams.
- **Local SQLite DB:** No massive database setups required; everything is stored locally for quick deployments.
- **Secure Encrypted Storage:** Sensitive information, such as API keys and session cookies, are safely encrypted using `Fernet` symmetric encryption.

## Prerequisites 📋

- Python 3.9+
- A Google Cloud Platform (GCP) project for OAuth authentication (if you want the login flow, optional).
- TinyFish API Key to run the live auditor agent.

## Setup and Installation 🚀

1. **Clone the repo:**
   ```bash
   git clone https://github.com/Boss17536/ghost-auditor.git
   cd ghost-auditor
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Copy the `.env.example` file to create your local `.env`:
   ```bash
   cp .env.example .env
   ```
   Fill in the necessary values:
   - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: For Google OAuth.
   - `SECRET_KEY`: Flask Secret Key.
   - `TINYFISH_API_KEY`: API Key to run the TinyFish browser extraction.
   - `ENCRYPTION_KEY`: A base64-encoded 32-byte key generated with `cryptography.fernet.Fernet.generate_key()`.

## Running Locally 🖥️

If you just want to see how the dashboard handles data, we have an interactive Demo batch script:

1. Double-click or run `start_demo.bat` inside the terminal.
2. The script will parse the mock `slack_members.csv` into a format the dashboard accepts and start the local webserver at `http://127.0.0.1:5000`.

To run the full Flask app with live AI Auditing:
```bash
python app.py
```
Navigate to `http://127.0.0.1:5000` in your browser.

## Contributing 🤝

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

Please check out our [CONTRIBUTING.md](./CONTRIBUTING.md) for details on how to contribute.

## License 📜

Distributed under the MIT License. See [LICENSE](./LICENSE) for more information.
