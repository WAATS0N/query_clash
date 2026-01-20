# Query Clash: SQL Murder Mystery Edition 🕵️‍♂️💻

Query Clash is a competitive, web-based SQL investigation platform. This edition features the famous **SQL Murder Mystery** integrated into a high-stakes, cyberpunk-themed competition environment.

![Query Clash UI](static/illustration.png)

## 🌟 Features

- **Immersive Storyline**: Investigating a murder in SQL City using real SQL queries.
- **Dynamic SQL Terminal**: Multi-tab terminal interface with real-time results and error feedback.
- **Live Leaderboard**: Real-time analytics tracking query counts, time taken, and solved status.
- **Persistent Notepad**: Built-in "Case Notes" area that saves automatically to your browser.
- **Visual Schema**: Interactive table list and a full database schema map for quick reference.
- **Dynamic Registration**: Instant login—simply choose a unique username and password to start.
- **Professional Structure**: Organized for scalability with dedicated `docs/`, `scripts/`, and `tests/` directories.

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- SQLite3

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/WAATS0N/query_clash.git
   cd query_clash
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Initialize the database:

   ```bash
   python init_db.py
   ```

4. Run the application:
   ```bash
   python app.py
   ```
   _Access the game at `http://127.0.0.1:5000`_

## 🕵️ The Investigation

**Objective:** A murder occurred on **Jan 15, 2018** in **SQL City**. You must use your SQL skills to:

1. Retrieve the crime scene report.
2. Track down witnesses and suspects.
3. Identify the killer and the mastermind behind the crime.

**Round 1:** Find the primary suspect.
**Round 2:** Uncover the true mastermind.

## 📁 Project Structure

```text
query_clash/
├── app.py              # Flask Backend API
├── init_db.py          # Database Setup & Migration
├── database.db         # SQLite Database (Auto-generated)
├── docs/               # Deployment & Security Documentation
├── scripts/            # Utility & Inspection Scripts
├── static/             # Cyberpunk UI Assets (CSS/JS/Images)
├── templates/          # HTML Templates
└── tests/              # Automated Test Suite
```

## 🛠️ Built With

- **Backend:** Python, Flask, SQLite
- **Frontend:** Vanilla JS, Tailwind-inspired Cyberpunk CSS
- **Deployment:** Gunicorn, Docker ready

## 🤝 Contributing

Feel free to open issues or submit pull requests to enhance the UI or add new mystery modules!
