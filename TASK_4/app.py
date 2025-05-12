from flask import Flask, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
import wave
import base64
import requests
import io
from pydub import AudioSegment
from dotenv import load_dotenv
import soundfile as sf
import sounddevice as sd
from sarvamai import SarvamAI
import json

# Load environment variables
load_dotenv()
api_key = os.getenv("API_KEY", "db88ef57-4a66-4b3b-877d-61d7586481cf")

app = Flask(__name__, static_folder='.')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching

# Ensure the upload directory exists
UPLOAD_FOLDER = '.'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def split_audio(audio_path, chunk_duration_ms=15 * 1000):  # Reduced to 15 seconds per chunk
    try:
        audio = AudioSegment.from_file(audio_path)
        chunks = []
        if len(audio) > chunk_duration_ms:
            for i in range(0, len(audio), chunk_duration_ms):
                chunk = audio[i: i + chunk_duration_ms]
                chunks.append(chunk)
        else:
            chunks.append(audio)
        return chunks
    except Exception as e:
        print(f"Error splitting audio: {str(e)}")
        raise

def translate_audio(audio_file_path, chunk_duration_ms=30 * 1000):
    api_url = "https://api.sarvam.ai/speech-to-text-translate"
    headers = {"api-subscription-key": api_key}
    data = {"model": "saaras:v2", "with_diarization": False}
    responses = []
    language = "en-IN"  # Default language

    try:
        chunks = split_audio(audio_file_path, chunk_duration_ms)
        print(f"Processing {len(chunks)} audio chunks...")

        for idx, chunk in enumerate(chunks):
            print(f"Processing chunk {idx + 1}/{len(chunks)}")
            buffer = io.BytesIO()
            chunk.export(buffer, format="wav")
            buffer.seek(0)
            files = {"file": ("audio.wav", buffer, "audio/wav")}
            
            try:
                resp = requests.post(api_url, headers=headers, files=files, data=data)
                resp.raise_for_status()
                json_data = resp.json()
                chunk_text = json_data.get("transcript", "")
                if chunk_text:
                    responses.append(chunk_text)
                language = json_data.get("language_code", language)
            except requests.exceptions.Timeout:
                print(f"Timeout processing chunk {idx + 1}")
                continue
            except Exception as e:
                print(f"Error processing chunk {idx + 1}: {str(e)}")
                continue
            finally:
                buffer.close()

        if not responses:
            raise Exception("No valid responses from any chunks")

        return responses, language
    except Exception as e:
        print(f"Error in translate_audio: {str(e)}")
        raise

def split_text(text, max_length=450):  # Reduced to 450 to be safe
    if not text:
        return []
        
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_length = len(word)
        # If adding this word would exceed the limit, start a new chunk
        if current_length + word_length + 1 > max_length:  # +1 for space
            if current_chunk:  # Only add if we have words
                chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length + 1  # +1 for space
    
    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    print(f"Split text into {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i + 1} length: {len(chunk)} characters")
    
    return chunks

def translation(text, target_language):
    try:
        client = SarvamAI(api_subscription_key=api_key)
        response = client.text.translate(
            input=text,
            source_language_code="en-IN",
            target_language_code=target_language,
            speaker_gender="Male"
        )
        return response
    except Exception as e:
        print(f"Error in translation: {str(e)}")
        raise

