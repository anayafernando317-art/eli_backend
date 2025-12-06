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
from pathlib import Path
import hashlib

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
print("🚀 Eli English Tutor - Backend INTELIGENTE v11.0")
print("🎯 Con GENERACIÓN DINÁMICA COMPLETA")
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
# GENERADOR DE CONTENIDO INTELIGENTE
# ============================================
class DynamicContentGenerator:
    """Genera TODO el contenido dinámicamente"""
    
    def __init__(self):
        # BANCOS DE PALABRAS POR TIEMPO VERBAL Y DIFICULTAD
        self.word_banks = {
            "beginner": {
                "present": {
                    "verbs": ["eat", "drink", "sleep", "study", "work", "play", "read", "write"],
                    "nouns": ["food", "water", "book", "school", "home", "friend", "family"],
                    "adjectives": ["good", "bad", "happy", "sad", "tired", "hungry"]
                },
                "past": {
                    "verbs": ["ate", "drank", "slept", "studied", "worked", "played", "read", "wrote"],
                    "time_words": ["yesterday", "last week", "this morning", "last night"],
                    "connectors": ["then", "after that", "later"]
                },
                "future": {
                    "verbs": ["will eat", "will drink", "will study", "will work", "will play"],
                    "time_words": ["tomorrow", "next week", "soon", "later"],
                    "plans": ["plan to", "want to", "hope to"]
                }
            },
            "intermediate": {
                "present": {
                    "verbs": ["analyze", "discuss", "explore", "create", "develop", "manage"],
                    "nouns": ["project", "meeting", "presentation", "research", "analysis"],
                    "adjectives": ["challenging", "interesting", "complex", "valuable"]
                },
                "past": {
                    "verbs": ["accomplished", "achieved", "completed", "experienced", "overcame"],
                    "time_words": ["previously", "formerly", "in the past", "earlier"],
                    "connectors": ["consequently", "as a result", "therefore"]
                },
                "future": {
                    "verbs": ["will achieve", "will complete", "will implement", "will establish"],
                    "time_words": ["in the future", "eventually", "down the road"],
                    "plans": ["aim to", "intend to", "aspire to"]
                },
                "present_perfect": {
                    "verbs": ["have learned", "have improved", "have developed", "have gained"],
                    "experiences": ["experience", "knowledge", "skills", "understanding"]
                },
                "past_continuous": {
                    "verbs": ["was studying", "were working", "was practicing", "were discussing"],
                    "time_words": ["while", "when", "during", "at that time"]
                }
            },
            "advanced": {
                "present": {
                    "verbs": ["scrutinize", "deconstruct", "conceptualize", "orchestrate", "pioneer"],
                    "nouns": ["methodology", "framework", "paradigm", "infrastructure"],
                    "adjectives": ["sophisticated", "cutting-edge", "groundbreaking", "innovative"]
                },
                "past_perfect": {
                    "verbs": ["had mastered", "had pioneered", "had revolutionized", "had established"],
                    "time_words": ["by that point", "prior to", "up until then"]
                },
                "future_perfect": {
                    "verbs": ["will have mastered", "will have pioneered", "will have transformed"],
                    "time_words": ["by then", "by that time", "by the time"]
                },
                "conditional": {
                    "verbs": ["would innovate", "could revolutionize", "might transform"],
                    "hypothetical": ["provided that", "assuming that", "in the event that"]
                },
                "subjunctive": {
                    "verbs": ["were to implement", "should one consider", "might one examine"],
                    "formal": ["it is essential that", "it is crucial that", "it is imperative that"]
                }
            }
        }
        
        # ESTRUCTURAS DE ORACIONES POR TIEMPO VERBAL
        self.sentence_structures = {
            "present_simple": [
                "I {verb} {noun} every day.",
                "She {verb} at {place}.",
                "They always {verb} {activity}."
            ],
            "present_continuous": [
                "I am {verb}ing right now.",
                "He is {verb}ing at the moment.",
                "We are {verb}ing together."
            ],
            "past_simple": [
                "Yesterday, I {verb} {noun}.",
                "Last week, she {verb} at {place}.",
                "They {verb} {activity}."
            ],
            "past_continuous": [
                "I was {verb}ing when {event}.",
                "They were {verb}ing at {time}.",
                "He was {verb}ing while {activity}."
            ],
            "future_simple": [
                "Tomorrow, I will {verb} {noun}.",
                "Next week, she will {verb} at {place}.",
                "They will {verb} {activity}."
            ],
            "present_perfect": [
                "I have {verb} {noun} recently.",
                "She has {verb} since {time}.",
                "They have {verb} many times."
            ],
            "past_perfect": [
                "I had {verb} before {event}.",
                "She had already {verb} when {event}.",
                "They had {verb} by that time."
            ],
            "future_perfect": [
                "By {time}, I will have {verb}.",
                "She will have {verb} by tomorrow.",
                "They will have {verb} soon."
            ],
            "conditional": [
                "If I had time, I would {verb}.",
                "She would {verb} if {condition}.",
                "They could {verb} provided that {condition}."
            ]
        }
        
        # PLANTILLAS DE PREGUNTAS POR TIEMPO VERBAL
        self.question_templates = {
            "present": [
                "What do you usually {verb}?",
                "How often do you {verb}?",
                "Where do you {verb}?",
                "Why do you {verb} {noun}?"
            ],
            "past": [
                "What did you {verb} yesterday?",
                "How did you {verb} last week?",
                "Where were you when you {verb}?",
                "Why did you {verb} {noun}?"
            ],
            "future": [
                "What will you {verb} tomorrow?",
                "How will you {verb} next month?",
                "Where will you {verb}?",
                "Why will you {verb} {noun}?"
            ],
            "present_perfect": [
                "What have you {verb} recently?",
                "How long have you {verb}?",
                "What {noun} have you {verb}?",
                "Why have you {verb} {activity}?"
            ],
            "hypothetical": [
                "What would you do if you could {verb}?",
                "How would you {verb} if {condition}?",
                "Where would you {verb} given the chance?",
                "Why would you {verb} {noun}?"
            ]
        }
        
        # CATEGORÍAS TEMÁTICAS
        self.categories = {
            "daily_life": ["routine", "habits", "schedule", "chores", "errands"],
            "work_study": ["projects", "assignments", "meetings", "classes", "exams"],
            "hobbies": ["sports", "music", "reading", "gaming", "cooking"],
            "travel": ["destinations", "experiences", "cultures", "adventures"],
            "personal": ["goals", "dreams", "memories", "achievements", "challenges"]
        }
    
    def generate_vocabulary(self, difficulty="beginner", tense="present", category="general"):
        """Genera palabra de vocabulario con contexto completo"""
        
        # Seleccionar banco según dificultad y tiempo verbal
        if difficulty in self.word_banks and tense in self.word_banks[difficulty]:
            bank = self.word_banks[difficulty][tense]
        else:
            # Fallback al banco más simple
            bank = self.word_banks["beginner"]["present"]
        
        # Seleccionar tipo de palabra
        word_type = random.choice(list(bank.keys()))
        word = random.choice(bank[word_type])
        
        # Generar oración según tiempo verbal
        sentence = self._generate_sentence(word, difficulty, tense, word_type)
        
        # Generar traducción
        translation = self._generate_translation(word, sentence, tense)
        
        # Información gramatical
        grammar_info = self._get_grammar_info(tense, word_type)
        
        return {
            "word": word,
            "type": word_type,
            "sentence": sentence,
            "translation": translation,
            "tense": tense,
            "difficulty": difficulty,
            "category": category,
            "grammar": grammar_info,
            "is_generated": True,
            "generated_at": datetime.now().isoformat()
        }
    
    def _generate_sentence(self, word, difficulty, tense, word_type):
        """Genera oración contextualizada"""
        
        # Determinar estructura según tiempo verbal
        if tense == "present":
            if "continuous" in tense:
                structure = random.choice(self.sentence_structures.get("present_continuous", ["I am {verb}ing."]))
            else:
                structure = random.choice(self.sentence_structures.get("present_simple", ["I {verb}."]))
        elif tense == "past":
            if "continuous" in tense:
                structure = random.choice(self.sentence_structures.get("past_continuous", ["I was {verb}ing."]))
            else:
                structure = random.choice(self.sentence_structures.get("past_simple", ["I {verb}."]))
        elif tense == "future":
            structure = random.choice(self.sentence_structures.get("future_simple", ["I will {verb}."]))
        elif "perfect" in tense:
            if "past" in tense:
                structure = random.choice(self.sentence_structures.get("past_perfect", ["I had {verb}."]))
            elif "future" in tense:
                structure = random.choice(self.sentence_structures.get("future_perfect", ["I will have {verb}."]))
            else:
                structure = random.choice(self.sentence_structures.get("present_perfect", ["I have {verb}."]))
        elif tense == "conditional":
            structure = random.choice(self.sentence_structures.get("conditional", ["I would {verb}."]))
        else:
            structure = "I {verb}."
        
        # Reemplazar marcadores
        if word_type == "verbs":
            sentence = structure.replace("{verb}", word)
        elif word_type == "nouns":
            sentence = structure.replace("{noun}", word)
        elif word_type == "adjectives":
            sentence = structure.replace("{adjective}", word)
        else:
            sentence = f"I {word}."
        
        # Añadir contexto adicional
        context_words = {
            "place": ["at home", "at school", "at work", "in the park", "at the gym"],
            "activity": ["reading", "studying", "working", "exercising", "relaxing"],
            "event": ["the phone rang", "it started raining", "my friend arrived"],
            "time": ["morning", "afternoon", "evening", "night"],
            "condition": ["I had more time", "it were possible", "circumstances allowed"]
        }
        
        # Añadir contexto aleatorio
        for marker in ["{place}", "{activity}", "{event}", "{time}", "{condition}"]:
            if marker in sentence:
                context_type = marker.strip("{}")
                if context_type in context_words:
                    sentence = sentence.replace(marker, random.choice(context_words[context_type]))
        
        return sentence.capitalize()
    
    def _generate_translation(self, word, sentence, tense):
        """Genera traducción al español"""
        
        # Diccionario básico de traducciones
        translations = {
            # Verbos comunes
            "eat": "comer", "drink": "beber", "sleep": "dormir", 
            "study": "estudiar", "work": "trabajar", "play": "jugar",
            "read": "leer", "write": "escribir",
            
            # Sustantivos
            "food": "comida", "water": "agua", "book": "libro",
            "school": "escuela", "home": "hogar", "friend": "amigo",
            "family": "familia",
            
            # Adjetivos
            "good": "bueno", "bad": "malo", "happy": "feliz",
            "sad": "triste", "tired": "cansado", "hungry": "hambriento"
        }
        
        # Traducir palabra individual
        word_translation = translations.get(word.lower(), word)
        
        # Traducir oración completa (simplificado)
        sentence_translation = sentence
        
        # Reemplazos básicos para tiempos verbales
        tense_translations = {
            "present": {"I": "Yo", "am": "estoy", "is": "está", "are": "están"},
            "past": {"was": "estaba", "were": "estaban", "did": "hice"},
            "future": {"will": "voy a", "will be": "estaré"},
            "present_perfect": {"have": "he", "has": "ha"},
            "past_perfect": {"had": "había"},
            "conditional": {"would": "haría", "could": "podría"}
        }
        
        if tense in tense_translations:
            for eng, esp in tense_translations[tense].items():
                sentence_translation = sentence_translation.replace(eng, esp)
        
        return {
            "word": word_translation,
            "sentence": sentence_translation,
            "tense": self._get_spanish_tense(tense)
        }
    
    def _get_spanish_tense(self, english_tense):
        """Convierte tiempo verbal inglés a español"""
        tense_map = {
            "present_simple": "presente simple",
            "present_continuous": "presente continuo",
            "past_simple": "pretérito",
            "past_continuous": "pretérito imperfecto",
            "future_simple": "futuro simple",
            "present_perfect": "pretérito perfecto",
            "past_perfect": "pretérito pluscuamperfecto",
            "future_perfect": "futuro perfecto",
            "conditional": "condicional"
        }
        return tense_map.get(english_tense, english_tense)
    
    def _get_grammar_info(self, tense, word_type):
        """Proporciona información gramatical"""
        
        grammar_explanations = {
            "present_simple": {
                "description": "Para hábitos y hechos generales",
                "structure": "Sujeto + verbo (+s en 3ra persona)",
                "example": "I work every day."
            },
            "past_simple": {
                "description": "Para acciones completadas en el pasado",
                "structure": "Sujeto + verbo en pasado (+ed o irregular)",
                "example": "I worked yesterday."
            },
            "future_simple": {
                "description": "Para decisiones espontáneas y predicciones",
                "structure": "Sujeto + will + verbo base",
                "example": "I will work tomorrow."
            },
            "present_perfect": {
                "description": "Para experiencias y acciones con relevancia presente",
                "structure": "Sujeto + have/has + participio pasado",
                "example": "I have worked here for years."
            },
            "conditional": {
                "description": "Para situaciones hipotéticas y cortesía",
                "structure": "Sujeto + would + verbo base",
                "example": "I would work if I could."
            }
        }
        
        return grammar_explanations.get(tense, {
            "description": f"Tiempo verbal: {tense}",
            "structure": "Consulta reglas gramaticales",
            "example": "Ejemplo no disponible"
        })
    
    def generate_question(self, difficulty="beginner", topic=None, force_tense=None):
        """Genera pregunta dinámica"""
        
        # Determinar tiempo verbal
        if force_tense:
            tense = force_tense
        else:
            tenses_by_difficulty = {
                "beginner": ["present", "past", "future"],
                "intermediate": ["present", "past", "future", "present_perfect", "past_continuous"],
                "advanced": ["present", "past_perfect", "future_perfect", "conditional", "subjunctive"]
            }
            available_tenses = tenses_by_difficulty.get(difficulty, ["present"])
            tense = random.choice(available_tenses)
        
        # Seleccionar plantilla según tiempo verbal
        if tense in self.question_templates:
            template = random.choice(self.question_templates[tense])
        else:
            template = "What do you think about {topic}?"
        
        # Seleccionar categoría
        if not topic:
            topic = random.choice(list(self.categories.keys()))
        
        # Obtener palabras para rellenar
        bank = self.word_banks.get(difficulty, self.word_banks["beginner"]).get(tense, {})
        
        if "verbs" in bank:
            verb = random.choice(bank["verbs"])
        else:
            verb = random.choice(self.word_banks["beginner"]["present"]["verbs"])
        
        if "nouns" in bank:
            noun = random.choice(bank["nouns"])
        else:
            noun = random.choice(self.word_banks["beginner"]["present"]["nouns"])
        
        # Rellenar plantilla
        question = template
        question = question.replace("{verb}", verb)
        question = question.replace("{noun}", noun)
        question = question.replace("{topic}", topic)
        
        # Añadir elementos específicos
        if "{activity}" in question and "activities" in self.categories:
            activity = random.choice(self.categories["hobbies"])
            question = question.replace("{activity}", activity)
        
        if "{condition}" in question:
            conditions = ["you had more time", "it were possible", "circumstances allowed"]
            question = question.replace("{condition}", random.choice(conditions))
        
        # Asegurar formato correcto
        if not question.endswith("?"):
            question += "?"
        
        # Capitalizar
        question = question[0].upper() + question[1:]
        
        # Generar traducción
        translation = self._translate_question(question, tense)
        
        return {
            "question": question,
            "translation": translation,
            "tense": tense,
            "difficulty": difficulty,
            "topic": topic,
            "category": random.choice(self.categories[topic]) if topic in self.categories else "general",
            "is_generated": True,
            "grammar_focus": self._get_grammar_focus(tense),
            "suggested_response": self._generate_suggested_response(question, tense, difficulty)
        }
    
    def _translate_question(self, question, tense):
        """Traduce pregunta al español"""
        
        # Traducciones básicas
        translations = {
            "What": "¿Qué",
            "How": "¿Cómo",
            "Where": "¿Dónde",
            "Why": "¿Por qué",
            "When": "¿Cuándo",
            "Who": "¿Quién",
            "do you": "tú",
            "does he/she": "él/ella",
            "did you": "tú",
            "will you": "tú",
            "have you": "has tú",
            "had you": "habías tú",
            "would you": "tú",
            "usually": "usualmente",
            "often": "a menudo",
            "yesterday": "ayer",
            "tomorrow": "mañana",
            "last week": "la semana pasada",
            "next month": "el próximo mes",
            "recently": "recientemente"
        }
        
        translated = question
        for eng, esp in translations.items():
            translated = translated.replace(eng, esp)
        
        # Asegurar formato español
        if not translated.startswith("¿"):
            translated = "¿" + translated
        
        return translated
    
    def _get_grammar_focus(self, tense):
        """Obtiene enfoque gramatical para la pregunta"""
        
        focus_map = {
            "present": "Presente simple - hábitos y rutinas",
            "past": "Pasado simple - experiencias completadas",
            "future": "Futuro simple - planes y predicciones",
            "present_perfect": "Presente perfecto - experiencias recientes",
            "past_perfect": "Pasado perfecto - acciones anteriores a otras",
            "future_perfect": "Futuro perfecto - acciones completadas antes de un punto futuro",
            "conditional": "Condicional - situaciones hipotéticas",
            "subjunctive": "Subjuntivo - deseos y situaciones improbables"
        }
        
        return focus_map.get(tense, "Práctica general")
    
    def _generate_suggested_response(self, question, tense, difficulty):
        """Genera respuesta sugerida según la pregunta"""
        
        response_templates = {
            "present": [
                "I usually {verb} at {time}.",
                "Normally, I {verb} {frequency}.",
                "Typically, I {verb} because {reason}."
            ],
            "past": [
                "Yesterday, I {verb} at {place}.",
                "Last week, I {verb} with {person}.",
                "Previously, I {verb} because {reason}."
            ],
            "future": [
                "Tomorrow, I will {verb} at {time}.",
                "Next week, I plan to {verb} at {place}.",
                "In the future, I hope to {verb} because {reason}."
            ]
        }
        
        # Seleccionar template
        template_group = "present"
        for key in ["past", "future", "present"]:
            if key in tense:
                template_group = key
                break
        
        template = random.choice(response_templates.get(template_group, ["I {verb}."]))
        
        # Obtener verbos apropiados
        bank = self.word_banks.get(difficulty, self.word_banks["beginner"])
        verbs = []
        for tense_bank in bank.values():
            if "verbs" in tense_bank:
                verbs.extend(tense_bank["verbs"])
        
        if verbs:
            verb = random.choice(verbs)
        else:
            verb = "do something"
        
        # Rellenar template
        response = template.replace("{verb}", verb)
        
        # Añadir contexto
        contexts = {
            "{time}": ["morning", "afternoon", "evening"],
            "{place}": ["home", "school", "work", "the park"],
            "{person}": ["my friend", "my family", "a colleague"],
            "{frequency}": ["every day", "once a week", "sometimes"],
            "{reason}": ["it's important", "I enjoy it", "it helps me learn"]
        }
        
        for placeholder, options in contexts.items():
            if placeholder in response:
                response = response.replace(placeholder, random.choice(options))
        
        return response

