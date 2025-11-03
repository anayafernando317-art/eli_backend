from flask import Flask, request, jsonify
from flask_cors import CORS
import whisper
import random
import os
import traceback
import subprocess

app = Flask(__name__)
CORS(app)

historial = []

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

def convertir_a_wav(input_path, output_path):
    comando = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ac", "1",
        "-ar", "16000",
        "-sample_fmt", "s16",
        output_path
    ]
    subprocess.run(comando, check=True)

@app.route("/conversar_audio", methods=["POST"])
def conversar_audio():
    audio = request.files.get("audio")
    if not audio:
        return jsonify({"error": "No se recibió archivo de audio"}), 400

    original_path = "temp_original.aac"
    wav_path = "temp.wav"

    try:
        audio.save(original_path)

        if os.path.getsize(original_path) < 1000:
            raise ValueError("Archivo demasiado pequeño para transcribir")

        convertir_a_wav(original_path, wav_path)

        modelo_whisper = whisper.load_model("tiny")
        resultado = modelo_whisper.transcribe(wav_path)
        texto_usuario = resultado.get("text", "").strip().lower()
        print(f"🗣️ Transcripción: {texto_usuario}")

        if not texto_usuario:
            raise ValueError("Transcripción vacía")

    except Exception as e:
        print(f"❌ Error al transcribir: {e}")
        traceback.print_exc()
        return jsonify({"error": "Error al procesar el audio"}), 500
    finally:
        for path in [original_path, wav_path]:
            if os.path.exists(path):
                os.remove(path)

    respuesta = f"Thanks for sharing! {generar_pregunta()}"
    historial.append({
        "usuario": texto_usuario,
        "eli": respuesta,
        "retroalimentacion": None
    })

    return jsonify({
        "respuesta": respuesta,
        "retroalimentacion": None,
        "transcripcion": texto_usuario,
        "historial": historial
    })

@app.route("/")
def index():
    return "✅ Eli está vivo y escuchando 👂", 200

print("✅ Eli backend cargado correctamente")