def text_to_speech(transcript, code):
    try:
        api_url = "https://api.sarvam.ai/text-to-speech"
        headers = {"Content-Type": "application/json", "api-subscription-key": api_key}
        all_audio = []
        
        # Handle both single text and list of texts
        texts_to_process = []
        if isinstance(transcript, list):
            texts_to_process = transcript
        else:
            text_to_speak = transcript.translated_text if hasattr(transcript, 'translated_text') else transcript
            texts_to_process = [text_to_speak]
        
        print(f"Processing {len(texts_to_process)} text chunks for TTS...")
        
        for idx, text in enumerate(texts_to_process):
            print(f"Processing TTS chunk {idx + 1}/{len(texts_to_process)}")
            print(f"Chunk text: {text[:100]}...")  # Print first 100 chars of chunk
            try:
                if code != "en-IN":
                    payload = {
                        "inputs": [text],
                        "target_language_code": code,
                        "speaker": "abhilash",
                        "model": "bulbul:v2",
                        "pitch": 0,
                        "pace": 1.0,
                        "loudness": 1.0,
                        "enable_preprocessing": True,
                    }
                else:
                    payload = {
                        "inputs": [text],
                        "target_language_code": code,
                        "speaker": "abhilash",
                        "model": "bulbul:v2",
                        "pitch": 0,
                        "pace": 1.0,
                        "loudness": 1.0,
                        "enable_preprocessing": True,
                    }
                
                response = requests.post(api_url, json=payload, headers=headers, timeout=60)
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        if not response_data or "audios" not in response_data or not response_data["audios"]:
                            print(f"Invalid response format for chunk {idx + 1}")
                            continue
                            
                        audio = response_data["audios"][0]
                        if not audio:
                            print(f"Empty audio data for chunk {idx + 1}")
                            continue
                            
                        try:
                            audio_data = base64.b64decode(audio)
                            if not audio_data:
                                print(f"Failed to decode audio data for chunk {idx + 1}")
                                continue
                            all_audio.append(audio_data)
                            print(f"Successfully processed chunk {idx + 1}")
                        except Exception as e:
                            print(f"Error decoding audio data for chunk {idx + 1}: {str(e)}")
                            continue
                    except json.JSONDecodeError as e:
                        print(f"Invalid JSON response for chunk {idx + 1}: {str(e)}")
                        print(f"Response content: {response.text[:200]}...")
                        continue
                else:
                    print(f"Error in TTS chunk {idx + 1}: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"Error details: {error_data}")
                    except:
                        print(f"Error response: {response.text[:200]}...")
                    continue
            except Exception as e:
                print(f"Error processing TTS chunk {idx + 1}: {str(e)}")
                continue
        
        # Combine all audio chunks
        if all_audio:
            output_file = "output.wav"
            try:
                print(f"Combining {len(all_audio)} audio chunks...")
                
                # Create a temporary file for each chunk
                temp_files = []
                for i, audio_data in enumerate(all_audio):
                    temp_file = f"temp_chunk_{i}.wav"
                    try:
                        with wave.open(temp_file, "wb") as wav_file:
                            wav_file.setnchannels(1)
                            wav_file.setsampwidth(2)
                            wav_file.setframerate(22050)
                            wav_file.writeframes(audio_data)
                        temp_files.append(temp_file)
                        print(f"Created temporary file for chunk {i + 1}")
                    except Exception as e:
                        print(f"Error creating temporary file for chunk {i + 1}: {str(e)}")
                        continue

                if not temp_files:
                    print("No valid temporary files were created")
                    return False

                # Combine all chunks using pydub
                try:
                    combined = AudioSegment.empty()
                    for i, temp_file in enumerate(temp_files):
                        try:
                            chunk = AudioSegment.from_wav(temp_file)
                            combined += chunk
                            print(f"Added chunk {i + 1} to combined audio")
                        except Exception as e:
                            print(f"Error processing chunk {i + 1}: {str(e)}")
                            continue
                        finally:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                                print(f"Removed temporary file for chunk {i + 1}")

                    if len(combined) == 0:
                        print("No audio data in combined file")
                        return False

                    # Export the combined audio
                    combined.export(output_file, format="wav")
                    print(f"Successfully created output file: {output_file}")
                    
                    if os.path.exists(output_file):
                        return True
                    else:
                        print("Failed to create output file")
                        return False
                except Exception as e:
                    print(f"Error combining audio chunks: {str(e)}")
                    return False
            except Exception as e:
                print(f"Error in audio processing: {str(e)}")
                # Clean up any remaining temp files
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                return False
        else:
            print("No audio chunks were successfully processed")
            return False
    except Exception as e:
        print(f"Error in text_to_speech: {str(e)}")
        return False

@app.route('/')
def serve_dashboard():
    return send_from_directory('.', 'dashboard.html')

@app.route('/output.wav')
def serve_audio():
    return send_from_directory('.', 'output.wav')

@app.route('/app.png')
def serve_logo():
    return send_from_directory('.', 'app.png')

@app.route('/process-audio', methods=['POST'])
def process_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    target_language = request.form.get('language', 'en-IN')
    
    if audio_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    try:
        # Save the uploaded audio file
        filename = 'input.wav'
        audio_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # Process the audio using your existing functions
        transcripts, lang = translate_audio(filename)
        
        if not transcripts:
            return jsonify({
                'error': 'No speech detected in the audio',
                'status': 'error'
            }), 400
        
        # Translate each transcript separately
        translated_texts = []
        for transcript in transcripts:
            if target_language == "en-IN":
                translated_texts.append(transcript)
            else:
                translated = translation(transcript, target_language)
                translated_texts.append(translated.translated_text)
        
        # Generate speech from all translated texts
        success = text_to_speech(translated_texts, target_language)
        
        if success:
            return jsonify({
                'translation': ' '.join(translated_texts),
                'status': 'success'
            })
        else:
            return jsonify({
                'error': 'Failed to generate audio. Please try with a shorter recording.',
                'status': 'error'
            }), 500
            
    except Exception as e:
        print(f"Error in process_audio: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
