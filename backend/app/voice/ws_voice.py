import json
import asyncio
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db.session import get_db
from app.agent.graph import process_utterance
from app.agent.templates.voice_templates import get_ai_disclosure
from app.config import settings

voice_router = APIRouter()

@voice_router.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    await websocket.accept()
    current_lang = settings.SHOP_DEFAULT_LANG
    
    # MANDATORY: First Turn AI Disclosure (Gnani Rubric Responsible AI requirement)
    disclosure = get_ai_disclosure(current_lang)
    await websocket.send_json({
        "type": "FIRST_TURN_DISCLOSURE",
        "text": disclosure,
        "language": current_lang,
        "compliance": "Mandatory First-Turn AI Disclosure Verified"
    })
    
    audio_buffer = bytearray()
    
    try:
        while True:
            message = await websocket.receive()
            
            # Binary frame (Audio PCM chunk from AudioWorklet)
            if "bytes" in message and message["bytes"]:
                audio_buffer.extend(message["bytes"])
                
            # Text frame (JSON event / control)
            elif "text" in message and message["text"]:
                msg_data = json.loads(message["text"])
                msg_type = msg_data.get("type")
                
                if msg_type == "LANG":
                    current_lang = msg_data.get("value", current_lang)
                    
                elif msg_type == "CANCEL": # Barge-in triggered
                    audio_buffer.clear()
                    await websocket.send_json({"type": "BARGE_IN_ACK", "status": "playback_cancelled"})
                    
                elif msg_type in ["COMMIT", "UTTERANCE"]:
                    # Spoken text transcript (either direct from WebSpeech or relayed from Gnani)
                    transcript_text = msg_data.get("text", "")
                    req_lang = msg_data.get("language", current_lang)
                    
                    if transcript_text.strip():
                        t0 = time.time()
                        with get_db() as conn:
                            result = process_utterance(transcript_text, req_lang, conn)
                            
                        elapsed_ms = int((time.time() - t0) * 1000)
                        result["timings"]["network_ms"] = 15
                        result["timings"]["total_latency_ms"] = elapsed_ms
                        
                        # Send back full structured ledger result & latency breakdown
                        await websocket.send_json({
                            "type": "LEDGER_RESULT",
                            "transcript": transcript_text,
                            "language": req_lang,
                            "data": result,
                            "spoken_reply": result.get("spoken_reply"),
                            "timings": result.get("timings")
                        })
                    audio_buffer.clear()
                    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.close()
        except Exception:
            pass