# Inicializar generador
content_generator = DynamicContentGenerator()

# ============================================
# BASE DE DATOS SIMPLE PARA PROGRESO
# ============================================
class ProgressDatabase:
    def __init__(self):
        self.db_file = "progress_db.json"
        self._init_db()
    
    def _init_db(self):
        if not Path(self.db_file).exists():
            with open(self.db_file, 'w') as f:
                json.dump({
                    "users": {},
                    "generated_content": {
                        "vocabulary": [],
                        "questions": [],
                        "sentences": []
                    }
                }, f, indent=2)
    
    def save_user_progress(self, user_id, progress_data):
        try:
            with open(self.db_file, 'r') as f:
                data = json.load(f)
            
            if user_id not in data["users"]:
                data["users"][user_id] = {
                    "created": datetime.now().isoformat(),
                    "sessions": [],
                    "total_xp": 0,
                    "current_level": "beginner"
                }
            
            user = data["users"][user_id]
            user["last_seen"] = datetime.now().isoformat()
            user["total_xp"] = progress_data.get("xp", user.get("total_xp", 0))
            user["current_level"] = progress_data.get("level", user.get("current_level", "beginner"))
            
            # Guardar sesión
            session = {
                "id": progress_data.get("session_id"),
                "timestamp": datetime.now().isoformat(),
                "xp_earned": progress_data.get("xp_earned", 0),
                "questions": progress_data.get("questions", 0)
            }
            user["sessions"].append(session)
            
            # Mantener solo últimas 50 sesiones
            if len(user["sessions"]) > 50:
                user["sessions"] = user["sessions"][-50:]
            
            with open(self.db_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving progress: {e}")
            return False
    
    def load_user_progress(self, user_id):
        try:
            with open(self.db_file, 'r') as f:
                data = json.load(f)
            
            return data["users"].get(user_id)
        except:
            return None
    
    def save_generated_content(self, content_type, content):
        try:
            with open(self.db_file, 'r') as f:
                data = json.load(f)
            
            if content_type not in data["generated_content"]:
                data["generated_content"][content_type] = []
            
            content_entry = {
                "id": hashlib.md5(json.dumps(content).encode()).hexdigest()[:8],
                "content": content,
                "created": datetime.now().isoformat(),
                "used": 0
            }
            
            data["generated_content"][content_type].append(content_entry)
            
            # Limitar a 1000 entradas
            if len(data["generated_content"][content_type]) > 1000:
                data["generated_content"][content_type] = data["generated_content"][content_type][-1000:]
            
            with open(self.db_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return content_entry["id"]
        except Exception as e:
            logger.error(f"Error saving generated content: {e}")
            return None

progress_db = ProgressDatabase()

# ============================================
# PROCESADOR DE AUDIO
# ============================================
class AudioProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()
    
    def transcribe_audio(self, audio_bytes):
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
        "service": "Eli English Tutor - Dynamic v11.0",
        "version": "11.0.0",
        "timestamp": datetime.now().isoformat(),
        "features": ["Dynamic Content", "Tense-Based Learning", "Progress Tracking"]
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "content_generator": "active"
    })

