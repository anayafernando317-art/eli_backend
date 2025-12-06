import os
import sys
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import speech_recognition as sr
import random
import traceback
from pydub import AudioSegment
import io
import uuid
import time
from datetime import datetime, timedelta
import json
import re

# ============================================
# CONFIGURACIÓN INICIAL
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

print("=" * 60)
print("🚀 Eli English Tutor - Backend COMPLETO v8.0")
print("🎯 Con juegos, scaffolding, español TODO")
print("=" * 60)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'eli-secret-key-' + str(uuid.uuid4())[:8])
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    AUDIO_FILE_MAX_SIZE = 5 * 1024 * 1024

app = Flask(__name__)
app.config.from_object(Config)

CORS(app, resources={
    r"/api/*": {
        "origins": ["*", "https://*.onrender.com", "http://localhost:*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-User-ID", "X-Session-ID"]
    }
})

# ============================================
# SISTEMA DE SESIONES
# ============================================
class UserSession:
    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self.current_level = "beginner"
        self.conversation_history = []
        self.game_stats = {
            "total_points": 0,
            "games_played": 0,
            "correct_answers": 0,
            "total_attempts": 0,
            "vocabulary_games": 0,
            "pronunciation_games": 0
        }
        self.xp = 0
        self.level = 1
        self.created_at = datetime.now()
        self.last_interaction = datetime.now()
        self.pronunciation_scores = []
        self.game_history = []
        self.current_question = "Tell me about yourself"
        self.current_topic = "general"
        self.needs_scaffolding = False
    
    def add_conversation(self, user_text: str, eli_response: str, score: float):
        self.conversation_history.append({
            "user": user_text[:100],
            "eli": eli_response[:500],
            "score": score,
            "timestamp": datetime.now().isoformat()
        })
        self.pronunciation_scores.append(score)
        
        if len(self.conversation_history) > 20:
            self.conversation_history.pop(0)
        if len(self.pronunciation_scores) > 10:
            self.pronunciation_scores.pop(0)
    
    def add_game_result(self, game_type: str, correct: bool, points: int):
        self.game_history.append({
            "game_type": game_type,
            "correct": correct,
            "points": points,
            "timestamp": datetime.now().isoformat()
        })
        
        self.game_stats["games_played"] += 1
        self.game_stats["total_points"] += points
        
        if game_type == "vocabulary":
            self.game_stats["vocabulary_games"] += 1
        elif game_type == "pronunciation":
            self.game_stats["pronunciation_games"] += 1
        
        if correct:
            self.game_stats["correct_answers"] += 1
            self.xp += points
        
        self.game_stats["total_attempts"] += 1
        
        if len(self.game_history) > 50:
            self.game_history.pop(0)
    
    def update_level(self):
        if not self.pronunciation_scores:
            return
        
        avg_score = sum(self.pronunciation_scores) / len(self.pronunciation_scores)
        
        if avg_score >= 80:
            self.current_level = "advanced"
        elif avg_score >= 60:
            self.current_level = "intermediate"
        else:
            self.current_level = "beginner"
    
    def to_dict(self):
        avg_score = sum(self.pronunciation_scores) / len(self.pronunciation_scores) if self.pronunciation_scores else 0
        
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "current_level": self.current_level,
            "xp": self.xp,
            "level": self.level,
            "game_stats": self.game_stats,
            "conversation_count": len(self.conversation_history),
            "avg_pronunciation_score": round(avg_score, 1),
            "game_history_count": len(self.game_history),
            "current_question": self.current_question,
            "current_topic": self.current_topic,
            "needs_scaffolding": self.needs_scaffolding,
            "last_interaction": self.last_interaction.isoformat()
        }

class SessionManager:
    def __init__(self):
        self.sessions = {}
    
    def create_session(self, user_id: str):
        session_id = f"{user_id[:6]}_{int(time.time())}"
        session = UserSession(user_id, session_id)
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str):
        session = self.sessions.get(session_id)
        if session:
            session.last_interaction = datetime.now()
        return session

session_manager = SessionManager()

