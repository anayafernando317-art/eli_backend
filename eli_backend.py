from flask import Flask, request, jsonify
from flask_cors import CORS
import language_tool_python
import requests
import random

app = Flask(__name__)
CORS(app)

tool = language_tool_python.LanguageTool('es')
historial = []

# Traducción al inglés usando LibreTranslate
def traducir_al_ingles(texto):
    url = "https://libretranslate.de/translate"
    payload = {
        "q": texto,
        "source": "es",
        "target": "en",
        "format": "text"
    }
    response = requests.post(url, json=payload)
    return response.json()["translatedText"]

# Corrección gramatical con explicación
def analizar_errores(frase):
    matches = tool.check(frase)
    errores = []
    for m in matches:
        if m.ruleIssueType in ['grammar', 'misspelling']:
            errores.append({
                "mensaje": m.message,
                "original": frase[m.offset:m.offset + m.errorLength],
                "sugerencia": m.replacements[0] if m.replacements else ""
            })
    return errores

# Preguntas naturales para mantener la conversación
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

@app.route("/")
def home():
    return "Eli está en línea. Usa /conversar para enviar frases."

@app.route("/conversar", methods=["POST"])
def conversar():
    data = request.get_json()
    frase_usuario = data.get("frase_usuario", "")
    
    errores = analizar_errores(frase_usuario)

    if errores:
        # Corrige y explica el error
        error = errores[0]
        respuesta = (
            f"Let's fix that: '{error['original']}' should be '{error['sugerencia']}'. "
            f"{error['mensaje']}"
        )
        historial.append({"usuario": frase_usuario, "eli": respuesta})
        return jsonify({
            "respuesta": respuesta,
            "repetir": True,
            "historial": historial
        })
    else:
        # Traduce y continúa la conversación con una pregunta
        traduccion = traducir_al_ingles(frase_usuario)
        pregunta = generar_pregunta()
        respuesta = f"{traduccion}. {pregunta}"
        historial.append({"usuario": frase_usuario, "eli": respuesta})
        return jsonify({
            "respuesta": respuesta,
            "repetir": False,
            "historial": historial
        })

if __name__ == "__main__":
    app.run()