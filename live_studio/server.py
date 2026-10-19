"""Live Studio - a browser UI for trying every Gemini Live API model with your voice.

Run:  python live_studio/server.py
Open: http://localhost:8000

The browser captures your mic and plays audio; this server holds the API key and
relays everything to the Live API, so the key never reaches the browser.
"""

import asyncio
import json

from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from google import genai
from google.genai import types

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")

client = genai.Client()
app = FastAPI()

# kind decides which config is built and which settings the UI shows
MODELS = [
    {
        "id": "gemini-2.5-flash-native-audio-latest",
        "label": "Gemini 2.5 Flash Native Audio",
        "kind": "chat",
        "blurb": "Native-audio dialog. Expressive voice, shares its thinking.",
    },
    {
        "id": "gemini-3.1-flash-live-preview",
        "label": "Gemini 3 Flash Live",
        "kind": "chat",
        "blurb": "Fast, low-latency voice conversation.",
    },
    {
        "id": "gemini-3.8-live",
        "label": "Gemini 3.8 Live",
        "kind": "chat",
        "blurb": "Newest general-purpose live voice model.",
    },
    {
        "id": "gemini-3.8-live-extended-thinking",
        "label": "Gemini 3.8 Live Extended Thinking",
        "kind": "thinking",
        "blurb": "Reasons before it answers. Pick how hard it thinks.",
    },
    {
        "id": "gemini-3.5-live-translate-preview",
        "label": "Gemini 3.5 Live Translate",
        "kind": "translate",
        "blurb": "Speak any language, hear it back translated.",
    },
    {
        "id": "gemini-3.5-transcribe-live",
        "label": "Gemini 3.5 Transcribe Live",
        "kind": "transcribe",
        "blurb": "Speech to text only. No voice replies.",
    },
]
MODELS_BY_ID = {m["id"]: m for m in MODELS}


def build_config(opts: dict) -> types.LiveConnectConfig:
    kind = MODELS_BY_ID[opts["model"]]["kind"]
    transcription = types.AudioTranscriptionConfig()

    if kind == "transcribe":
        return types.LiveConnectConfig(
            response_modalities=["TEXT"],
            input_audio_transcription=types.AudioTranscriptionConfig(
                mode=opts.get("transcribe_mode") or "VERBATIM"
            ),
        )

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        input_audio_transcription=transcription,
        output_audio_transcription=transcription,
    )

    if kind == "translate":
        config.translation_config = types.TranslationConfig(
            target_language_code=opts.get("target_language") or "es"
        )
        return config

    if opts.get("system_instruction"):
        config.system_instruction = opts["system_instruction"]
    if opts.get("voice"):
        config.speech_config = types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=opts["voice"])
            )
        )
    if kind == "thinking":
        config.thinking_config = types.ThinkingConfig(
            thinking_level=opts.get("thinking_level") or "LOW", include_thoughts=True
        )
    return config


@app.get("/")
async def index():
    return FileResponse(HERE / "index.html")


@app.get("/api/models")
async def models():
    return MODELS


@app.websocket("/ws")
async def live(ws: WebSocket):
    await ws.accept()
    opts = await ws.receive_json()

    try:
        async with client.aio.live.connect(model=opts["model"], config=build_config(opts)) as session:
            await ws.send_json({"type": "ready"})

            async def browser_to_gemini():
                while True:
                    msg = await ws.receive()
                    if msg["type"] == "websocket.disconnect":
                        return
                    if msg.get("bytes"):
                        await session.send_realtime_input(
                            audio=types.Blob(data=msg["bytes"], mime_type="audio/pcm;rate=16000")
                        )
                    elif msg.get("text"):
                        data = json.loads(msg["text"])
                        if data.get("type") == "text" and data.get("text"):
                            await session.send_realtime_input(text=data["text"])

            async def gemini_to_browser():
                while True:
                    async for r in session.receive():
                        if r.usage_metadata and r.usage_metadata.total_token_count:
                            await ws.send_json({"type": "usage", "total": r.usage_metadata.total_token_count})
                        if r.go_away:
                            await ws.send_json({"type": "info", "text": f"Server will close the session in {r.go_away.time_left}"})

                        sc = r.server_content
                        if sc is None:
                            continue
                        if sc.model_turn:
                            for part in sc.model_turn.parts:
                                if part.inline_data and part.inline_data.data:
                                    await ws.send_bytes(part.inline_data.data)
                                elif part.text:
                                    await ws.send_json({"type": "thought" if part.thought else "text", "text": part.text})
                        if sc.input_transcription and sc.input_transcription.text:
                            await ws.send_json({"type": "input", "text": sc.input_transcription.text})
                        if sc.output_transcription and sc.output_transcription.text:
                            await ws.send_json({"type": "output", "text": sc.output_transcription.text})
                        if sc.interrupted:
                            await ws.send_json({"type": "interrupted"})
                        if sc.turn_complete:
                            await ws.send_json({"type": "turn_complete"})

            tasks = [asyncio.create_task(browser_to_gemini()), asyncio.create_task(gemini_to_browser())]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
            for t in done:
                t.result()  # surface errors from whichever side ended first
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "text": str(e)})
            await ws.close()
        except Exception:
            pass


if __name__ == "__main__":
  
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
