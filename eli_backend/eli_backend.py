from flask import Flask, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/conversar', methods=['POST'])
def conversar():
    data = request.get_json()
    frase_usuario = data.get('frase_usuario', '')

    if not frase_usuario.strip():
        return jsonify({
            "estado": "error",
            "retroalimentacion": "No recibí ninguna frase. ¿Puedes intentarlo de nuevo?"
        }), 400

    # Llamada a la API de LanguageTool
    try:
        lt_response = requests.post(
            'https://api.languagetoolplus.com/v2/check',
            data={
                'text': frase_usuario,
                'language': 'es'
            }
        )
        result = lt_response.json()
        errores = result.get('matches', [])

        if errores:
            primer_error = errores[0]
            mensaje = primer_error['message']
            sugerencia = primer_error['replacements'][0] if primer_error['replacements'] else "Revisa la estructura"

            return jsonify({
                "estado": "incorrecta",
                "correccion": sugerencia,
                "invitacion_a_repetir": f"Por favor, intenta decirlo así: '{sugerencia}'",
                "retroalimentacion": f"{mensaje}. ¿Puedes repetirlo en voz alta?"
            })

        else:
            return jsonify({
                "estado": "correcta",
                "retroalimentacion": "¡Muy bien! Tu frase está correctamente estructurada."
            })

    except Exception as e:
        return jsonify({
            "estado": "error",
            "retroalimentacion": f"Ocurrió un error al analizar tu frase: {str(e)}"
        }), 500

@app.route('/')
def home():
    return "Eli está en línea. Usa /conversar para enviar frases.", 200