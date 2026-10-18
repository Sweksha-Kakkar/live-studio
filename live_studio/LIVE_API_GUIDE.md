# Gemini Live API: how to call it (with curl)

A reference for calling the six Gemini Live models on this API key directly: which HTTP calls work with `curl`, and the exact WebSocket messages for everything else. All JSON below was tested against the live API on 2026-09-28.

## Contents

1. [How the API is split: REST vs WebSocket](#1-how-the-api-is-split-rest-vs-websocket)
2. [Authentication](#2-authentication)
3. [curl: list and inspect models](#3-curl-list-and-inspect-models)
4. [The Live WebSocket](#4-the-live-websocket)
5. [Setup message for each model](#5-setup-message-for-each-model)
6. [Sending input](#6-sending-input)
7. [What the server sends back](#7-what-the-server-sends-back)
8. [Trying it from a terminal](#8-trying-it-from-a-terminal)
9. [Gotchas](#9-gotchas)

---

## 1. How the API is split: REST vs WebSocket

| What you want | Protocol | Works with curl? |
|---|---|---|
| List models, read a model's limits | REST (HTTPS) | Yes |
| Talk to a Live model (voice, translate, transcribe) | WebSocket, both directions at once | No |

Live models support only one method, `bidiGenerateContent` ("bidirectional"). You keep one connection open, stream audio up, and receive audio and text back while you are still talking. `curl` sends a request and waits for a response, so it can't hold that conversation. For the live part, use a WebSocket client (section 8) or code.

---

## 2. Authentication

Get a key at <https://aistudio.google.com/apikey>. In this project it lives in `.env` as `GEMINI_API_KEY`.

- **REST:** send it as a header: `x-goog-api-key: $GEMINI_API_KEY`
- **WebSocket:** pass it in the URL: `...BidiGenerateContent?key=$GEMINI_API_KEY`

Because the key sits in the WebSocket URL, don't paste those URLs into chats, screenshots or logs.

Load the key into your shell:

```bash
# bash / Git Bash
set -a; . ./.env; set +a
```

```powershell
# PowerShell
Get-Content .env | Where-Object { $_ -match '^GEMINI_API_KEY=' } | ForEach-Object { $env:GEMINI_API_KEY = $_.Split('=', 2)[1] }
```

---

## 3. curl: list and inspect models

**List every model that supports the Live API:**

```bash
curl -s "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  | python -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin)['models'] if 'bidiGenerateContent' in m.get('supportedGenerationMethods',[])]"
```

```powershell
# PowerShell: use curl.exe, because plain "curl" is an alias for Invoke-WebRequest
curl.exe -s "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200" -H "x-goog-api-key: $env:GEMINI_API_KEY"
```

**Read one model's details:**

```bash
curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-live" \
  -H "x-goog-api-key: $GEMINI_API_KEY"
```

Response:

```json
{
  "name": "models/gemini-3.8-live",
  "displayName": "Gemini 3.8 Live",
  "inputTokenLimit": 131072,
  "outputTokenLimit": 65536,
  "supportedGenerationMethods": ["bidiGenerateContent"],
  "temperature": 1,
  "topP": 0.95,
  "topK": 64,
  "maxTemperature": 2
}
```

**The six models and their IDs:**

| AI Studio name | Model ID | What it does |
|---|---|---|
| Gemini 2.5 Flash Native Audio Dialog | `gemini-2.5-flash-native-audio-latest` | Voice chat; also returns its thinking as text |
| Gemini 3 Flash Live | `gemini-3.1-flash-live-preview` | Fast voice chat |
| Gemini 3.8 Live | `gemini-3.8-live` | Voice chat |
| Gemini 3.8 Live Extended Thinking | `gemini-3.8-live-extended-thinking` | Voice chat that reasons first |
| Gemini 3.5 Live Translate | `gemini-3.5-live-translate-preview` | Speech in, translated speech out |
| Gemini 3.5 Transcribe Live | `gemini-3.5-transcribe-live` | Speech in, text out |

---

## 4. The Live WebSocket

**Endpoint:**

```
wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=YOUR_KEY
```

**Message flow.** Every message is a JSON object, in both directions.

```
you                                   server
 │  1. {"setup": {...}}          ──►
 │                               ◄──  {"setupComplete": {}}
 │  2. {"realtimeInput": ...}    ──►   (repeat: audio chunks or text)
 │                               ◄──  {"serverContent": ...}  (audio, transcripts, many messages)
 │                               ◄──  {"serverContent": {"turnComplete": true}}
 │  ... keep streaming; the connection stays open for the whole conversation
```

- The **first** message must be `setup`, and you can send only one. To change model or settings, open a new connection.
- Wait for `setupComplete` before sending input.

---

## 5. Setup message for each model

### Voice chat: 2.5 Native Audio, 3 Flash Live, 3.8 Live

```json
{
  "setup": {
    "model": "models/gemini-3.8-live",
    "generationConfig": {
      "responseModalities": ["AUDIO"],
      "speechConfig": {
        "voiceConfig": { "prebuiltVoiceConfig": { "voiceName": "Kore" } }
      }
    },
    "systemInstruction": { "parts": [{ "text": "Answer in one short sentence." }] },
    "inputAudioTranscription": {},
    "outputAudioTranscription": {}
  }
}
```

- Swap `model` for `models/gemini-2.5-flash-native-audio-latest` or `models/gemini-3.1-flash-live-preview`; everything else stays the same.
- `responseModalities` must be `["AUDIO"]`. `["TEXT"]` is rejected with error 1007.
- Voices include `Puck`, `Charon`, `Kore`, `Fenrir`, `Aoede`, `Leda`, `Orus` and `Zephyr`. Leave out `speechConfig` for the default voice.
- The two empty `...AudioTranscription` objects switch on text transcripts of what you said and what the model said. They're optional but very useful.

### Extended thinking: 3.8 Live Extended Thinking

```json
{
  "setup": {
    "model": "models/gemini-3.8-live-extended-thinking",
    "generationConfig": {
      "responseModalities": ["AUDIO"],
      "thinkingConfig": { "thinkingLevel": "LOW" }
    },
    "outputAudioTranscription": {}
  }
}
```

- `thinkingLevel` is **required**: `MINIMAL`, `LOW`, `MEDIUM` or `HIGH`. Without it you get `Thinking level must be specified for this model`.
- It uses far more tokens than the other models: about 3,000 for a question that cost the others 400 to 600.

### Translation: 3.5 Live Translate

```json
{
  "setup": {
    "model": "models/gemini-3.5-live-translate-preview",
    "generationConfig": {
      "responseModalities": ["AUDIO"],
      "translationConfig": { "targetLanguageCode": "fr" }
    },
    "inputAudioTranscription": {},
    "outputAudioTranscription": {}
  }
}
```

- `translationConfig` goes **inside** `generationConfig`. At the top level of `setup` it is rejected with `Unknown name "translationConfig"`.
- `targetLanguageCode` is a BCP-47 code such as `en`, `es`, `fr`, `de`, `hi`, `ur`, `ar`, `zh` or `ja`.
- It only reacts to **speech**. Text input gets no reply.

### Transcription: 3.5 Transcribe Live

```json
{
  "setup": {
    "model": "models/gemini-3.5-transcribe-live",
    "generationConfig": { "responseModalities": ["TEXT"] },
    "inputAudioTranscription": { "mode": "SMART" }
  }
}
```

- `responseModalities` must be `["TEXT"]`. `["AUDIO"]` is rejected.
- `mode` is `VERBATIM` (the default: every word, fillers included) or `SMART` (removes fillers and false starts and adds formatting).
- The text arrives in `inputTranscription`, not in `modelTurn`, because it is a transcript of *your* audio.
- It only reacts to **speech**.

---

## 6. Sending input

**Text** (chat models only):

```json
{ "realtimeInput": { "text": "What is the capital of France?" } }
```

**Audio.** Send it as many small chunks; about 100 ms each works well.

```json
{
  "realtimeInput": {
    "audio": {
      "data": "<base64 of raw PCM bytes>",
      "mimeType": "audio/pcm;rate=16000"
    }
  }
}
```

| | Format |
|---|---|
| Audio you send | Raw PCM, 16-bit signed little-endian, mono, **16 kHz** |
| Audio you receive | Raw PCM, 16-bit signed little-endian, mono, **24 kHz** |

There is no WAV header, only raw samples. The server detects when you stop talking, so you don't need to send an "end of turn" message.

---

## 7. What the server sends back

Everything arrives as JSON. The useful parts:

| Field | Meaning |
|---|---|
| `setupComplete` | Setup accepted; start sending input |
| `serverContent.modelTurn.parts[].inlineData` | A chunk of reply audio: base64 PCM, `mimeType: "audio/pcm;rate=24000"` |
| `serverContent.modelTurn.parts[].text` | Text. With `"thought": true` it is the model's reasoning (2.5 Native Audio only) |
| `serverContent.inputTranscription.text` | Transcript of what you said, a piece at a time |
| `serverContent.interimInputTranscription` | Rough, still-changing transcript (Transcribe model) |
| `serverContent.outputTranscription.text` | Transcript of what the model said, a piece at a time |
| `serverContent.interrupted` | You spoke over the model. Stop playing its queued audio |
| `serverContent.turnComplete` | The model finished its reply |
| `usageMetadata.totalTokenCount` | Tokens used so far |
| `voiceActivity` | Server-side speech start/end detection |
| `sessionResumptionUpdate` | A handle for resuming the session later (safe to ignore) |
| `goAway` | The server will close the connection soon |

Example audio message, shortened:

```json
{
  "serverContent": {
    "modelTurn": {
      "parts": [{ "inlineData": { "mimeType": "audio/pcm;rate=24000", "data": "AAABAP7/..." } }]
    }
  }
}
```

---

## 8. Trying it from a terminal

### Option A: the Python script in this repo (tested)

[live_raw_example.py](live_raw_example.py) uses only the JSON above and the `websockets` library, with no Google SDK. It sends a text question, prints the transcript and saves the spoken reply to `reply.wav`.

```bash
python live_raw_example.py "What is the capital of France?"
```

```
{'setupComplete': {}}
The capital of France is Paris.
Saved 2.2s of audio to reply.wav
```

Change the `SETUP` block to any example from section 5 to try another model. Translate and Transcribe need audio rather than text; see [live_voice_test.py](live_voice_test.py) for microphone streaming.

### Option B: websocat (not tested on this machine)

[websocat](https://github.com/vi/websocat) is like curl for WebSockets: it connects, sends each line you type as a message, and prints what comes back. Install it with `scoop install websocat` (Windows), `brew install websocat` (macOS) or `cargo install websocat`.

```bash
websocat "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=$GEMINI_API_KEY"
```

Then paste each message **on one line**:

```
{"setup":{"model":"models/gemini-3.8-live","generationConfig":{"responseModalities":["AUDIO"]},"outputAudioTranscription":{}}}
{"realtimeInput":{"text":"Tell me a one-line joke."}}
```

Look for `outputTranscription` in the output to read the reply. The audio chunks are long base64 strings, so this is only useful for checking that a setup is accepted.

### Option C: the Live Studio UI

For talking to every model with your microphone, run `python live_studio/server.py` and open <http://localhost:8000>.

---

## 9. Gotchas

| Symptom | Cause and fix |
|---|---|
| `1007 ... response modalities (TEXT) is not supported` | Chat models only output `AUDIO`. Use `outputAudioTranscription` to get text. |
| `1007 ... response modalities (AUDIO) is not supported` | Transcribe Live only outputs `TEXT`. |
| `1007 Thinking level must be specified` | Extended Thinking needs `generationConfig.thinkingConfig.thinkingLevel`. |
| `Unknown name "translationConfig" at 'setup'` | Move it inside `generationConfig`. |
| Translate or Transcribe never replies | They ignore text. Send audio. |
| Translate or Transcribe never sends `turnComplete` | Expected: they stream continuously. Read messages until you close the connection. |
| Extended Thinking says "Let me calculate that…" and stops | In testing it sent a short filler reply ending in `turnComplete`. Don't close the connection on the first `turnComplete`; keep reading in case the real answer follows. |
| Reply audio plays at the wrong speed | Play it at **24 kHz**. Your mic input must be **16 kHz**. |
| The model keeps interrupting itself | It hears its own voice through your speakers. Use headphones, or echo cancellation in the browser. |
| `No API key was provided` from Python | `load_dotenv()` looks next to the running script. Run from the project folder or pass the path: `load_dotenv("path/to/.env")`. |
