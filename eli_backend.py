from flask import Flask, request, jsonify
from flask_cors import CORS
import whisper
import random
import os
import traceback

app = Flask(__name__)
CORS(app)

# 🧠 Historial en memoria
historial = []

# 🎯 Preguntas que Eli puede hacer
def generar_pregunta():
    preguntas = [
        "What do you like to do on weekends?",
        "Do you have any pets?",
        "What’s your favorite food?",
        "Where would you like to travel?",
        "What do you usually eat for breakfast?",
        "What kind of music do you enjoy?"
    ]
    return random.choice(preguntas)

@app.route("/conversar_audio", methods=["POST"])
def conversar_audio():
    audio = request.files.get("audio")
    if not audio:
        return jsonify({"error": "No se recibió archivo de audio"}), 400

    ruta_audio = "temp.wav"
    audio.save(ruta_audio)

    try:
        modelo_whisper = whisper.load_model("tiny")  # ✅ Ligero para Render Free
        resultado = modelo_whisper.transcribe(ruta_audio)
        texto_usuario = resultado.get("text", "").strip().lower()
        print(f"🗣️ Transcripción: {texto_usuario}")

        if not texto_usuario:
            raise ValueError("Transcripción vacía")

    except Exception as e:
        print(f"❌ Error al transcribir: {e}")
        traceback.print_exc()
        return jsonify({"error": "Error al procesar el audio"}), 500
    finally:
        if os.path.exists(ruta_audio):
            os.remove(ruta_audio)

    # ✅ Respuesta libre sin comparación
    if texto_usuario:
        retro = None
        respuesta = f"Thanks for sharing! {generar_pregunta()}"
    else:
        retro = "I couldn't hear anything. Try speaking a bit louder or longer."
        respuesta = "Let's try again. Say anything you'd like!"

    historial.append({
        "usuario": texto_usuario,
        "eli": respuesta,
        "retroalimentacion": retro
    })

    return jsonify({
        "respuesta": respuesta,
        "retroalimentacion": retro,
        "historial": historial
    })

@app.route("/")
def index():
    return "✅ Eli está vivo y escuchando 👂", 200

print("✅ Eli backend cargado correctamente")