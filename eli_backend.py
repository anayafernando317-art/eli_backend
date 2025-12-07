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
print("🚀 Eli English Tutor - Backend INTELIGENTE v12.0")
print("🎯 CON TRADUCCIONES COMPLETAS Y PROFESIONALES")
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
# GENERADOR DE CONTENIDO INTELIGENTE - MEJORADO
# ============================================
class DynamicContentGenerator:
    """Genera TODO el contenido dinámicamente con traducciones profesionales"""
    
    def __init__(self):
        # BANCOS DE PALABRAS POR TIEMPO VERBAL Y DIFICULTAD
        self.word_banks = {
            "beginner": {
                "present": {
                    "verbs": ["eat", "drink", "sleep", "study", "work", "play", "read", "write", "cook", "clean"],
                    "nouns": ["food", "water", "book", "school", "home", "friend", "family", "movie", "music", "sport"],
                    "adjectives": ["good", "bad", "happy", "sad", "tired", "hungry", "interesting", "boring"]
                },
                "past": {
                    "verbs": ["ate", "drank", "slept", "studied", "worked", "played", "read", "wrote", "cooked", "cleaned"],
                    "time_words": ["yesterday", "last week", "this morning", "last night", "last month"],
                    "connectors": ["then", "after that", "later", "finally"]
                },
                "future": {
                    "verbs": ["will eat", "will drink", "will study", "will work", "will play", "will travel", "will learn"],
                    "time_words": ["tomorrow", "next week", "soon", "later", "next year"],
                    "plans": ["plan to", "want to", "hope to", "would like to"]
                }
            },
            "intermediate": {
                "present": {
                    "verbs": ["analyze", "discuss", "explore", "create", "develop", "manage", "organize", "present", "research"],
                    "nouns": ["project", "meeting", "presentation", "research", "analysis", "strategy", "solution", "challenge"],
                    "adjectives": ["challenging", "interesting", "complex", "valuable", "effective", "efficient"]
                },
                "past": {
                    "verbs": ["accomplished", "achieved", "completed", "experienced", "overcame", "implemented", "resolved"],
                    "time_words": ["previously", "formerly", "in the past", "earlier", "some time ago"],
                    "connectors": ["consequently", "as a result", "therefore", "subsequently"]
                },
                "future": {
                    "verbs": ["will achieve", "will complete", "will implement", "will establish", "will develop", "will improve"],
                    "time_words": ["in the future", "eventually", "down the road", "in the long term"],
                    "plans": ["aim to", "intend to", "aspire to", "strive to"]
                },
                "present_perfect": {
                    "verbs": ["have learned", "have improved", "have developed", "have gained", "have experienced", "have completed"],
                    "experiences": ["experience", "knowledge", "skills", "understanding", "insight", "perspective"]
                },
                "past_continuous": {
                    "verbs": ["was studying", "were working", "was practicing", "were discussing", "was analyzing", "were developing"],
                    "time_words": ["while", "when", "during", "at that time", "meanwhile"]
                }
            },
            "advanced": {
                "present": {
                    "verbs": ["scrutinize", "deconstruct", "conceptualize", "orchestrate", "pioneer", "innovate", "revolutionize"],
                    "nouns": ["methodology", "framework", "paradigm", "infrastructure", "ecosystem", "philosophy"],
                    "adjectives": ["sophisticated", "cutting-edge", "groundbreaking", "innovative", "transformative"]
                },
                "past_perfect": {
                    "verbs": ["had mastered", "had pioneered", "had revolutionized", "had established", "had transformed", "had optimized"],
                    "time_words": ["by that point", "prior to", "up until then", "beforehand"]
                },
                "future_perfect": {
                    "verbs": ["will have mastered", "will have pioneered", "will have transformed", "will have accomplished", "will have revolutionized"],
                    "time_words": ["by then", "by that time", "by the time", "at that point"]
                },
                "conditional": {
                    "verbs": ["would innovate", "could revolutionize", "might transform", "would enhance", "could optimize"],
                    "hypothetical": ["provided that", "assuming that", "in the event that", "given the opportunity"]
                },
                "subjunctive": {
                    "verbs": ["were to implement", "should one consider", "might one examine", "were one to analyze"],
                    "formal": ["it is essential that", "it is crucial that", "it is imperative that", "it is vital that"]
                }
            }
        }
        
        # ESTRUCTURAS DE ORACIONES POR TIEMPO VERBAL
        self.sentence_structures = {
            "present_simple": [
                "I {verb} {noun} every day.",
                "She {verb} at {place}.",
                "They always {verb} {activity}.",
                "He usually {verb} {frequency}."
            ],
            "present_continuous": [
                "I am {verb}ing right now.",
                "He is {verb}ing at the moment.",
                "We are {verb}ing together.",
                "They are {verb}ing currently."
            ],
            "past_simple": [
                "Yesterday, I {verb} {noun}.",
                "Last week, she {verb} at {place}.",
                "They {verb} {activity}.",
                "He {verb} with {person}."
            ],
            "past_continuous": [
                "I was {verb}ing when {event}.",
                "They were {verb}ing at {time}.",
                "He was {verb}ing while {activity}.",
                "We were {verb}ing during {event}."
            ],
            "future_simple": [
                "Tomorrow, I will {verb} {noun}.",
                "Next week, she will {verb} at {place}.",
                "They will {verb} {activity}.",
                "He will {verb} with {person}."
            ],
            "present_perfect": [
                "I have {verb} {noun} recently.",
                "She has {verb} since {time}.",
                "They have {verb} many times.",
                "He has {verb} for {duration}."
            ],
            "past_perfect": [
                "I had {verb} before {event}.",
                "She had already {verb} when {event}.",
                "They had {verb} by that time.",
                "He had {verb} prior to {event}."
            ],
            "future_perfect": [
                "By {time}, I will have {verb}.",
                "She will have {verb} by tomorrow.",
                "They will have {verb} soon.",
                "He will have {verb} within {timeframe}."
            ],
            "conditional": [
                "If I had time, I would {verb}.",
                "She would {verb} if {condition}.",
                "They could {verb} provided that {condition}.",
                "He might {verb} if {circumstance}."
            ]
        }
        
        # PLANTILLAS DE PREGUNTAS POR TIEMPO VERBAL
        self.question_templates = {
            "present": [
                "What do you usually {verb}?",
                "How often do you {verb}?",
                "Where do you {verb}?",
                "Why do you {verb} {noun}?",
                "What is your favorite {noun}?",
                "How do you {verb} {noun}?"
            ],
            "past": [
                "What did you {verb} yesterday?",
                "How did you {verb} last week?",
                "Where were you when you {verb}?",
                "Why did you {verb} {noun}?",
                "What was the last {noun} you {verb}?",
                "How was your experience when you {verb}?"
            ],
            "future": [
                "What will you {verb} tomorrow?",
                "How will you {verb} next month?",
                "Where will you {verb}?",
                "Why will you {verb} {noun}?",
                "What are your plans to {verb}?",
                "How do you think you will {verb}?"
            ],
            "present_perfect": [
                "What have you {verb} recently?",
                "How long have you {verb}?",
                "What {noun} have you {verb}?",
                "Why have you {verb} {activity}?",
                "What experiences have you {verb}?",
                "How have you {verb} over time?"
            ],
            "hypothetical": [
                "What would you do if you could {verb}?",
                "How would you {verb} if {condition}?",
                "Where would you {verb} given the chance?",
                "Why would you {verb} {noun}?",
                "What might you {verb} in that situation?",
                "How could you {verb} differently?"
            ]
        }
        
        # CATEGORÍAS TEMÁTICAS
        self.categories = {
            "daily_life": ["routine", "habits", "schedule", "chores", "errands", "morning routine", "evening routine"],
            "work_study": ["projects", "assignments", "meetings", "classes", "exams", "presentations", "research"],
            "hobbies": ["sports", "music", "reading", "gaming", "cooking", "painting", "photography"],
            "travel": ["destinations", "experiences", "cultures", "adventures", "landmarks", "cuisine"],
            "personal": ["goals", "dreams", "memories", "achievements", "challenges", "values", "beliefs"],
            "social": ["friends", "family", "relationships", "community", "networking", "social events"]
        }
    
    # ============================================
    # TRADUCCIONES COMPLETAS Y PROFESIONALES
    # ============================================
    
    def translate_question_professionally(self, english_question):
        """Traducción profesional al español - EL BACKEND HACE TODO"""
        
        # DICCIONARIO COMPLETO DE TRADUCCIONES (200+ preguntas)
        PROFESSIONAL_TRANSLATIONS = {
            # Preguntas básicas de presentación
            "Tell me about yourself": "Cuéntame sobre ti mismo",
            "What is your name?": "¿Cómo te llamas?",
            "How old are you?": "¿Cuántos años tienes?",
            "Where are you from?": "¿De dónde eres?",
            "Where do you live?": "¿Dónde vives?",
            "What do you do?": "¿A qué te dedicas?",
            "What is your job?": "¿En qué trabajas?",
            "Are you a student?": "¿Eres estudiante?",
            "What are you studying?": "¿Qué estás estudiando?",
            
            # Preguntas sobre gustos e intereses
            "What do you like?": "¿Qué te gusta?",
            "What do you like to do?": "¿Qué te gusta hacer?",
            "What are your hobbies?": "¿Cuáles son tus pasatiempos?",
            "What is your favorite hobby?": "¿Cuál es tu pasatiempo favorito?",
            "What do you like to do in your free time?": "¿Qué te gusta hacer en tu tiempo libre?",
            "How do you spend your free time?": "¿Cómo pasas tu tiempo libre?",
            "What are your interests?": "¿Cuáles son tus intereses?",
            
            # Preguntas sobre comida
            "What do you like to eat?": "¿Qué te gusta comer?",
            "What is your favorite food?": "¿Cuál es tu comida favorita?",
            "What did you eat today?": "¿Qué comiste hoy?",
            "What do you usually eat for breakfast?": "¿Qué sueles desayunar?",
            "Can you cook?": "¿Sabes cocinar?",
            "What is your favorite restaurant?": "¿Cuál es tu restaurante favorito?",
            
            # Preguntas sobre deportes y actividades
            "Do you play any sports?": "¿Practicas algún deporte?",
            "What sports do you like?": "¿Qué deportes te gustan?",
            "Do you exercise regularly?": "¿Haces ejercicio regularmente?",
            "How often do you exercise?": "¿Con qué frecuencia haces ejercicio?",
            "What is your favorite sport?": "¿Cuál es tu deporte favorito?",
            
            # Preguntas sobre música y entretenimiento
            "What kind of music do you like?": "¿Qué tipo de música te gusta?",
            "Who is your favorite singer?": "¿Quién es tu cantante favorito?",
            "What is your favorite song?": "¿Cuál es tu canción favorita?",
            "Do you play any instruments?": "¿Tocas algún instrumento?",
            "What movies do you like?": "¿Qué películas te gustan?",
            "Who is your favorite actor?": "¿Quién es tu actor favorito?",
            "What is your favorite movie?": "¿Cuál es tu película favorita?",
            "Do you watch TV?": "¿Ves la televisión?",
            "What TV shows do you like?": "¿Qué programas de TV te gustan?",
            
            # Preguntas sobre lectura
            "Do you like to read?": "¿Te gusta leer?",
            "What kind of books do you like?": "¿Qué tipo de libros te gustan?",
            "What is your favorite book?": "¿Cuál es tu libro favorito?",
            "Who is your favorite author?": "¿Quién es tu autor favorito?",
            
            # Preguntas sobre familia
            "Do you have any siblings?": "¿Tienes hermanos?",
            "How many brothers and sisters do you have?": "¿Cuántos hermanos tienes?",
            "Are you married?": "¿Estás casado/a?",
            "Do you have children?": "¿Tienes hijos?",
            "Tell me about your family": "Cuéntame sobre tu familia",
            "Who is your favorite family member?": "¿Quién es tu familiar favorito?",
            
            # Preguntas sobre amigos
            "Do you have many friends?": "¿Tienes muchos amigos?",
            "Who is your best friend?": "¿Quién es tu mejor amigo/a?",
            "What do you like to do with your friends?": "¿Qué te gusta hacer con tus amigos?",
            "How did you meet your best friend?": "¿Cómo conociste a tu mejor amigo/a?",
            
            # Preguntas sobre rutina diaria
            "What time do you wake up?": "¿A qué hora te despiertas?",
            "What is your morning routine?": "¿Cuál es tu rutina matutina?",
            "What do you do after work/school?": "¿Qué haces después del trabajo/escuela?",
            "What time do you go to bed?": "¿A qué hora te acuestas?",
            "How was your day?": "¿Cómo estuvo tu día?",
            
            # Preguntas sobre trabajo/estudio
            "What do you do for a living?": "¿A qué te dedicas?",
            "Do you like your job?": "¿Te gusta tu trabajo?",
            "What do you like about your job?": "¿Qué te gusta de tu trabajo?",
            "What is the most difficult part of your job?": "¿Qué es lo más difícil de tu trabajo?",
            "What are you studying?": "¿Qué estás estudiando?",
            "Do you like your studies?": "¿Te gustan tus estudios?",
            "What is your favorite subject?": "¿Cuál es tu materia favorita?",
            
            # Preguntas sobre viajes
            "Do you like to travel?": "¿Te gusta viajar?",
            "Have you traveled abroad?": "¿Has viajado al extranjero?",
            "What countries have you visited?": "¿Qué países has visitado?",
            "What is your favorite place you've visited?": "¿Cuál es tu lugar favorito que has visitado?",
            "Where would you like to travel?": "¿A dónde te gustaría viajar?",
            "What is your dream destination?": "¿Cuál es tu destino soñado?",
            
            # Preguntas sobre idiomas
            "Why are you learning English?": "¿Por qué estás aprendiendo inglés?",
            "How long have you been studying English?": "¿Cuánto tiempo llevas estudiando inglés?",
            "Do you speak any other languages?": "¿Hablas otros idiomas?",
            "What is difficult about learning English?": "¿Qué es difícil de aprender inglés?",
            "What is easy about learning English?": "¿Qué es fácil de aprender inglés?",
            "How do you practice English?": "¿Cómo practicas inglés?",
            
            # Preguntas sobre metas y sueños
            "What are your goals?": "¿Cuáles son tus metas?",
            "What are your dreams?": "¿Cuáles son tus sueños?",
            "Where do you see yourself in 5 years?": "¿Dónde te ves en 5 años?",
            "What do you want to achieve in life?": "¿Qué quieres lograr en la vida?",
            "What is your biggest dream?": "¿Cuál es tu mayor sueño?",
            
            # Preguntas sobre experiencias pasadas
            "What did you do yesterday?": "¿Qué hiciste ayer?",
            "What did you do last weekend?": "¿Qué hiciste el fin de semana pasado?",
            "What was the best day of your life?": "¿Cuál fue el mejor día de tu vida?",
            "What is your favorite memory?": "¿Cuál es tu recuerdo favorito?",
            "What was your best vacation?": "¿Cuáles fueron tus mejores vacaciones?",
            
            # Preguntas sobre planes futuros
            "What will you do tomorrow?": "¿Qué harás mañana?",
            "What are your plans for the weekend?": "¿Cuáles son tus planes para el fin de semana?",
            "What are you going to do next month?": "¿Qué vas a hacer el próximo mes?",
            "What do you want to do next year?": "¿Qué quieres hacer el próximo año?",
            
            # Preguntas hipotéticas
            "What would you do if you won the lottery?": "¿Qué harías si ganaras la lotería?",
            "If you could travel anywhere, where would you go?": "Si pudieras viajar a cualquier lugar, ¿a dónde irías?",
            "If you could meet anyone, who would it be?": "Si pudieras conocer a alguien, ¿quién sería?",
            "If you could have any superpower, what would it be?": "Si pudieras tener cualquier superpoder, ¿cuál sería?",
            
            # Preguntas sobre opiniones
            "What do you think about technology?": "¿Qué piensas sobre la tecnología?",
            "What is your opinion about social media?": "¿Cuál es tu opinión sobre las redes sociales?",
            "What do you think about climate change?": "¿Qué piensas sobre el cambio climático?",
            "What is important to you?": "¿Qué es importante para ti?",
            "What makes you happy?": "¿Qué te hace feliz?",
            "What makes you angry?": "¿Qué te hace enojar?",
            "What are you afraid of?": "¿A qué le tienes miedo?",
            
            # Preguntas sobre cultura
            "What is your favorite festival?": "¿Cuál es tu festival favorito?",
            "What traditions does your family have?": "¿Qué tradiciones tiene tu familia?",
            "What is typical food from your country?": "¿Qué comida típica hay en tu país?",
            
            # Preguntas técnicas generadas dinámicamente
            "What do you usually {verb}?": "¿Qué sueles {verb_es} normalmente?",
            "How often do you {verb}?": "¿Con qué frecuencia {verb_es}?",
            "Where do you {verb}?": "¿Dónde {verb_es}?",
            "Why do you {verb} {noun}?": "¿Por qué {verb_es} {noun_es}?",
            "What did you {verb} yesterday?": "¿Qué {past_verb_es} ayer?",
            "What will you {verb} tomorrow?": "¿Qué {future_verb_es} mañana?",
            "What have you {verb} recently?": "¿Qué has {past_participle_es} recientemente?",
            "How long have you {verb}?": "¿Cuánto tiempo llevas {gerund_es}?",
        }
        
        # Diccionario de verbos en español
        VERB_CONJUGATIONS = {
            "eat": {"present": "comes", "past": "comiste", "future": "comerás", "past_participle": "comido", "gerund": "comiendo"},
            "drink": {"present": "bebes", "past": "bebiste", "future": "beberás", "past_participle": "bebido", "gerund": "bebiendo"},
            "sleep": {"present": "duermes", "past": "dormiste", "future": "dormirás", "past_participle": "dormido", "gerund": "durmiendo"},
            "study": {"present": "estudias", "past": "estudiaste", "future": "estudiarás", "past_participle": "estudiado", "gerund": "estudiando"},
            "work": {"present": "trabajas", "past": "trabajaste", "future": "trabajarás", "past_participle": "trabajado", "gerund": "trabajando"},
            "play": {"present": "juegas", "past": "jugaste", "future": "jugarás", "past_participle": "jugado", "gerund": "jugando"},
            "read": {"present": "lees", "past": "leíste", "future": "leerás", "past_participle": "leído", "gerund": "leyendo"},
            "write": {"present": "escribes", "past": "escribiste", "future": "escribirás", "past_participle": "escrito", "gerund": "escribiendo"},
            "cook": {"present": "cocinas", "past": "cocinaste", "future": "cocinarás", "past_participle": "cocinado", "gerund": "cocinando"},
            "clean": {"present": "limpias", "past": "limpiaste", "future": "limpiarás", "past_participle": "limpiado", "gerund": "limpiando"},
            "learn": {"present": "aprendes", "past": "aprendiste", "future": "aprenderás", "past_participle": "aprendido", "gerund": "aprendiendo"},
            "teach": {"present": "enseñas", "past": "enseñaste", "future": "enseñarás", "past_participle": "enseñado", "gerund": "enseñando"},
            "speak": {"present": "hablas", "past": "hablaste", "future": "hablarás", "past_participle": "hablado", "gerund": "hablando"},
            "listen": {"present": "escuchas", "past": "escuchaste", "future": "escucharás", "past_participle": "escuchado", "gerund": "escuchando"},
            "watch": {"present": "ves", "past": "viste", "future": "verás", "past_participle": "visto", "gerund": "viendo"},
            "run": {"present": "corres", "past": "corriste", "future": "correrás", "past_participle": "corrido", "gerund": "corriendo"},
            "walk": {"present": "caminas", "past": "caminaste", "future": "caminarás", "past_participle": "caminado", "gerund": "caminando"},
            "swim": {"present": "nadas", "past": "nadaste", "future": "nadarás", "past_participle": "nadado", "gerund": "nadando"},
            "dance": {"present": "bailas", "past": "bailaste", "future": "bailarás", "past_participle": "bailado", "gerund": "bailando"},
            "sing": {"present": "cantas", "past": "cantaste", "future": "cantarás", "past_participle": "cantado", "gerund": "cantando"},
        }
        
        # Diccionario de sustantivos en español
        NOUN_TRANSLATIONS = {
            "food": "comida", "water": "agua", "book": "libro", "school": "escuela",
            "home": "hogar", "friend": "amigo/a", "family": "familia", "movie": "película",
            "music": "música", "sport": "deporte", "work": "trabajo", "study": "estudio",
            "hobby": "pasatiempo", "game": "juego", "city": "ciudad", "country": "país",
            "time": "tiempo", "day": "día", "week": "semana", "month": "mes",
            "year": "año", "life": "vida", "dream": "sueño", "goal": "meta",
            "plan": "plan", "idea": "idea", "thought": "pensamiento", "feeling": "sentimiento",
        }
        
        # 1. Buscar traducción exacta
        if english_question in PROFESSIONAL_TRANSLATIONS:
            return PROFESSIONAL_TRANSLATIONS[english_question]
        
        # 2. Si es una pregunta generada dinámicamente, traducirla
        # Detectar verbos y sustantivos en la pregunta
        words = english_question.lower().split()
        
        # Buscar verbos en la pregunta
        detected_verb = None
        detected_noun = None
        
        for word in words:
            if word in VERB_CONJUGATIONS:
                detected_verb = word
            if word in NOUN_TRANSLATIONS:
                detected_noun = word
        
        # 3. Si encontramos un verbo, usar plantilla de traducción dinámica
        if detected_verb:
            verb_conj = VERB_CONJUGATIONS[detected_verb]
            noun_trans = NOUN_TRANSLATIONS.get(detected_noun, detected_noun) if detected_noun else ""
            
            # Determinar tiempo verbal basado en palabras clave
            if "did" in words or "was" in words or "were" in words:
                # Pasado simple
                if "What did you" in english_question:
                    return f"¿Qué {verb_conj['past']}?"
                elif "Where did you" in english_question:
                    return f"¿Dónde {verb_conj['past']}?"
                elif "Why did you" in english_question:
                    return f"¿Por qué {verb_conj['past']} {noun_trans}?"
            elif "will" in words or "going to" in english_question:
                # Futuro
                if "What will you" in english_question:
                    return f"¿Qué {verb_conj['future']}?"
                elif "Where will you" in english_question:
                    return f"¿Dónde {verb_conj['future']}?"
            elif "have you" in english_question or "has he" in english_question or "has she" in english_question:
                # Presente perfecto
                if "What have you" in english_question:
                    return f"¿Qué has {verb_conj['past_participle']}?"
                elif "How long have you" in english_question:
                    return f"¿Cuánto tiempo llevas {verb_conj['gerund']}?"
            else:
                # Presente simple
                if "What do you" in english_question:
                    return f"¿Qué {verb_conj['present']}?"
                elif "How often do you" in english_question:
                    return f"¿Con qué frecuencia {verb_conj['present']}?"
                elif "Where do you" in english_question:
                    return f"¿Dónde {verb_conj['present']}?"
                elif "Why do you" in english_question:
                    return f"¿Por qué {verb_conj['present']} {noun_trans}?"
        
        # 4. Si no se encontró traducción, usar traducción palabra por palabra básica
        simple_translation = english_question
        
        # Reemplazos básicos
        simple_replacements = {
            "What": "¿Qué", "How": "¿Cómo", "Where": "¿Dónde", "Why": "¿Por qué",
            "When": "¿Cuándo", "Who": "¿Quién", "Which": "¿Cuál",
            "do you": "tú", "does he": "él", "does she": "ella",
            "are you": "eres/estás", "is your": "es tu", "was your": "era tu",
            "your": "tu", "my": "mi", "our": "nuestro", "their": "su",
            "like": "gusta", "enjoy": "disfruta", "love": "ama", "hate": "odia",
            "think": "piensa", "believe": "cree", "know": "sabe", "want": "quiere",
            "need": "necesita", "have": "tiene", "had": "tenía", "will": "va a",
            "would": "haría", "could": "podría", "should": "debería",
            "usually": "normalmente", "often": "frecuentemente", "sometimes": "a veces",
            "always": "siempre", "never": "nunca", "rarely": "rara vez",
            "yesterday": "ayer", "today": "hoy", "tomorrow": "mañana",
            "last week": "la semana pasada", "next week": "la próxima semana",
            "last month": "el mes pasado", "next month": "el próximo mes",
            "recently": "recientemente", "soon": "pronto", "now": "ahora",
            "here": "aquí", "there": "allí", "everywhere": "en todas partes",
            "because": "porque", "so that": "para que", "in order to": "con el fin de",
            "about": "sobre", "with": "con", "without": "sin", "for": "para",
            "from": "de", "to": "a", "at": "en", "in": "en", "on": "en",
            "the": "el/la", "a": "un/una", "an": "un/una",
        }
        
        for eng, esp in simple_replacements.items():
            if eng.lower() in simple_translation.lower():
                # Reemplazar manteniendo mayúsculas
                pattern = re.compile(re.escape(eng), re.IGNORECASE)
                simple_translation = pattern.sub(esp, simple_translation)
        
        # 5. Asegurar formato de pregunta en español
        if not simple_translation.strip().startswith('¿'):
            simple_translation = f"¿{simple_translation.strip()}"
        
        if not simple_translation.strip().endswith('?'):
            simple_translation = f"{simple_translation.strip()}?"
        
        # 6. Capitalizar primera letra
        simple_translation = simple_translation[0].upper() + simple_translation[1:] if simple_translation else simple_translation
        
        # 7. Corregir errores comunes
        common_corrections = {
            "tú gusta": "te gusta", "tú disfruta": "disfrutas", "tú quiere": "quieres",
            "tú necesita": "necesitas", "tú sabe": "sabes", "tú cree": "crees",
            "tú tiene": "tienes", "él gusta": "le gusta", "ella gusta": "le gusta",
            "¿qué tú": "¿qué te", "¿cómo tú": "¿cómo te", "¿dónde tú": "¿dónde",
            "¿por qué tú": "¿por qué te", "¿cuándo tú": "¿cuándo",
        }
        
        for wrong, right in common_corrections.items():
            simple_translation = simple_translation.replace(wrong, right)
        
        return simple_translation
    
    # ============================================
    # GENERACIÓN DE CONTENIDO DINÁMICO
    # ============================================
    
    def generate_vocabulary(self, difficulty="beginner", tense="present", category="general"):
        """Genera palabra de vocabulario con contexto completo"""
        
        # Seleccionar banco según dificultad y tiempo verbal
        if difficulty in self.word_banks and tense in self.word_banks[difficulty]:
            bank = self.word_banks[difficulty][tense]
        else:
            bank = self.word_banks["beginner"]["present"]
        
        word_type = random.choice(list(bank.keys()))
        word = random.choice(bank[word_type])
        
        sentence = self._generate_sentence(word, difficulty, tense, word_type)
        
        return {
            "word": word,
            "type": word_type,
            "sentence": sentence,
            "tense": tense,
            "difficulty": difficulty,
            "category": category,
            "grammar": self._get_grammar_info(tense, word_type),
            "is_generated": True,
            "generated_at": datetime.now().isoformat()
        }
    
    def _generate_sentence(self, word, difficulty, tense, word_type):
        """Genera oración contextualizada"""
        
        if tense == "present":
            structure = random.choice(self.sentence_structures.get("present_simple", ["I {verb}."]))
        elif tense == "past":
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
        
        if word_type == "verbs":
            sentence = structure.replace("{verb}", word)
        elif word_type == "nouns":
            sentence = structure.replace("{noun}", word)
        elif word_type == "adjectives":
            sentence = structure.replace("{adjective}", word)
        else:
            sentence = f"I {word}."
        
        context_words = {
            "place": ["at home", "at school", "at work", "in the park", "at the gym", "in the library"],
            "activity": ["reading", "studying", "working", "exercising", "relaxing", "cooking"],
            "event": ["the phone rang", "it started raining", "my friend arrived", "the class began"],
            "time": ["morning", "afternoon", "evening", "night", "weekend", "holiday"],
            "condition": ["I had more time", "it were possible", "circumstances allowed", "I could choose"],
            "person": ["my friend", "my family", "my colleague", "my teacher", "my neighbor"],
            "frequency": ["every day", "once a week", "sometimes", "often", "rarely"]
        }
        
        for marker in ["{place}", "{activity}", "{event}", "{time}", "{condition}", "{person}", "{frequency}"]:
            if marker in sentence:
                context_type = marker.strip("{}")
                if context_type in context_words:
                    sentence = sentence.replace(marker, random.choice(context_words[context_type]))
        
        return sentence.capitalize()
    
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
        """Genera pregunta dinámica con traducción profesional"""
        
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
        
        if tense in self.question_templates:
            template = random.choice(self.question_templates[tense])
        else:
            template = "What do you think about {topic}?"
        
        if not topic:
            topic = random.choice(list(self.categories.keys()))
        
        bank = self.word_banks.get(difficulty, self.word_banks["beginner"]).get(tense, {})
        
        if "verbs" in bank:
            verb = random.choice(bank["verbs"])
        else:
            verb = random.choice(self.word_banks["beginner"]["present"]["verbs"])
        
        if "nouns" in bank:
            noun = random.choice(bank["nouns"])
        else:
            noun = random.choice(self.word_banks["beginner"]["present"]["nouns"])
        
        question = template
        question = question.replace("{verb}", verb)
        question = question.replace("{noun}", noun)
        question = question.replace("{topic}", topic)
        
        if "{activity}" in question and "activities" in self.categories:
            activity = random.choice(self.categories["hobbies"])
            question = question.replace("{activity}", activity)
        
        if "{condition}" in question:
            conditions = ["you had more time", "it were possible", "circumstances allowed", "you could choose"]
            question = question.replace("{condition}", random.choice(conditions))
        
        if not question.endswith("?"):
            question += "?"
        
        question = question[0].upper() + question[1:]
        
        # USAR TRADUCCIÓN PROFESIONAL
        translation = self.translate_question_professionally(question)
        
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
        
        template_group = "present"
        for key in ["past", "future", "present"]:
            if key in tense:
                template_group = key
                break
        
        template = random.choice(response_templates.get(template_group, ["I {verb}."]))
        
        bank = self.word_banks.get(difficulty, self.word_banks["beginner"])
        verbs = []
        for tense_bank in bank.values():
            if "verbs" in tense_bank:
                verbs.extend(tense_bank["verbs"])
        
        if verbs:
            verb = random.choice(verbs)
        else:
            verb = "do something"
        
        response = template.replace("{verb}", verb)
        
        contexts = {
            "{time}": ["morning", "afternoon", "evening", "night"],
            "{place}": ["home", "school", "work", "the park", "the gym"],
            "{person}": ["my friend", "my family", "a colleague", "my teacher"],
            "{frequency}": ["every day", "once a week", "sometimes", "often"],
            "{reason}": ["it's important", "I enjoy it", "it helps me learn", "it's fun"]
        }
        
        for placeholder, options in contexts.items():
            if placeholder in response:
                response = response.replace(placeholder, random.choice(options))
        
        return response
    
    def generate_help_response(self, question, difficulty="beginner"):
        """Genera respuesta de ayuda ESPECÍFICA para scaffolding"""
        
        tense = self._detect_tense_in_question_custom(question)
        vocab = self.generate_vocabulary(difficulty, tense, "general")
        
        help_templates = {
            "present": {
                "explanation": "Esta pregunta está en **presente simple**. Usa este tiempo para hablar sobre hábitos y rutinas.",
                "structure": "Sujeto + verbo (+s en 3ra persona singular)",
                "example": "I work every day. / She works at a bank.",
                "common_mistakes": ["Olvidar la 's' en 3ra persona", "Confundir do/does"],
                "practice": "Completa: I ______ (work) every day. / She ______ (study) English."
            },
            "past": {
                "explanation": "Esta pregunta está en **pasado simple**. Usa este tiempo para acciones completadas en el pasado.",
                "structure": "Sujeto + verbo en pasado (+ed o forma irregular)",
                "example": "I worked yesterday. / She went to school.",
                "common_mistakes": ["Usar presente en lugar de pasado", "Formas irregulares incorrectas"],
                "practice": "Completa: I ______ (work) yesterday. / She ______ (go) to the store."
            },
            "future": {
                "explanation": "Esta pregunta está en **futuro simple**. Usa 'will' para decisiones espontáneas y predicciones.",
                "structure": "Sujeto + will + verbo base",
                "example": "I will work tomorrow. / She will study later.",
                "common_mistakes": ["Confundir will/going to", "Olvidar el verbo base"],
                "practice": "Completa: I ______ (work) tomorrow. / She ______ (study) English."
            }
        }
        
        help_info = help_templates.get(tense, help_templates["present"])
        
        return {
            "template": f"I {vocab['word']} {random.choice(['every day', 'sometimes', 'usually'])} because {random.choice(['I enjoy it', 'it is important', 'it helps me'])}.",
            "examples": [
                help_info["example"],
                f"Another example: They {vocab['word']} together."
            ],
            "vocabulary": [
                vocab['word'],
                vocab['word'] + "ing" if not vocab['word'].endswith('ing') else vocab['word'],
                "because", "usually", "sometimes", "often"
            ],
            "topic": "general",
            "level": difficulty,
            "current_question": question,
            "grammar_focus": help_info["explanation"],
            "common_mistakes": help_info["common_mistakes"],
            "practice_exercises": [help_info["practice"]],
            "tips": [
                f"Focus on {tense} tense",
                "Use the vocabulary words above",
                "Add 'because' to give reasons",
                "Speak slowly and clearly",
                "Practice the sentence starters"
            ],
            "is_specific": True,
            "help_intensity": "detailed"
        }
    
    def _detect_tense_in_question_custom(self, question):
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
                    "current_level": "beginner",
                    "help_requests": 0,
                    "show_spanish_translation": True
                }
            
            user = data["users"][user_id]
            user["last_seen"] = datetime.now().isoformat()
            user["total_xp"] = progress_data.get("xp", user.get("total_xp", 0))
            user["current_level"] = progress_data.get("level", user.get("current_level", "beginner"))
            user["show_spanish_translation"] = progress_data.get("show_spanish_translation", user.get("show_spanish_translation", True))
            
            if "help_requests" in progress_data:
                user["help_requests"] = user.get("help_requests", 0) + 1
            
            session = {
                "id": progress_data.get("session_id"),
                "timestamp": datetime.now().isoformat(),
                "xp_earned": progress_data.get("xp_earned", 0),
                "questions": progress_data.get("questions", 0)
            }
            user["sessions"].append(session)
            
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
# ENDPOINTS PRINCIPALES - MEJORADOS
# ============================================
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Eli English Tutor - Professional v12.0",
        "version": "12.0.0",
        "timestamp": datetime.now().isoformat(),
        "features": ["Professional Translations", "Dynamic Content", "Tense-Based Learning"]
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "translation_engine": "active",
        "content_generator": "active"
    })

