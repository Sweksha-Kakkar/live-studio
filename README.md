# Live Studio

A real-time web studio to test and interact with Google Gemini Live API models using bidirectional voice, real-time transcription, translation, and extended reasoning.

---

## Features

- **Bidirectional Voice Streaming:** Talk in real time using your microphone with instant audio replies and interruption support.

- **Support for 6 Gemini Live Models:**
  - `gemini-2.5-flash-native-audio-latest`: Native-audio dialog with visible thought process.
  - `gemini-3.1-flash-live-preview`: Ultra-fast, low-latency live voice interaction.
  - `gemini-3.8-live`: General-purpose live voice model.
  - `gemini-3.8-live-extended-thinking`: Configurable deep reasoning before responding.
  - `gemini-3.5-live-translate-preview`: Real-time speech-to-speech translation in multiple languages.
  - `gemini-3.5-transcribe-live`: Real-time speech-to-text without voice replies.

- **Audio Visualizers:** Live volume meters for both your voice and the AI's audio stream.

- **Customizable Controls:** Voice selection (Puck, Charon, Kore, Fenrir, etc.), system instructions, thinking level, and translation targets.

- **Secure Architecture:** Your Gemini API key is loaded on the FastAPI server and relayed via WebSocket—it never touches the browser frontend.

---

## Project Structure

```text
live_studio_app/
│
├── live_studio/
│   ├── index.html          # Web UI with audio recording, player, and live chat
│   ├── server.py           # FastAPI backend relaying WebSockets to Gemini Live API
│   └── LIVE_API_GUIDE.md   # Reference guide for Gemini Live API & WebSocket protocol
│
├── .env.example            # Environment variable template
├── .gitignore              # Files to ignore from git
├── requirements.txt        # Python package dependencies
└── README.md               # Project documentation
```

---

## Getting Started

### 1. Prerequisites

- Python 3.10 or higher
- A Google Gemini API key from [Google AI Studio](https://aistudio.google.com/)

### 2. Installation

Clone this repository:

```bash
git clone https://github.com/Sweksha-Kakkar/live-studio.git
cd live-studio
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

### 3. Configure API Key

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Open `.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your_actual_api_key_here
```

**Keep your API key private. Do not commit your `.env` file to GitHub.**

### 4. Run the Application

Start the server:

```bash
python live_studio/server.py
```

Your browser will automatically open at `http://localhost:8000`.

Grant microphone permissions, select a model, and click **Connect** to get started.

---

## Live API Guide

For detailed technical explanations, curl commands, and WebSocket message schemas, see [`live_studio/LIVE_API_GUIDE.md`](live_studio/LIVE_API_GUIDE.md).

---

## Deployment

The application has been deployed on Render and is available online.

**Live Website:** [https://live-studio-33p5.onrender.com](https://live-studio-33p5.onrender.com)

**GitHub Repository:** [https://github.com/Sweksha-Kakkar/live-studio](https://github.com/Sweksha-Kakkar/live-studio)