# ============================================
# SISTEMA COACH COMPLETO (TODO EN UNO)
# ============================================
class SistemaCoachCompleto:
    def __init__(self):
        # Palabras clave para detección
        self.help_keywords_english = [
            'help', 'i dont know', "i don't know", 'what should i say',
            'how do i say', 'i cant', "i can't", "i'm not sure",
            'i need help', "i don't understand", 'what do i say',
            'i need assistance', 'can you help', 'no idea', 'not sure',
            'tell me what to say', 'give me an example'
        ]
        
        self.help_keywords_spanish = [
            'ayuda', 'no sé', 'no se', 'qué digo', 'cómo se dice',
            'qué puedo decir', 'no entiendo', 'no puedo',
            'ayúdame', 'no sé qué decir', 'qué debo decir',
            'dime qué decir', 'dame un ejemplo', 'no tengo idea'
        ]
        
        # Detección de español
        self.spanish_indicators = [
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
            'y', 'o', 'pero', 'porque', 'cuando', 'donde', 'que',
            'con', 'de', 'en', 'para', 'por', 'sin', 'sobre',
            'hola', 'gracias', 'por favor', 'adiós', 'buenos',
            'días', 'tardes', 'noches', 'perdón', 'siento'
        ]
        
        # Scaffolding templates (MANTENIDOS de tu código original)
        self.scaffolding_templates = {
            "beginner": [
                "My name is ______ and I like ______.",
                "I am from ______ and I study ______.",
                "Today is ______ and I feel ______.",
                "I have ______ and my favorite ______ is ______.",
                "I like to ______ because it is ______."
            ],
            "intermediate": [
                "On weekends, I usually ______ because ______.",
                "My favorite hobby is ______ since ______.",
                "Recently, I have been ______ which makes me feel ______.",
                "Although ______, I still ______ because ______.",
                "When I have free time, I enjoy ______ as it helps me ______."
            ],
            "advanced": [
                "From my perspective, ______ demonstrates that ______.",
                "The implications of ______ suggest that ______.",
                "Despite ______, it is evident that ______ consequently ______.",
                "Throughout my experience, I have learned that ______ therefore ______.",
                "Considering ______, one can observe that ______ which leads to ______."
            ]
        }
        
        # Vocabulario por tema (MANTENIDO)
        self.topic_vocabulary = {
            "daily routine": ["wake up", "get dressed", "have breakfast", "go to school", 
                            "study", "have lunch", "do homework", "relax", "go to bed"],
            "family": ["parents", "siblings", "grandparents", "relatives", "close",
                      "supportive", "loving", "spend time", "traditions"],
            "hobbies": ["reading", "sports", "music", "drawing", "cooking",
                       "gaming", "watching movies", "collecting", "photography"],
            "food": ["breakfast", "lunch", "dinner", "snacks", "healthy",
                    "delicious", "restaurant", "cook", "recipe", "favorite"]
        }
    
    def detectar_idioma(self, texto: str) -> dict:
        """Detectar idioma del texto"""
        if not texto:
            return {"language": "unknown", "is_spanish": False, "needs_help": False}
        
        texto_lower = texto.lower()
        words = re.findall(r'\b\w+\b', texto_lower)
        
        # Detectar español
        spanish_count = sum(1 for word in words if word in self.spanish_indicators)
        english_words = ['the', 'and', 'but', 'because', 'when', 'where', 'how', 'what', 'why']
        english_count = sum(1 for word in words if word in english_words)
        
        # Detectar ayuda
        help_spanish = any(keyword in texto_lower for keyword in self.help_keywords_spanish)
        help_english = any(keyword in texto_lower for keyword in self.help_keywords_english)
        
        is_spanish = spanish_count > english_count or help_spanish
        
        return {
            "language": "es" if is_spanish else "en",
            "is_spanish": is_spanish,
            "is_english": not is_spanish,
            "needs_help": help_spanish or help_english,
            "help_type": "spanish" if help_spanish else "english" if help_english else None
        }
    
    def analizar_pronunciacion(self, texto: str, duracion: float) -> dict:
        """Análisis de pronunciación (MANTENIDO de tu código)"""
        if not texto:
            return {
                'score': 0,
                'problem_words': [],
                'tips': ["Try speaking for at least 2 seconds"],
                'detected_level': "beginner",
                'word_count': 0,
                'duration': duracion
            }
        
        palabras = texto.lower().split()
        nivel = self.detectar_nivel_usuario(texto, duracion)
        
        problem_patterns = {
            'the': 'ðə (tongue between teeth)',
            'think': 'θɪŋk (soft "th")',
            'this': 'ðɪs (vibrating "th")',
            'very': 'vɛri (bite lower lip)',
            'water': 'wɔːtər (pronounce the "t")'
        }
        
        problem_words = []
        for palabra in palabras[:5]:
            clean = re.sub(r'[^\w]', '', palabra)
            if clean in problem_patterns:
                problem_words.append({
                    'word': clean,
                    'explanation': problem_patterns[clean]
                })
        
        score = 65.0
        
        if duracion >= 2.0:
            score += 10
        if len(palabras) >= 5:
            score += 5
        
        if problem_words:
            score -= len(problem_words) * 5
        
        if nivel == "intermediate":
            score += 5
        elif nivel == "advanced":
            score += 10
        
        score = max(30.0, min(98.0, score))
        
        tips = []
        if nivel == "beginner":
            if len(palabras) < 3:
                tips.append("Try to form longer sentences (minimum 3 words)")
            if duracion < 1.5:
                tips.append("Speak for at least 2 seconds to practice rhythm")
        
        elif nivel == "intermediate":
            if not problem_words and len(palabras) > 5:
                tips.append("Great! Now try using connecting words")
        
        if problem_words:
            tips.append(f"Practice: {', '.join(pw['word'] for pw in problem_words[:2])}")
        
        return {
            'score': round(score, 1),
            'problem_words': problem_words[:2],
            'tips': tips[:3],
            'detected_level': nivel,
            'word_count': len(palabras),
            'duration': round(duracion, 1)
        }
    
    def detectar_nivel_usuario(self, texto: str, duracion_audio: float) -> str:
        """Detectar nivel del usuario (MANTENIDO)"""
        if not texto or len(texto.strip()) < 3:
            return "beginner"
        
        palabras = texto.split()
        word_count = len(palabras)
        
        advanced_words = {'although', 'however', 'therefore', 'furthermore', 
                         'meanwhile', 'consequently', 'nevertheless'}
        
        advanced_count = sum(1 for word in palabras if word.lower() in advanced_words)
        
        score = 0
        if word_count > 10: score += 3
        elif word_count > 5: score += 2
        elif word_count > 2: score += 1
        
        score += advanced_count * 2
        
        if score >= 6: return "advanced"
        elif score >= 3: return "intermediate"
        return "beginner"
    
    def generar_respuesta_spanish(self, texto_espanol: str) -> dict:
        """Respuesta cuando hablan en español"""
        # Traducciones básicas
        translations = {
            'hola': 'hello',
            'no sé': "I don't know",
            'ayuda': 'help',
            'cómo se dice': 'how do you say',
            'qué digo': 'what should I say',
            'me llamo': 'my name is',
            'soy de': 'I am from',
            'tengo': 'I have',
            'me gusta': 'I like',
            'no entiendo': "I don't understand"
        }
        
        # Buscar traducciones
        translated = []
        for esp, eng in translations.items():
            if esp in texto_espanol.lower():
                translated.append(eng)
        
        english_version = " ".join(translated) if translated else "I need help with English"
        
        response = f"""🌐 **¡Noté que hablaste en español! ¡Excelente!**

🇪🇸 **En español dijiste:** "{texto_espanol}"
🇺🇸 **En inglés sería:** "{english_version}"

🎯 **Ahora intenta decirlo en inglés:**
1. Escucha la versión en inglés
2. Repite palabra por palabra
3. Enfócate en la pronunciación
4. Pon todo junto

💡 **Consejo:** No traduzcas palabra por palabra. ¡Piensa en el mensaje!

🔁 **Para practicar:** "{english_version}"

🌟 **Recuerda:** Cada vez que practicas en inglés, mejoras. ¡Tú puedes! 💪"""
        
        return {
            "type": "language_switch",
            "message": response,
            "pronunciation_score": 40,
            "detected_level": "beginner",
            "needs_scaffolding": True,
            "scaffolding_data": {
                "template": english_version,
                "examples": [english_version],
                "vocabulary": ["practice", "speak", "english", "slowly"],
                "topic": "translation_practice",
                "level": "beginner",
                "tips": ["Think in English, don't translate", "Speak slowly", "Focus on key words"]
            },
            "next_question": "Can you say that in English now?",
            "detected_language": "es",
            "xp_earned": 5
        }
    
    def generar_respuesta_normal(self, texto: str, analisis: dict, current_question: str) -> dict:
        """Generar respuesta normal en inglés"""
        motivational = {
            "beginner": "🎉 **Great effort!** You're making progress!",
            "intermediate": "🌟 **Well done!** Your English is improving!",
            "advanced": "💫 **Excellent!** Very impressive English!"
        }
        
        nivel = analisis['detected_level']
        
        response_parts = []
        response_parts.append(motivational.get(nivel, "🎉 Good job!"))
        response_parts.append(f"🗣️ **You said:** \"{texto}\"")
        response_parts.append(f"📊 **Pronunciation Score:** {analisis['score']}/100")
        
        if analisis['problem_words']:
            response_parts.append("\n🎯 **Focus on:**")
            for pw in analisis['problem_words']:
                response_parts.append(f"• **{pw['word']}**: {pw['explanation']}")
        
        if analisis['tips']:
            response_parts.append("\n💡 **Tips:**")
            for tip in analisis['tips']:
                response_parts.append(f"• {tip}")
        
        # Detectar tema para siguiente pregunta
        tema = self.detectar_tema(texto, current_question)
        next_q = self.generar_pregunta_siguiente(tema, nivel)
        
        response_parts.append(f"\n💬 **Next question:** {next_q}")
        
        # Scaffolding si es necesario
        needs_scaffolding = analisis['score'] < 60 or analisis['word_count'] < 3
        scaffolding_data = None
        
        if needs_scaffolding:
            scaffolding_data = self.generar_scaffolding_data(tema, nivel, current_question)
        
        return {
            "type": "conversation_response",
            "message": "\n".join(response_parts),
            "pronunciation_score": analisis['score'],
            "detected_level": nivel,
            "needs_scaffolding": needs_scaffolding,
            "scaffolding_data": scaffolding_data,
            "next_question": next_q,
            "detected_topic": tema,
            "detected_language": "en",
            "xp_earned": self.calcular_xp(analisis['score'], analisis['word_count'])
        }
    
    def generar_respuesta_ayuda(self, texto: str, es_spanish: bool, current_question: str) -> dict:
        """Generar respuesta de ayuda"""
        nivel = "beginner"
        tema = self.detectar_tema("", current_question)
        template = random.choice(self.scaffolding_templates[nivel])
        
        if es_spanish:
            message = f"""🆘 **¡Te ayudo a responder en inglés!**

❓ **Pregunta:** {current_question}

📝 **Usa esta estructura:**
"{template}"

🔤 **Vocabulario útil:**
name, like, from, have, enjoy, because

💡 **Ejemplo:**
"My name is Carlos and I like to practice English."

🎤 **¡Ahora inténtalo tú!**
1. Llena los espacios en blanco
2. Grábalo
3. Te daré retroalimentación

🌟 **Recuerda:** ¡Todos empezamos así! 💪"""
        else:
            message = f"""🆘 **I'll help you structure your answer!**

❓ **Question:** {current_question}

📝 **Use this structure:**
"{template}"

🔤 **Useful vocabulary:**
name, like, from, have, enjoy, because

💡 **Example:**
"My name is Alex and I enjoy learning new things."

🎤 **Now try:**
1. Fill in the blanks
2. Record your answer
3. I'll give you personalized feedback

🌟 **Remember:** It's okay to make mistakes. That's how we learn! 💪"""
        
        return {
            "type": "help_response",
            "message": message,
            "pronunciation_score": 0,
            "detected_level": nivel,
            "needs_scaffolding": True,
            "scaffolding_data": {
                "template": template,
                "examples": [f"My name is... and I {random.choice(['like', 'enjoy', 'love'])}..."],
                "vocabulary": ["name", "like", "from", "have", "enjoy", "because"],
                "topic": tema,
                "level": nivel,
                "tips": ["Speak slowly", "Use the vocabulary", "Add personal details"],
                "current_question": current_question
            },
            "next_question": current_question,  # ¡MANTENER misma pregunta!
            "detected_topic": tema,
            "detected_language": "es" if es_spanish else "en",
            "xp_earned": 10,
            "is_help_response": True
        }
    
    def detectar_tema(self, texto: str, current_question: str) -> str:
        """Detectar tema"""
        combined = (texto + " " + current_question).lower()
        
        if "family" in combined or "parents" in combined or "brother" in combined or "sister" in combined:
            return "family"
        elif "hobby" in combined or "free time" in combined or "like to do" in combined:
            return "hobbies"
        elif "food" in combined or "eat" in combined or "restaurant" in combined:
            return "food"
        elif "routine" in combined or "day" in combined or "morning" in combined:
            return "daily routine"
        elif "name" in combined and ("where" in combined or "from" in combined):
            return "introduction"
        else:
            return "general"
    
    def generar_pregunta_siguiente(self, tema: str, nivel: str) -> str:
        """Generar siguiente pregunta"""
        preguntas = {
            "family": {
                "beginner": "Do you have any brothers or sisters?",
                "intermediate": "What activities do you enjoy with your family?",
                "advanced": "How has your family influenced you?"
            },
            "hobbies": {
                "beginner": "What do you like to do in your free time?",
                "intermediate": "How did you get interested in your hobby?",
                "advanced": "How does your hobby contribute to your personal growth?"
            },
            "general": {
                "beginner": "What is your favorite color?",
                "intermediate": "Describe your hometown.",
                "advanced": "What are your future goals?"
            }
        }
        
        tema_preguntas = preguntas.get(tema, preguntas["general"])
        return tema_preguntas.get(nivel, tema_preguntas["beginner"])
    
    def generar_scaffolding_data(self, tema: str, nivel: str, current_question: str) -> dict:
        """Generar datos de scaffolding"""
        template = random.choice(self.scaffolding_templates.get(nivel, self.scaffolding_templates["beginner"]))
        vocab = self.topic_vocabulary.get(tema, ["words", "phrases", "sentences"])
        
        return {
            "template": template,
            "examples": [f"Example: {template.replace('______', 'something')}"],
            "vocabulary": vocab[:6],
            "topic": tema,
            "level": nivel,
            "tips": ["Speak clearly", "Take your time", "Focus on communication"],
            "current_question": current_question
        }
    
    def calcular_xp(self, score: float, word_count: int) -> int:
        """Calcular XP"""
        base_xp = 10
        score_bonus = int(score / 10)
        length_bonus = min(word_count, 10)
        return min(base_xp + score_bonus + length_bonus, 30)

