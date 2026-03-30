# 🧠 GitPulse: GitHub Talent Finder (Pro)

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Gemini AI](https://img.shields.io/badge/Gemini--AI-4285F4?style=for-the-badge&logo=google-cloud)](https://aistudio.google.com/)

GitPulse is an advanced, asynchronous developer intelligence dashboard that uses AI to analyze GitHub talent at scale.

## ✨ Extraordinary Features

-   **🤖 Real-Time Gemini Summaries**: Uses Google Gemini Pro to generate professional, multi-sentence summaries of a developer's skills based on their bio and activity.
-   **⚡ Asynchronous Architecture**: Powered by FastAPI and `httpx` for non-blocking, concurrent API interactions.
-   **🧠 Behavioral Personas**: Classifies developers (e.g., "The Architect", "The Exterminator") by analyzing their latest commit messages.
-   **🛡️ Engineering Rigor Grading**: Automatically grades repository quality (A-F) based on stars, forks, and health metrics.
-   **📈 Market Trends Dashboard**: Scans GitHub in real-time to identify the hottest technical topics (AI, FastAPI, etc.).

## 🚀 Getting Started

1.  **Clone & Install**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Environment Setup**:
    Create a `.env` file in this folder:
    ```env
    GITHUB_TOKEN=your_github_token
    GEMINI_API_KEY=your_gemini_api_key
    ```
3.  **Run the Server**:
    ```bash
    uvicorn main:app --reload --port 8000
    ```

## 🛠️ Tech Stack
-   **Backend**: FastAPI, Httpx (Async)
-   **AI**: Google Generative AI (Gemini Pro)
-   **Frontend**: Vanilla HTML5, Modern CSS, Chart.js
-   **Data**: Openpyxl (Excel Exporting)
