import google.generativeai as genai
import os
from moviepy.editor import AudioFileClip, ColorClip, CompositeVideoClip, TextClip, concatenate_audioclips
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout
import random
import requests
import json
import re

# --- Konfigurasi ---
GOOGLE_API_KEY = "AIzaSyBDP8S_UKUwLrUoZyWbfeqU1mX8Ams-ZZ0"  # Ganti dengan kunci API Anda
ELEVENLABS_API_KEY = "sk_1a88d281fe94c7b953637c292ea50bb2a6bdd6a111e9695e"  # Kunci API ElevenLabs Anda
ELEVENLABS_VOICE_ID = "RWiGLY9uXI70QL540WNd"  # Contoh ID suara - ganti sesuai keinginan
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')  # Coba model ini
OUTPUT_FILENAME = "gemini_video.mp4"
FONT = 'Impact'
FONT_SIZE = 50
TEXT_COLORS = ['red', 'blue', 'green', 'orange', 'purple', 'black']
ANIMATION_DURATION = 0.2
VIDEO_SIZE = (1280, 720)
BACKGROUND_COLOR = (255, 255, 255)
FPS = 24

# --- Langkah 1: Generate Frasa Cerita dari Gemini ---
PROMPT = """Buatlah sebuah cerita singkat lucu unik dengan plot twist sekitar 150 kata dengan gaya bahasa santai. Jadikan agar ceritanya ekspresif saat di bacakan dengan text-to-speech. Bagilah cerita ini menjadi frasa frasa kecil yang naratif. Sajikan output hanya dalam format JSON array string. Contoh: ["Frasa pertama.", "Ini frasa kedua.", "dan seterusnya"] Jangan menyertakan penjelasan atau teks lain selain JSON array tersebut, tidak perlu menyertakan nama format dan simbol tambahan diluar dari JSON nya."""

try:
    response = model.generate_content(PROMPT)
    frasa_list = []
    if response.parts:
        response_text = response.parts[0].text.strip()
        response_text = response_text.replace('\u00a0', ' ') # Ganti karakter whitespace khusus dengan spasi biasa
        response_text = re.sub(r'^```json\n*', '', response_text) # Hapus ```json di awal
        response_text = re.sub(r'\n*```$', '', response_text) # Hapus ``` di akhir
        response_text = response_text.strip() # Hapus lagi whitespace setelah pembersihan

        try:
            frasa_list = json.loads(response_text)
            if isinstance(frasa_list, list):
                print("Frasa dari Gemini:\n", frasa_list)
            else:
                print("Gagal memproses respons Gemini sebagai list JSON.")
                print("Respons asli setelah pembersihan:\n", response_text)
                exit()
        except json.JSONDecodeError as e:
            print("Respons Gemini tidak sesuai format JSON array yang diharapkan setelah pembersihan.")
            print(f"Error JSON: {e}")
            print("Respons asli sebelum pembersihan:\n", response.parts[0].text)
            print("Respons asli setelah pembersihan:\n", response_text)
            exit()
    else:
        print("Gagal menghasilkan cerita dari Gemini: Respon tidak memiliki bagian.")
        exit()

except Exception as e:
    print(f"Terjadi kesalahan saat menghubungi Gemini API: {e}")
    exit()

# --- Langkah 2: Hasilkan Audio dengan ElevenLabs per Frasa ---
audio_clips = []
audio_durations = []
for i, frasa in enumerate(frasa_list):
    audio_filename = f"frasa_{i}.mp3"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}?output_format=mp3_44100_128"
    headers = {
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": frasa,
        "model_id": ELEVENLABS_MODEL_ID
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        with open(audio_filename, "wb") as f:
            f.write(response.content)
        audio_clip = AudioFileClip(audio_filename)
        audio_clips.append(audio_clip)
        audio_durations.append(audio_clip.duration)
        os.remove(audio_filename) # Hapus file audio sementara setelah digunakan
    except requests.exceptions.RequestException as e:
        print(f"Terjadi kesalahan saat menghubungi API ElevenLabs untuk frasa '{frasa}': {e}")
        exit()
    except Exception as e:
        print(f"Terjadi kesalahan saat menghasilkan audio untuk frasa '{frasa}': {e}")
        exit()

total_audio_duration = sum(audio_durations)

# --- Langkah 3: Buat Klip Teks per Frasa ---
clips = []
current_time = 0
for i, frasa in enumerate(frasa_list):
    color = random.choice(TEXT_COLORS)
    duration = audio_durations[i]

    text_clip = TextClip(
        frasa,
        font=FONT,
        fontsize=FONT_SIZE,
        color=color,
        stroke_color='black',
        stroke_width=2,
        method='caption',
        align='center'
    ).set_duration(duration).fx(fadein, ANIMATION_DURATION).fx(fadeout, ANIMATION_DURATION)

    text_clip = text_clip.set_position(('center', 'center')).set_start(current_time)
    clips.append(text_clip)
    current_time += duration

# --- Langkah 4: Gabungkan Klip Video ---
video_clip = ColorClip(size=VIDEO_SIZE, color=BACKGROUND_COLOR, duration=total_audio_duration)
final_clip = CompositeVideoClip([video_clip] + clips).set_audio(concatenate_audioclips(audio_clips))
final_clip.write_videofile(OUTPUT_FILENAME, fps=FPS)

print(f"\nVideo '{OUTPUT_FILENAME}' berhasil dibuat dengan audio dan teks per frasa.")