coach = SistemaCoachCompleto()

# ============================================
# SISTEMA DE JUEGOS (COMPLETO - MANTENIDO)
# ============================================
class VocabularyGame:
    def __init__(self):
        # Categorías de vocabulario por nivel (MANTENIDO)
        self.categories = {
            "beginner": {
                "food": ["apple", "bread", "water", "rice", "milk", "egg", "meat", "fruit"],
                "family": ["mother", "father", "sister", "brother", "family", "home", "love"],
                "animals": ["dog", "cat", "bird", "fish", "horse", "cow", "rabbit"],
                "colors": ["red", "blue", "green", "yellow", "black", "white", "orange"],
                "numbers": ["one", "two", "three", "four", "five", "six", "seven", "eight"]
            },
            "intermediate": {
                "daily routine": ["wake up", "get dressed", "have breakfast", "go to work", "exercise", "relax"],
                "hobbies": ["reading", "sports", "music", "cooking", "painting", "dancing", "photography"],
                "travel": ["airport", "hotel", "passport", "suitcase", "ticket", "destination", "journey"],
                "school": ["teacher", "student", "classroom", "homework", "exam", "project", "knowledge"],
                "weather": ["sunny", "rainy", "cloudy", "windy", "storm", "temperature", "forecast"]
            },
            "advanced": {
                "technology": ["software", "hardware", "algorithm", "database", "network", "interface", "protocol"],
                "business": ["strategy", "management", "marketing", "finance", "investment", "entrepreneur"],
                "science": ["research", "experiment", "hypothesis", "analysis", "discovery", "innovation"],
                "politics": ["government", "democracy", "economy", "policy", "election", "diplomacy"],
                "education": ["pedagogy", "curriculum", "assessment", "literacy", "cognitive", "development"]
            }
        }
        
        # Frases completas para práctica (MANTENIDO)
        self.sentences = {
            "beginner": [
                "I like to eat apples.",
                "My family is very important.",
                "The dog is playing outside.",
                "My favorite color is blue.",
                "I have two brothers."
            ],
            "intermediate": [
                "Every morning I wake up at 7 AM.",
                "In my free time, I enjoy reading books.",
                "Last year I traveled to Spain.",
                "Learning English requires practice.",
                "The weather today is sunny and warm."
            ],
            "advanced": [
                "Technological innovation drives economic growth.",
                "Effective communication is essential in business.",
                "Scientific research contributes to societal progress.",
                "Democratic principles ensure political stability.",
                "Educational reform addresses systemic challenges."
            ]
        }
    
    def get_game_round(self, difficulty: str, category: str = None):
        """Obtener una ronda de juego (MANTENIDO)"""
        if difficulty not in self.categories:
            difficulty = "beginner"
        
        if not category or category not in self.categories[difficulty]:
            category = random.choice(list(self.categories[difficulty].keys()))
        
        if random.random() > 0.5:
            word = random.choice(self.categories[difficulty][category])
            game_type = "word_translation"
            points = {"beginner": 10, "intermediate": 20, "advanced": 30}[difficulty]
            
            return {
                "type": game_type,
                "content": word,
                "category": category,
                "difficulty": difficulty,
                "points": points,
                "instructions": f"Translate this word to Spanish: '{word}'",
                "hint": f"Category: {category}"
            }
        else:
            sentence = random.choice(self.sentences[difficulty])
            game_type = "sentence_translation"
            points = {"beginner": 15, "intermediate": 30, "advanced": 45}[difficulty]
            
            return {
                "type": game_type,
                "content": sentence,
                "category": "sentence",
                "difficulty": difficulty,
                "points": points,
                "instructions": f"Translate this sentence to Spanish: '{sentence}'",
                "hint": "Speak clearly and pronounce each word"
            }
    
    def validate_answer(self, game_data: dict, user_answer: str, session_id: str = None):
        """Validar respuesta del juego (MANTENIDO)"""
        original = game_data["content"].lower()
        user_lower = user_answer.lower().strip()
        
        # Simulación simple de validación
        is_correct = len(user_lower) > 2  # Si la respuesta tiene al menos 3 caracteres
        
        base_points = game_data["points"]
        points_earned = base_points if is_correct else max(1, int(base_points * 0.2))
        
        # Actualizar sesión
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                session.add_game_result("vocabulary", is_correct, points_earned)
        
        if is_correct:
            message = f"🎯 Correct! {points_earned} points!"
        else:
            message = f"📚 Try again! The word was: '{original}'"
        
        return {
            "is_correct": is_correct,
            "points_earned": points_earned,
            "message": message,
            "user_answer": user_answer,
            "game_type": game_data["type"],
            "difficulty": game_data["difficulty"]
        }

