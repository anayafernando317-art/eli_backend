from flask import Flask, request, jsonify
from flask_cors import CORS
import whisper
from difflib import SequenceMatcher
import random
import os

app = Flask(__name__)
CORS(app)

# 🔊 Carga el modelo Whisper
modelo_whisper = whisper.load_model("base")

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

# 🗣️ Frase esperada para comparar
frase_esperada = "hello how are you"

@app.route("/conversar_audio", methods=["POST"])
def conversar_audio():
    audio = request.files.get("audio")
    if not audio:
        return jsonify({"error": "No se recibió archivo de audio"}), 400

    ruta_audio = "temp.wav"
    audio.save(ruta_audio)

    try:
        resultado = modelo_whisper.transcribe(ruta_audio)
        texto_usuario = resultado["text"].lower()
        print(f"🗣️ Transcripción: {texto_usuario}")
    except Exception as e:
        print(f"❌ Error al transcribir: {e}")
        return jsonify({"error": "Error al procesar el audio"}), 500
    finally:
        if os.path.exists(ruta_audio):
            os.remove(ruta_audio)

    similitud = SequenceMatcher(None, frase_esperada, texto_usuario).ratio()
    print(f"📊 Similitud: {similitud:.2f}")

    if similitud < 0.8:
        retro = f"It sounded like '{texto_usuario}'. Try saying: {frase_esperada}"
        respuesta = f"{retro} Let's try again: {frase_esperada}"
    else:
        retro = None
        respuesta = f"Great! {generar_pregunta()}"

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