# ============================================
# ENDPOINT: PROCESAR AUDIO
# ============================================
@app.route('/api/process-audio', methods=['POST'])
def process_audio():
    """Endpoint principal para procesar audio"""
    try:
        if 'audio' not in request.files:
            return jsonify({"status": "error", "message": "No audio file"}), 400
        
        audio_file = request.files['audio']
        session_id = request.form.get('session_id', 'default')
        user_id = request.form.get('user_id', 'anonymous')
        current_question = request.form.get('current_question', 'Tell me about yourself')
        
        logger.info(f"Processing audio from {user_id}")
        
        # Transcribir audio
        audio_bytes = audio_file.read()
        transcription = audio_processor.transcribe_audio(audio_bytes)
        user_text = transcription['text']
        
        # Generar respuesta dinámica
        if user_text and len(user_text.strip()) > 2:
            # Analizar texto del usuario
            detected_tense = _detect_tense_in_text(user_text)
            user_level = _estimate_user_level(user_text)
            
            # Generar nueva pregunta
            next_question = content_generator.generate_question(
                difficulty=user_level,
                force_tense=detected_tense
            )
            
            # Análisis de pronunciación simulado
            pronunciation_score = min(95, max(30, len(user_text.split()) * 5 + random.randint(-10, 10)))
            
            # Generar scaffolding
            scaffolding = {
                "template": content_generator._generate_suggested_response(
                    next_question["question"],
                    next_question["tense"],
                    user_level
                ),
                "examples": [
                    f"Example: {content_generator._generate_suggested_response(next_question['question'], next_question['tense'], user_level)}"
                ],
                "vocabulary": [next_question.get("suggested_word", "practice")],
                "topic": next_question["topic"],
                "level": user_level,
                "tips": [
                    f"Focus on {next_question['tense']} tense",
                    "Speak clearly and slowly",
                    "Use complete sentences"
                ],
                "current_question": next_question["question"],
                "grammar_focus": next_question["grammar_focus"]
            }
            
            response = {
                "type": "conversation_response",
                "message": f"""🎉 **Great!** I heard you say: "{user_text[:50]}..."

📊 **Pronunciation:** {pronunciation_score}/100
🎯 **Next Question:** {next_question['question']}
🇪🇸 **En español:** {next_question['translation']}
💡 **Grammar Focus:** {next_question['grammar_focus']}

Keep up the good work!""",
                "pronunciation_score": pronunciation_score,
                "detected_level": user_level,
                "needs_scaffolding": pronunciation_score < 70,
                "scaffolding_data": scaffolding,
                "next_question": next_question["question"],
                "next_question_spanish": next_question["translation"],
                "next_question_category": next_question["topic"],
                "detected_language": transcription['language'],
                "xp_earned": min(30, max(5, int(pronunciation_score / 3))),
                "is_dynamic_content": True,
                "tense_used": detected_tense,
                "grammar_focus": next_question["grammar_focus"]
            }
        else:
            # No se detectó audio
            next_question = content_generator.generate_question(difficulty="beginner")
            
            response = {
                "type": "no_speech",
                "message": f"""🎤 **I didn't hear anything**

💡 **Try this question:** {next_question['question']}
🇪🇸 **En español:** {next_question['translation']}

Speak clearly for 2-3 seconds!""",
                "pronunciation_score": 0,
                "detected_level": "beginner",
                "needs_scaffolding": True,
                "scaffolding_data": {
                    "template": content_generator._generate_suggested_response(
                        next_question["question"],
                        next_question["tense"],
                        "beginner"
                    ),
                    "examples": ["Try: 'Hello, my name is...'"],
                    "vocabulary": ["hello", "name", "practice", "speak"],
                    "topic": "introduction",
                    "level": "beginner",
                    "current_question": next_question["question"]
                },
                "next_question": next_question["question"],
                "next_question_spanish": next_question["translation"],
                "detected_language": "unknown",
                "xp_earned": 0,
                "is_dynamic_content": True
            }
            user_text = ""
        
        # Guardar progreso
        progress_db.save_user_progress(user_id, {
            "session_id": session_id,
            "xp": response.get("xp_earned", 0),
            "level": response.get("detected_level", "beginner"),
            "questions": 1
        })
        
        # Guardar contenido generado
        if response.get("is_dynamic_content"):
            progress_db.save_generated_content("questions", {
                "question": response.get("next_question"),
                "tense": next_question.get("tense"),
                "difficulty": response.get("detected_level")
            })
        
        return jsonify({
            "status": "success",
            "data": {
                **response,
                "transcription": user_text,
                "session_info": {
                    "session_id": session_id,
                    "user_id": user_id,
                    "current_level": response.get("detected_level", "beginner"),
                    "xp_earned": response.get("xp_earned", 0),
                    "current_question": response.get("next_question"),
                    "show_spanish_translation": True
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# ENDPOINT: GENERAR VOCABULARIO DINÁMICO
# ============================================
@app.route('/api/generate/vocabulary', methods=['POST'])
def generate_vocabulary():
    """Genera vocabulario dinámico para juegos"""
    try:
        data = request.json or {}
        difficulty = data.get('difficulty', 'beginner')
        tense = data.get('tense', 'present')
        category = data.get('category', 'general')
        
        # Generar contenido
        vocabulary = content_generator.generate_vocabulary(difficulty, tense, category)
        
        # Guardar en base de datos
        content_id = progress_db.save_generated_content("vocabulary", vocabulary)
        
        return jsonify({
            "status": "success",
            "data": {
                **vocabulary,
                "content_id": content_id,
                "game_type": "vocabulary",
                "points": {"beginner": 10, "intermediate": 15, "advanced": 20}.get(difficulty, 10),
                "instructions": f"Translate this {tense} tense word: '{vocabulary['word']}'",
                "hint": f"Used in: '{vocabulary['sentence']}'"
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating vocabulary: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# ENDPOINT: GENERAR PREGUNTA DINÁMICA
# ============================================
@app.route('/api/generate/question', methods=['POST'])
def generate_question():
    """Genera pregunta dinámica para práctica"""
    try:
        data = request.json or {}
        difficulty = data.get('difficulty', 'beginner')
        topic = data.get('topic')
        force_tense = data.get('tense')
        
        question = content_generator.generate_question(difficulty, topic, force_tense)
        
        # Guardar en base de datos
        content_id = progress_db.save_generated_content("questions", question)
        
        return jsonify({
            "status": "success",
            "data": {
                **question,
                "content_id": content_id
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating question: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# ENDPOINT: JUEGO DE VOCABULARIO DINÁMICO
# ============================================
@app.route('/api/game/vocabulary/start', methods=['POST'])
def start_vocabulary_game():
    """Inicia juego de vocabulario con contenido dinámico"""
    try:
        data = request.json or {}
        difficulty = data.get('difficulty', 'beginner')
        category = data.get('category', 'general')
        session_id = data.get('session_id')
        
        # Determinar tiempo verbal según dificultad
        tenses_by_difficulty = {
            "beginner": ["present", "past", "future"],
            "intermediate": ["present", "past", "future", "present_perfect"],
            "advanced": ["past_perfect", "future_perfect", "conditional", "subjunctive"]
        }
        
        available_tenses = tenses_by_difficulty.get(difficulty, ["present"])
        selected_tense = random.choice(available_tenses)
        
        # Generar vocabulario
        vocabulary = content_generator.generate_vocabulary(difficulty, selected_tense, category)
        
        # Determinar tipo de juego
        game_types = ["translation", "sentence_completion", "tense_identification"]
        game_type = random.choice(game_types)
        
        game_data = {
            "type": "dynamic_vocabulary",
            "content": vocabulary["word"],
            "translation": vocabulary["translation"]["word"],
            "sentence": vocabulary["sentence"],
            "full_translation": vocabulary["translation"]["sentence"],
            "tense": selected_tense,
            "difficulty": difficulty,
            "category": category,
            "points": {"beginner": 10, "intermediate": 15, "advanced": 20}.get(difficulty, 10),
            "grammar_info": vocabulary["grammar"],
            "is_generated": True
        }
        
        # Añadir instrucciones según tipo de juego
        if game_type == "translation":
            game_data["instructions"] = f"Translate this {selected_tense} tense word to Spanish: '{vocabulary['word']}'"
            game_data["hint"] = f"Used in: '{vocabulary['sentence']}'"
        elif game_type == "sentence_completion":
            incomplete = vocabulary["sentence"].replace(vocabulary["word"], "_____")
            game_data["instructions"] = f"Complete the sentence: '{incomplete}'"
            game_data["hint"] = f"Tense: {selected_tense} | Translation: {vocabulary['translation']['word']}"
        else:  # tense_identification
            game_data["instructions"] = f"What tense is used in: '{vocabulary['sentence']}'?"
            game_data["hint"] = f"Options: present, past, future, perfect"
        
        game_data["game_type"] = game_type
        
        return jsonify({
            "status": "success",
            "data": game_data
        })
        
    except Exception as e:
        logger.error(f"Error starting vocabulary game: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# ENDPOINT: VALIDAR RESPUESTA DE JUEGO
# ============================================
@app.route('/api/game/vocabulary/validate', methods=['POST'])
def validate_vocabulary_game():
    """Valida respuesta del juego de vocabulario"""
    try:
        data = request.json or {}
        game_data = data.get('game_data', {})
        user_answer = data.get('user_answer', '').strip().lower()
        session_id = data.get('session_id')
        
        correct = False
        points = game_data.get('points', 10)
        
        # Lógica de validación según tipo de juego
        game_type = game_data.get('game_type', 'translation')
        correct_answer = game_data.get('translation', '').lower()
        target_word = game_data.get('content', '').lower()
        
        if game_type == "translation":
            # Validar traducción (flexible)
            correct = _validate_translation(user_answer, correct_answer, target_word)
        elif game_type == "sentence_completion":
            # Validar palabra faltante
            correct = user_answer == target_word
        else:  # tense_identification
            correct_tense = game_data.get('tense', 'present')
            correct = user_answer in correct_tense or correct_tense in user_answer
        
        # Calcular puntos
        points_earned = points if correct else max(1, points // 3)
        
        # Mensaje de retroalimentación
        if correct:
            tense_info = game_data.get('tense', 'present')
            message = f"🎯 Correct! {points_earned} points!\n"
            if tense_info != 'present':
                message += f"Excellent use of {tense_info} tense!"
        else:
            message = f"📚 Almost! The correct answer was: '{correct_answer}'"
            if game_data.get('grammar_info'):
                message += f"\n💡 Grammar tip: {game_data['grammar_info']['description']}"
        
        return jsonify({
            "status": "success",
            "data": {
                "is_correct": correct,
                "points_earned": points_earned,
                "message": message,
                "correct_answer": correct_answer,
                "tense": game_data.get('tense'),
                "grammar_tip": game_data.get('grammar_info', {}).get('description', '')
            }
        })
        
    except Exception as e:
        logger.error(f"Error validating vocabulary game: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# ENDPOINT: JUEGO DE PRONUNCIACIÓN DINÁMICO
# ============================================
@app.route('/api/game/pronunciation/start', methods=['POST'])
def start_pronunciation_game():
    """Inicia juego de pronunciación con contenido dinámico"""
    try:
        data = request.json or {}
        difficulty = data.get('difficulty', 'beginner')
        
        # Generar oración según dificultad
        if difficulty == "beginner":
            vocab = content_generator.generate_vocabulary("beginner", "present", "general")
            sentence = vocab["sentence"]
            tense = "present"
        elif difficulty == "intermediate":
            vocab = content_generator.generate_vocabulary("intermediate", "past", "work_study")
            sentence = vocab["sentence"]
            tense = "past"
        else:  # advanced
            vocab = content_generator.generate_vocabulary("advanced", "conditional", "personal")
            sentence = vocab["sentence"]
            tense = "conditional"
        
        # Crear datos del juego
        game_data = {
            "type": "pronunciation_challenge",
            "content": sentence,
            "translation": vocab.get("translation", {}).get("sentence", sentence),
            "difficulty": difficulty,
            "tense": tense,
            "points": {"beginner": 15, "intermediate": 25, "advanced": 35}.get(difficulty, 15),
            "focus": f"Clarity and {tense} tense pronunciation",
            "challenge_type": "sentence_repetition",
            "is_generated": True
        }
        
        return jsonify({
            "status": "success",
            "data": game_data
        })
        
    except Exception as e:
        logger.error(f"Error starting pronunciation game: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# ENDPOINT: OBTENER PREGUNTA
# ============================================
@app.route('/api/get-question', methods=['POST'])
def get_question_endpoint():
    """Obtiene pregunta dinámica"""
    try:
        data = request.json or {}
        session_id = data.get('session_id', '')
        topic = data.get('topic', '')
        force_new = data.get('force_new', False)
        
        # Determinar dificultad basada en sesión
        difficulty = "beginner"  # Por defecto
        
        # Generar pregunta
        question = content_generator.generate_question(
            difficulty=difficulty,
            topic=topic if topic else None
        )
        
        return jsonify({
            "status": "success",
            "data": {
                **question,
                "show_spanish_translation": True,
                "session_id": session_id
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting question: {e}")
        return jsonify({
            "status": "success",
            "data": {
                "question": "What did you do yesterday?",
                "translation": "¿Qué hiciste ayer?",
                "tense": "past",
                "difficulty": "beginner",
                "topic": "daily_life",
                "is_generated": False
            }
        })

# ============================================
# ENDPOINT: AYUDA EXPLÍCITA
# ============================================
@app.route('/api/request-help', methods=['POST'])
def request_help():
    """Proporciona ayuda específica para una pregunta"""
    try:
        data = request.json or {}
        current_question = data.get('current_question', 'Tell me about yourself')
        session_id = data.get('session_id', '')
        
        # Analizar pregunta para determinar tiempo verbal
        detected_tense = _detect_tense_in_question(current_question)
        difficulty = "beginner"
        
        # Generar scaffolding específico
        suggested_response = content_generator._generate_suggested_response(
            current_question,
            detected_tense,
            difficulty
        )
        
        # Obtener vocabulario relevante
        vocab = content_generator.generate_vocabulary(difficulty, detected_tense, "general")
        
        response = {
            "type": "help_response",
            "message": f"""🆘 **I'll help you answer this question:**

❓ **Question:** {current_question}
💡 **Suggested structure:** "{suggested_response}"
🔤 **Useful vocabulary:** {vocab['word']} ({vocab['translation']['word']})
🎯 **Tense to use:** {detected_tense}

**Try saying:** "{suggested_response}" """,
            "pronunciation_score": 0,
            "detected_level": difficulty,
            "needs_scaffolding": True,
            "scaffolding_data": {
                "template": suggested_response,
                "examples": [suggested_response],
                "vocabulary": [vocab['word'], vocab['translation']['word']],
                "topic": "general",
                "level": difficulty,
                "tips": [
                    f"Use {detected_tense} tense",
                    "Speak slowly and clearly",
                    "Add personal details"
                ],
                "current_question": current_question,
                "grammar_focus": f"{detected_tense} tense practice"
            },
            "next_question": current_question,  # Mantener misma pregunta
            "detected_language": "en",
            "xp_earned": 10,
            "is_help_response": True,
            "is_dynamic_content": True
        }
        
        return jsonify({
            "status": "success",
            "data": response
        })
        
    except Exception as e:
        logger.error(f"Error in request-help: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# ENDPOINT: INICIAR SESIÓN
# ============================================
@app.route('/api/sesion/iniciar', methods=['POST'])
def iniciar_sesion():
    try:
        data = request.json or {}
        user_id = data.get('user_id', f"user_{uuid.uuid4().hex[:8]}")
        
        # Generar primera pregunta
        first_question = content_generator.generate_question(difficulty="beginner")
        
        return jsonify({
            "estado": "exito",
            "user_id": user_id,
            "session_id": f"{user_id[:6]}_{int(time.time())}",
            "welcome_message": "🎯 Welcome to Eli! Practice English with AI-generated content!",
            "initial_level": "beginner",
            "initial_question": first_question["question"],
            "initial_question_spanish": first_question["translation"],
            "show_spanish_translation": True,
            "xp": 0,
            "is_dynamic_content": True
        })
    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)[:100]}), 500

# ============================================
# ENDPOINT: PROGRESO
# ============================================
@app.route('/api/progress/save', methods=['POST'])
def save_progress():
    try:
        data = request.json or {}
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"estado": "error", "mensaje": "User ID required"}), 400
        
        progress_db.save_user_progress(user_id, data)
        
        return jsonify({
            "estado": "exito",
            "mensaje": "Progress saved",
            "user_id": user_id
        })
        
    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)[:100]}), 500

@app.route('/api/progress/load', methods=['POST'])
def load_progress():
    try:
        data = request.json or {}
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"estado": "error", "mensaje": "User ID required"}), 400
        
        progress = progress_db.load_user_progress(user_id)
        
        if progress:
            return jsonify({
                "estado": "exito",
                "progress_found": True,
                "user_data": {
                    "user_id": user_id,
                    "current_level": progress.get("current_level", "beginner"),
                    "total_xp": progress.get("total_xp", 0),
                    "total_sessions": len(progress.get("sessions", [])),
                    "last_seen": progress.get("last_seen")
                }
            })
        else:
            return jsonify({
                "estado": "exito",
                "progress_found": False,
                "mensaje": "No previous progress found"
            })
        
    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)[:100]}), 500

# ============================================
# FUNCIONES AUXILIARES
# ============================================
def _detect_tense_in_text(text):
    """Detecta tiempo verbal en texto"""
    text_lower = text.lower()
    
    tense_indicators = {
        "past": ["yesterday", "last", "ago", "was", "were", "did", "had", "went"],
        "future": ["will", "tomorrow", "next", "going to", "gonna"],
        "present_perfect": ["have", "has", "ever", "never", "just", "already"],
        "present_continuous": ["am", "is", "are", "ing"],
        "conditional": ["would", "could", "should", "might"]
    }
    
    for tense, indicators in tense_indicators.items():
        for indicator in indicators:
            if indicator in text_lower:
                return tense
    
    return "present"

def _detect_tense_in_question(question):
    """Detecta tiempo verbal en pregunta"""
    question_lower = question.lower()
    
    if "did" in question_lower:
        return "past"
    elif "will" in question_lower:
        return "future"
    elif "have" in question_lower or "has" in question_lower:
        return "present_perfect"
    elif "are" in question_lower and "ing" in question_lower:
        return "present_continuous"
    elif "would" in question_lower or "could" in question_lower:
        return "conditional"
    else:
        return "present"

def _estimate_user_level(text):
    """Estima nivel del usuario basado en texto"""
    word_count = len(text.split())
    
    if word_count < 3:
        return "beginner"
    elif word_count < 8:
        return "intermediate"
    else:
        return "advanced"

def _validate_translation(user_answer, correct_answer, english_word):
    """Valida traducción de manera flexible"""
    # Normalizar respuestas
    user_norm = user_answer.strip().lower()
    correct_norm = correct_answer.strip().lower()
    
    # Coincidencia exacta
    if user_norm == correct_norm:
        return True
    
    # Coincidencia parcial
    if correct_norm in user_norm or user_norm in correct_norm:
        return True
    
    # Para verbos, verificar formas conjugadas
    verb_equivalents = {
        "comer": ["como", "comes", "come", "comemos", "comen"],
        "beber": ["bebo", "bebes", "bebe", "bebemos", "beben"],
        "estudiar": ["estudio", "estudias", "estudia", "estudiamos", "estudian"]
    }
    
    if english_word in ["eat", "drink", "study"] and user_norm in verb_equivalents.get(correct_norm, []):
        return True
    
    return False

# ============================================
# EJECUCIÓN
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print("🚀 Eli Backend v11.0 - GENERACIÓN DINÁMICA COMPLETA")
    print(f"📡 Running on port: {port}")
    print("=" * 60)
    print("✅ FEATURES:")
    print("   • Dynamic question generation")
    print("   • Tense-based vocabulary")
    print("   • Spanish translations")
    print("   • Grammar explanations")
    print("   • Progress persistence")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)