class PronunciationGame:
    def __init__(self):
        # Tongue twisters (MANTENIDO)
        self.tongue_twisters = {
            "beginner": [
                "She sells seashells by the seashore.",
                "How can a clam cram in a clean cream can?",
                "I scream, you scream, we all scream for ice cream.",
                "Four fine fresh fish for you.",
                "Red lorry, yellow lorry."
            ],
            "intermediate": [
                "Peter Piper picked a peck of pickled peppers.",
                "How much wood would a woodchuck chuck if a woodchuck could chuck wood?",
                "Six slippery snails slid slowly seaward.",
                "A proper copper coffee pot.",
                "Fuzzy Wuzzy was a bear."
            ],
            "advanced": [
                "The sixth sick sheik's sixth sheep's sick.",
                "Betty Botter bought some butter but she said the butter's bitter.",
                "I slit the sheet, the sheet I slit, and on the slitted sheet I sit.",
                "Through three cheese trees three free fleas flew.",
                "Lesser leather never weathered wetter weather better."
            ]
        }
    
    def get_pronunciation_challenge(self, difficulty: str):
        """Obtener desafío de pronunciación (MANTENIDO)"""
        if difficulty not in self.tongue_twisters:
            difficulty = "beginner"
        
        twister = random.choice(self.tongue_twisters[difficulty])
        points = {"beginner": 20, "intermediate": 40, "advanced": 60}[difficulty]
        
        return {
            "type": "tongue_twister",
            "content": twister,
            "difficulty": difficulty,
            "points": points,
            "instructions": "Repeat this tongue twister as clearly as possible:",
            "focus": "Clarity and speed"
        }
    
    def validate_pronunciation(self, game_data: dict, session_id: str = None):
        """Validar pronunciación (simplificado) (MANTENIDO)"""
        difficulty = game_data["difficulty"]
        
        # Simulación
        score = random.randint(60, 95)
        passing_threshold = {"beginner": 70, "intermediate": 75, "advanced": 80}[difficulty]
        is_correct = score >= passing_threshold
        
        base_points = game_data["points"]
        if is_correct:
            bonus = int((score - passing_threshold) / 5) * 5
            points_earned = base_points + bonus
        else:
            points_earned = max(1, int(base_points * 0.3))
        
        # Actualizar sesión
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                session.add_game_result("pronunciation", is_correct, points_earned)
        
        if is_correct:
            if score >= 90:
                message = f"🎤 Excellent pronunciation! {points_earned} points! (Score: {score}%)"
            elif score >= 80:
                message = f"🗣️ Very good! {points_earned} points! (Score: {score}%)"
            else:
                message = f"✅ Good effort! {points_earned} points! (Score: {score}%)"
        else:
            message = f"💪 Keep practicing! Focus on: {game_data.get('focus', 'clarity')}"
        
        return {
            "is_correct": is_correct,
            "score": score,
            "points_earned": points_earned,
            "message": message,
            "game_type": "tongue_twister",
            "difficulty": difficulty
        }

