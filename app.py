import os
import json
from flask import Flask, request, send_file
from moviepy.editor import *
# --- CONFIGURACIÓN DE FLASK ---
app = Flask(__name__)
# DIRECTORIO TEMPORAL PARA GUARDAR ARCHIVOS SUBIDOS Y EL RESULTADO
UPLOAD_FOLDER = 'temp_uploads' 
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
# --- FUNCIÓN CENTRAL DE GENERACIÓN DE VIDEO ---
def create_video(config, file_mapping):
    clips = []
    for clip_config in config['clips']:
        file_path = file_mapping.get(clip_config['id'])
        if not file_path:
            continue
        clip_type = clip_config['type'].split('/')[0]
        if clip_type == 'image':
            clip = ImageClip(file_path, duration=clip_config['duration'])
        elif clip_type == 'video':
            clip = VideoFileClip(file_path)
        clip = clip.resize(height=1920).set_position('center').crop(width=1080, height=1920)
        clips.append(clip)
    if not clips:
        raise ValueError("No se pudieron procesar clips visuales válidos.")
    final_clip = concatenate_videoclips(clips)
    if config['text']:
        txt_clip = TextClip(
            config['text'], 
            fontsize=100, 
            color='white', 
            font='Arial-Bold',
            bg_color='transparent',
            size=(1080 * 0.8, None)
        )
        txt_clip = txt_clip.set_pos(('center', 'center')).set_duration(final_clip.duration)
        final_clip = CompositeVideoClip([final_clip, txt_clip])
    if config['audioName']:
        audio_path = file_mapping.get('audio_file')
        if audio_path:
            audio_clip = AudioFileClip(audio_path)
            audio_clip = audio_clip.set_duration(final_clip.duration)
            final_clip = final_clip.set_audio(audio_clip)
    output_filename = os.path.join(UPLOAD_FOLDER, f"final_reel_{os.urandom(8).hex()}.mp4")
    print("\n--- EMPEZANDO RENDERIZADO (Puede tardar según la duración) ---")
    final_clip.write_videofile(
        output_filename, 
        codec='libx264', 
        audio_codec='aac', 
        temp_audiofile='temp-audio.m4a',
        remove_temp=True,
        fps=24
    )
    print("--- RENDERIZADO COMPLETADO ---\n")
    return output_filename
# --- RUTAS DE FLASK ---
@app.route('/')
def index():
    return send_file('index.html')
@app.route('/generate-reel', methods=['POST'])
def generate_reel():
    try:
        config_data = request.form.get('config')
        config = json.loads(config_data)
    except Exception:
        return "Error al leer la configuración JSON.", 400
    file_mapping = {}
    temp_files_to_clean = []
    try:
        for key, media_file in request.files.items():
            save_path = os.path.join(UPLOAD_FOLDER, f"{key}_{media_file.filename}")
            media_file.save(save_path)
            file_mapping[key] = save_path
            temp_files_to_clean.append(save_path)
        output_path = create_video(config, file_mapping)
        temp_files_to_clean.append(output_path)
        return send_file(output_path, as_attachment=True, mimetype='video/mp4')
    except Exception as e:
        print(f"Error fatal durante la generación: {e}")
        return f"Error interno del servidor durante el renderizado: {e}", 500
    finally:
        for path in temp_files_to_clean:
            try:
                os.remove(path)
            except OSError:
                pass
# --- INICIAR EL SERVIDOR ---
if __name__ == '__main__':
    print("----------------------------------------------------------------------")
    print("--- ¡SERVIDOR LISTO! Abre tu navegador y ve a http://127.0.0.1:5000 ---")
    print("----------------------------------------------------------------------")
    app.run(debug=True)