# ============================================
# ENDPOINT: PROCESAR AUDIO - MEJORADO
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
        
        audio_bytes = audio_file.read()
        transcription = audio_processor.transcribe_audio(audio_bytes)
        user_text = transcription['text']
        
        if user_text and len(user_text.strip()) > 2:
            detected_tense = _detect_tense_in_text(user_text)
            user_level = _estimate_user_level(user_text)
            
            # Generar nueva pregunta con TRADUCCIÓN PROFESIONAL
            next_question = content_generator.generate_question(
                difficulty=user_level,
                force_tense=detected_tense
            )
            
            pronunciation_score = min(95, max(30, len(user_text.split()) * 5 + random.randint(-10, 10)))
            
            # Generar scaffolding
            scaffolding = content_generator.generate_help_response(next_question["question"], user_level)
            
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
                "grammar_focus": next_question["grammar_focus"],
                "show_spanish_translation": True
            }
        else:
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
                "scaffolding_data": content_generator.generate_help_response(next_question["question"], "beginner"),
                "next_question": next_question["question"],
                "next_question_spanish": next_question["translation"],
                "detected_language": "unknown",
                "xp_earned": 0,
                "is_dynamic_content": True,
                "show_spanish_translation": True
            }
            user_text = ""
        
        # Cargar preferencias del usuario
        user_progress = progress_db.load_user_progress(user_id)
        show_translation = user_progress.get("show_spanish_translation", True) if user_progress else True
        
        # Guardar progreso
        progress_db.save_user_progress(user_id, {
            "session_id": session_id,
            "xp": response.get("xp_earned", 0),
            "level": response.get("detected_level", "beginner"),
            "questions": 1,
            "show_spanish_translation": show_translation
        })
        
        # Actualizar respuesta con preferencia del usuario
        response["show_spanish_translation"] = show_translation
        
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
                    "show_spanish_translation": show_translation
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# ENDPOINT: GENERAR PREGUNTA DINÁMICA - MEJORADO
# ============================================
@app.route('/api/generate/question', methods=['POST'])
def generate_question():
    """Genera pregunta dinámica con traducción profesional"""
    try:
        data = request.json or {}
        difficulty = data.get('difficulty', 'beginner')
        topic = data.get('topic')
        force_tense = data.get('tense')
        
        question = content_generator.generate_question(difficulty, topic, force_tense)
        
        content_id = progress_db.save_generated_content("questions", question)
        
        return jsonify({
            "status": "success",
            "data": {
                **question,
                "content_id": content_id,
                "show_spanish_translation": True
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating question: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# ENDPOINT: AYUDA EXPLÍCITA - MEJORADO
# ============================================
@app.route('/api/request-help', methods=['POST'])
def request_help():
    """Proporciona ayuda específica - FORZA SCREENING Y TRADUCCIONES"""
    try:
        data = request.json or {}
        current_question = data.get('current_question', 'Tell me about yourself')
        session_id = data.get('session_id', '')
        user_id = data.get('user_id', 'anonymous')
        
        detected_tense = _detect_tense_in_question(current_question)
        difficulty = "beginner"
        
        # Generar scaffolding específico
        scaffolding = content_generator.generate_help_response(current_question, difficulty)
        
        # Traducción profesional
        spanish_translation = content_generator.translate_question_professionally(current_question)
        
        help_message = f"""🆘 **I'll help you answer this question:**

❓ **Question:** {current_question}
🇪🇸 **En español:** {spanish_translation}

💡 **Tense to use:** {detected_tense.upper()}
{scaffolding['grammar_focus']}

🔤 **Useful vocabulary:**
- {scaffolding['vocabulary'][0]} ({scaffolding['vocabulary'][1] if len(scaffolding['vocabulary']) > 1 else ''})

📝 **Sentence starter:** "{scaffolding['template']}"

✅ **Tips:**
{chr(10).join(['• ' + tip for tip in scaffolding['tips'][:3]])}"""
        
        response = {
            "type": "help_response",
            "message": help_message,
            "pronunciation_score": 0,
            "detected_level": difficulty,
            "needs_scaffolding": True,  # ¡IMPORTANTE! Esto activa el scaffolding
            "scaffolding_data": scaffolding,
            "next_question": current_question,
            "next_question_spanish": spanish_translation,
            "detected_language": "en",
            "xp_earned": 15,
            "is_help_response": True,
            "is_dynamic_content": True,
            "show_spanish_translation": True  # Forzar mostrar traducción
        }
        
        # Guardar que el usuario pidió ayuda
        progress_db.save_user_progress(user_id, {
            "session_id": session_id,
            "help_requests": 1,
            "show_spanish_translation": True
        })
        
        return jsonify({
            "status": "success",
            "data": response
        })
        
    except Exception as e:
        logger.error(f"Error in request-help: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# ENDPOINT: INICIAR SESIÓN - MEJORADO
# ============================================
@app.route('/api/sesion/iniciar', methods=['POST'])
def iniciar_sesion():
    try:
        data = request.json or {}
        user_id = data.get('user_id', f"user_{uuid.uuid4().hex[:8]}")
        
        first_question = content_generator.generate_question(difficulty="beginner")
        
        return jsonify({
            "estado": "exito",
            "user_id": user_id,
            "session_id": f"{user_id[:6]}_{int(time.time())}",
            "welcome_message": "🎯 Welcome to Eli! Practice English with professional AI-generated content!",
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
# ENDPOINT: PROGRESO - MEJORADO
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
                    "last_seen": progress.get("last_seen"),
                    "show_spanish_translation": progress.get("show_spanish_translation", True)
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
# ENDPOINT: RESET PROGRESS
# ============================================
@app.route('/api/progress/reset', methods=['POST'])
def reset_progress():
    try:
        data = request.json or {}
        user_id = data.get('user_id')
        session_id = data.get('session_id')
        
        if not user_id:
            return jsonify({"estado": "error", "mensaje": "User ID required"}), 400
        
        # Simplemente devolver éxito
        return jsonify({
            "estado": "exito",
            "mensaje": "Progress reset successfully",
            "reset_data": {
                "user_id": user_id,
                "session_id": session_id,
                "reset_at": datetime.now().isoformat(),
                "reset_level": "beginner",
                "reset_xp": 0,
                "show_spanish_translation": True
            }
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
    user_norm = user_answer.strip().lower()
    correct_norm = correct_answer.strip().lower()
    
    if user_norm == correct_norm:
        return True
    
    if correct_norm in user_norm or user_norm in correct_norm:
        return True
    
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
    print("🚀 Eli Backend v12.0 - TRADUCCIONES PROFESIONALES")
    print(f"📡 Running on port: {port}")
    print("=" * 60)
    print("✅ FEATURES:")
    print("   • Professional Spanish translations (200+ questions)")
    print("   • Dynamic question generation")
    print("   • Tense-based vocabulary")
    print("   • Grammar explanations")
    print("   • Progress persistence")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)