# Inicializar juegos
vocabulary_game = VocabularyGame()
pronunciation_game = PronunciationGame()

# ============================================
# PROCESADOR DE AUDIO
# ============================================
class AudioProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()
    
    def transcribe_audio(self, audio_bytes: bytes) -> dict:
        """Transcribir audio"""
        try:
            audio_io = io.BytesIO(audio_bytes)
            
            with sr.AudioFile(audio_io) as source:
                audio_data = self.recognizer.record(source)
                
                try:
                    texto = self.recognizer.recognize_google(audio_data, language='en-US')
                    return {"text": texto, "language": "en", "error": None}
                except sr.UnknownValueError:
                    try:
                        texto = self.recognizer.recognize_google(audio_data, language='es-ES')
                        return {"text": texto, "language": "es", "error": None}
                    except sr.UnknownValueError:
                        return {"text": "", "language": "unknown", "error": "No speech detected"}
                        
        except Exception as e:
            logger.error(f"Error in transcription: {str(e)}")
            return {"text": "", "language": "unknown", "error": str(e)}

audio_processor = AudioProcessor()

# ============================================
# ENDPOINTS PRINCIPALES
# ============================================
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Eli English Tutor v8.0 COMPLETO",
        "version": "8.0.0",
        "timestamp": datetime.now().isoformat(),
        "features": ["Practice", "Games", "Scaffolding", "Spanish Detection"]
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "sessions_active": len(session_manager.sessions)
    })

