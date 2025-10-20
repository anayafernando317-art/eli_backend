from flask import Flask, request, jsonify
# import language_tool_python

app = Flask(__name__)
#tool = language_tool_python.LanguageTool('en-US')

# Diccionario de respuestas por palabra clave
respuestas_contextuales = {
    "beach": "Do you like swimming or just relaxing?",
    "school": "What subject do you enjoy the most?",
    "iguana": "Wow! Did you take a picture of the iguana?",
    "acapulco": "Acapulco is beautiful. Did you visit La Quebrada?",
    "food": "Yum! What kind of food do you like?",
    "music": "Nice! What kind of music do you listen to?",
    "travel": "Traveling is amazing. Where would you like to go next?",
    "done": "Great job today! Your English is improving. Keep practicing!",
    "thanks": "You're welcome! I'm here whenever you want to practice."
}

# Función para detectar errores gramaticales
def detectar_errores(frase_usuario):
   # errores = tool.check(frase_usuario)
    #if errores:
     #   mensaje = errores[0].message
      #  sugerencia = errores[0].replacements[0] if errores[0].replacements else "Revisa la estructura"
       # return {
        #    "estado": "incorrecta",
         #  "correccion": sugerencia,
          #  "invitacion_a_repetir": f"Por favor, intenta decirlo así: '{sugerencia}'",
          
          #  "retroalimentacion": f"{mensaje}. ¿Puedes repetirlo en voz alta?"
  #      }
    #else:
     #   return {
      #      "estado": "correcta",
       #     "retroalimentacion": "¡Muy bien! Tu frase está correctamente estructurada."
        #}
    return {
    "estado": "correcta",
    "retroalimentacion": "¡Gracias! Eli recibió tu frase. Pronto te dará retroalimentación más precisa."
        }

# Función para generar respuesta contextual
def generar_respuesta(frase_usuario):
    frase_lower = frase_usuario.lower()
    for palabra, respuesta in respuestas_contextuales.items():
        if palabra in frase_lower:
            return respuesta
    return "Interesting! Tell me more."

# Endpoint principal
@app.route('/conversar', methods=['POST'])
def conversar():
    data = request.json
    frase = data.get('frase')

    resultado = detectar_errores(frase)
    respuesta_contextual = generar_respuesta(frase)

    resultado["respuesta_contextual"] = respuesta_contextual
    return jsonify(resultado)

if __name__ == '__main__':
    app.run(debug=True)