@app.route('/api/sesion/iniciar', methods=['POST'])
def iniciar_sesion():
    try:
        data = request.json or {}
        user_id = data.get('user_id', f"user_{uuid.uuid4().hex[:8]}")
        
        session = session_manager.create_session(user_id)
        
        return jsonify({
            "estado": "exito",
            "user_id": user_id,
            "session_id": session.session_id,
            "welcome_message": "🎯 Welcome to Eli! Let's practice English!",
            "initial_level": session.current_level,
            "initial_question": session.current_question
        })
    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)[:100]}), 500

# ============================================
# ENDPOINT PRINCIPAL: PROCESAR AUDIO
# ============================================
@app.route('/api/process-audio', methods=['POST'])
def process_audio_unified():
    """Endpoint principal UNIFICADO"""
    try:
        if 'audio' not in request.files:
            return jsonify({
                "status": "error",
                "message": "No audio file provided"
            }), 400
        
        audio_file = request.files['audio']
        session_id = request.form.get('session_id', 'default_session')
        user_id = request.form.get('user_id', 'default_user')
        current_question = request.form.get('current_question', 'Tell me about yourself')
        
        logger.info(f"🔊 Processing audio - Session: {session_id}, Question: {current_question}")
        
        # Leer y transcribir
        audio_bytes = audio_file.read()
        transcription_result = audio_processor.transcribe_audio(audio_bytes)
        texto = transcription_result['text']
        
        # Obtener sesión
        session = session_manager.get_session(session_id)
        if not session:
            session = session_manager.create_session(user_id)
        
        session.current_question = current_question
        
        # Si no hay audio
        if not texto or len(texto.strip()) < 2:
            response = {
                "type": "no_speech",
                "message": """🎤 **I didn't hear anything**

💡 **Tips:**
• Speak for 2-3 seconds
• Be in a quiet place
• Hold the microphone closer

🔊 **Try saying:**
• "Hello, my name is..."
• "I like to practice English"
• "Today is a good day"

🎯 **Ready when you are!**""",
                "pronunciation_score": 0,
                "detected_level": "beginner",
                "needs_scaffolding": True,
                "scaffolding_data": {
                    "template": "Hello, my name is...",
                    "examples": ["Hello, my name is [Your Name]", "I like to learn English"],
                    "vocabulary": ["hello", "name", "my", "like", "learn"],
                    "topic": "introduction",
                    "level": "beginner",
                    "current_question": current_question
                },
                "next_question": "What is your name?",
                "detected_language": "unknown",
                "xp_earned": 0
            }
        else:
            # Análisis completo
            lang_analysis = coach.detectar_idioma(texto)
            duration_est = len(texto.split()) * 0.4
            
            if lang_analysis['is_spanish']:
                if lang_analysis['needs_help']:
                    response = coach.generar_respuesta_ayuda(texto, True, current_question)
                else:
                    response = coach.generar_respuesta_spanish(texto)
            else:
                if lang_analysis['needs_help']:
                    response = coach.generar_respuesta_ayuda(texto, False, current_question)
                else:
                    pron_analysis = coach.analizar_pronunciacion(texto, duration_est)
                    response = coach.generar_respuesta_normal(texto, pron_analysis, current_question)
            
            # Asegurar que ayuda mantiene pregunta actual
            if response.get('is_help_response', False):
                response['next_question'] = current_question
            
            # Actualizar sesión
            session.add_conversation(texto, response['message'], response['pronunciation_score'])
            session.xp += response['xp_earned']
            session.update_level()
            session.current_question = response['next_question']
            session.needs_scaffolding = response['needs_scaffolding']
        
        # Respuesta final
        final_response = {
            "status": "success",
            "data": {
                **response,
                "transcription": texto,
                "session_info": {
                    "session_id": session_id,
                    "user_id": user_id,
                    "current_level": session.current_level,
                    "xp": session.xp,
                    "xp_earned": response.get('xp_earned', 0),
                    "current_question": session.current_question,
                    "needs_scaffolding": session.needs_scaffolding
                }
            }
        }
        
        return jsonify(final_response)
        
    except Exception as e:
        logger.error(f"❌ Error in process-audio: {str(e)}")
        return jsonify({"status": "error", "message": "Error processing audio"}), 500

# ============================================
# ENDPOINT PARA AYUDA EXPLÍCITA (BOTÓN HELP)
# ============================================
@app.route('/api/request-help', methods=['POST'])
def request_help():
    """Endpoint para botón HELP"""
    try:
        data = request.json or {}
        session_id = data.get('session_id', '')
        user_id = data.get('user_id', '')
        current_question = data.get('current_question', 'Tell me about yourself')
        
        logger.info(f"🆘 Help request - Question: {current_question}")
        
        # Generar ayuda
        response = coach.generar_respuesta_ayuda(
            texto="I need help with this question",
            es_spanish=False,
            current_question=current_question
        )
        
        # Forzar misma pregunta
        response['next_question'] = current_question
        
        return jsonify({
            "status": "success",
            "data": response
        })
        
    except Exception as e:
        logger.error(f"Error in request-help: {str(e)}")
        return jsonify({"status": "error", "message": "Error processing help"}), 500

# ============================================
# ENDPOINT PARA PREGUNTAS
# ============================================
@app.route('/api/get-question', methods=['POST'])
def get_question():
    try:
        data = request.json or {}
        session_id = data.get('session_id', '')
        topic = data.get('topic', 'general')
        
        session = None
        if session_id:
            session = session_manager.get_session(session_id)
        
        level = session.current_level if session else "beginner"
        
        preguntas = {
            "general": [
                "What is your name and where are you from?",
                "Tell me about your family.",
                "What do you like to do in your free time?",
                "Describe your daily routine.",
                "What is your favorite food and why?"
            ],
            "family": [
                "Do you have any brothers or sisters?",
                "What activities do you enjoy with your family?",
                "Tell me about your parents.",
                "What family traditions do you have?"
            ],
            "hobbies": [
                "What are your hobbies?",
                "How did you get interested in your favorite hobby?",
                "What do you enjoy most about your free time?"
            ]
        }
        
        questions = preguntas.get(topic, preguntas["general"])
        question = random.choice(questions)
        
        if session:
            session.current_question = question
        
        return jsonify({
            "status": "success",
            "data": {
                "question": question,
                "topic": topic,
                "level": level
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get-question: {str(e)}")
        return jsonify({
            "status": "success",
            "data": {
                "question": "Tell me about yourself",
                "topic": "general",
                "level": "beginner"
            }
        })

# ============================================
# ENDPOINTS DE JUEGOS (COMPLETOS)
# ============================================
@app.route('/api/game/vocabulary/start', methods=['POST'])
def start_vocabulary_game():
    try:
        data = request.json or {}
        session_id = data.get('session_id', '')
        difficulty = data.get('difficulty', 'beginner')
        category = data.get('category', None)
        
        if session_id and difficulty == 'beginner':
            session = session_manager.get_session(session_id)
            if session:
                difficulty = session.current_level
        
        game_round = vocabulary_game.get_game_round(difficulty, category)
        
        return jsonify({
            "status": "success",
            "data": game_round
        })
        
    except Exception as e:
        logger.error(f"Error starting vocabulary game: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)[:100]
        }), 500

@app.route('/api/game/vocabulary/validate', methods=['POST'])
def validate_vocabulary_game():
    try:
        data = request.json or {}
        session_id = data.get('session_id', '')
        game_data = data.get('game_data', {})
        user_answer = data.get('user_answer', '')
        
        if not game_data or not user_answer:
            return jsonify({"status": "error", "message": "Missing data"}), 400
        
        result = vocabulary_game.validate_answer(game_data, user_answer, session_id)
        
        return jsonify({
            "status": "success",
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Error validating vocabulary game: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)[:100]
        }), 500

@app.route('/api/game/pronunciation/start', methods=['POST'])
def start_pronunciation_game():
    try:
        data = request.json or {}
        session_id = data.get('session_id', '')
        difficulty = data.get('difficulty', 'beginner')
        
        if session_id and difficulty == 'beginner':
            session = session_manager.get_session(session_id)
            if session:
                difficulty = session.current_level
        
        challenge = pronunciation_game.get_pronunciation_challenge(difficulty)
        
        return jsonify({
            "status": "success",
            "data": challenge
        })
        
    except Exception as e:
        logger.error(f"Error starting pronunciation game: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)[:100]
        }), 500

@app.route('/api/game/pronunciation/validate', methods=['POST'])
def validate_pronunciation_game():
    try:
        data = request.json or {}
        session_id = data.get('session_id', '')
        game_data = data.get('game_data', {})
        
        result = pronunciation_game.validate_pronunciation(game_data, session_id)
        
        return jsonify({
            "status": "success",
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Error validating pronunciation game: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)[:100]
        }), 500

@app.route('/api/game/categories', methods=['GET'])
def get_game_categories():
    try:
        session_id = request.args.get('session_id', '')
        difficulty = request.args.get('difficulty', 'beginner')
        
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                difficulty = session.current_level
        
        categories = list(vocabulary_game.categories.get(difficulty, vocabulary_game.categories["beginner"]).keys())
        
        return jsonify({
            "status": "success",
            "data": {
                "categories": categories,
                "difficulty": difficulty,
                "game_types": ["vocabulary", "pronunciation"]
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting game categories: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)[:100]
        }), 500

# ============================================
# ENDPOINTS DE ESTADÍSTICAS
# ============================================
@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas():
    try:
        session_id = request.args.get('session_id')
        
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                return jsonify({
                    "estado": "exito", 
                    "stats": session.to_dict(),
                    "game_stats": session.game_stats,
                    "recent_games": session.game_history[-5:] if session.game_history else []
                })
        
        return jsonify({
            "estado": "exito",
            "global_stats": {
                "total_sessions": len(session_manager.sessions)
            }
        })
    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)[:100]}), 500

@app.route('/api/game/leaderboard', methods=['GET'])
def get_leaderboard():
    try:
        all_sessions = list(session_manager.sessions.values())
        sorted_sessions = sorted(all_sessions, key=lambda s: s.xp, reverse=True)[:10]
        
        leaderboard = []
        for i, session in enumerate(sorted_sessions, 1):
            leaderboard.append({
                "rank": i,
                "user_id": session.user_id[:8] + "...",
                "xp": session.xp,
                "level": session.current_level,
                "games_played": session.game_stats["games_played"],
                "accuracy": round(session.game_stats["correct_answers"] / session.game_stats["total_attempts"] * 100, 1) 
                if session.game_stats["total_attempts"] > 0 else 0
            })
        
        return jsonify({
            "status": "success",
            "data": {
                "leaderboard": leaderboard,
                "updated": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)[:100]
        }), 500

# ============================================
# ENDPOINTS DE COMPATIBILIDAD
# ============================================
@app.route('/api/conversar_audio', methods=['POST'])
def conversar_audio():
    try:
        if 'audio' not in request.files:
            return jsonify({"estado": "error", "respuesta": "No audio file"}), 400
        
        return process_audio_unified()
    
    except Exception as e:
        logger.error(f"Error in conversar_audio: {str(e)}")
        return jsonify({"estado": "error", "respuesta": "Error processing audio"}), 500

# ============================================
# EJECUCIÓN
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print(f"🚀 Eli English Tutor v8.0 - SISTEMA COMPLETO")
    print(f"📡 Puerto: {port}")
    print("=" * 60)
    print("✅ CARACTERÍSTICAS INCLUIDAS:")
    print("   • Sistema Coach unificado")
    print("   • Detección de español/inglés")
    print("   • Scaffolding automático")
    print("   • Sistema de juegos COMPLETO")
    print("   • Endpoint de ayuda explícita")
    print("   • Estadísticas y leaderboard")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)