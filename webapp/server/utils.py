import os
import librosa
import numpy as np
import tensorflow as tf
import requests
import time
from dotenv import load_dotenv
from pydub import AudioSegment

load_dotenv()
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")
def update_prediction_to_firebase(result: dict):
    timestamp = int(time.time() * 1000)
    current_url = f"{FIREBASE_DB_URL}/predictions/current.json"
    current_res = requests.get(current_url)
    
    if current_res.ok and current_res.json():
        current_data = current_res.json()
        history_url = f"{FIREBASE_DB_URL}/predictions/history/prediction{timestamp}.json"
        history_payload = {
            "result": current_data.get("result"),
            "confidence": current_data.get("confidence"),
            "modelName": current_data.get("modelName"),
            "timestamp": current_data.get("lastUpdated")
        }
        requests.put(history_url, json=history_payload)

    new_current = {
        "result": result["label"],
        "confidence": result["confidence"],
        "modelName": result["model_used"],
        "lastUpdated": timestamp
    }
    requests.put(current_url, json=new_current)

models = {}

def load_model(model_type: str):
    model_paths = {
        "normal": "model_mfcc_26_large.keras",
        "mini": "model_mfcc_mini.keras",
    }
    
    if model_type not in model_paths:
        raise ValueError(f"Invalid model type: {model_type}")
    
    if model_type not in models:
        models[model_type] = tf.keras.models.load_model(model_paths[model_type])
    
    return models[model_type]

MODEL_CONFIGS = {
    "normal": {
        "sample_rate": 16000,
        "n_mfcc": 26,
        "n_fft": 2048,
        "hop_length": lambda sr: int(0.010 * sr),
        "win_length": lambda sr: int(0.025 * sr),
        "window": "hamming",
        "n_mels": 26,
        "normalize": True,
        "mean": -7.0426135,
        "std": 48.8516,
        "output_shape": (1, 26, 301, 1)
    },
    "mini": {
        "sample_rate": 16000,  
        "n_mfcc": 13,     
        "n_fft": 1024,
        "hop_length": lambda sr: int(0.010 * sr),
        "win_length": lambda sr: int(0.025 * sr),
        "window": "hamming",
        "n_mels": 13,
        "normalize": True, 
        "mean": -36.16106,
        "std": 162.93813,
        "output_shape": (1, 13, 301, 1)
    }
}

def convert_to_wav(file_path: str) -> str:
    output_path = file_path.rsplit('.', 1)[0] + '_converted.wav'
    try:
        audio = AudioSegment.from_file(file_path)
        audio = audio.set_frame_rate(16000).set_channels(1)  # Normalize 16kHz, mono
        audio.export(output_path, format="wav")
        return output_path
    except Exception as e:
        raise ValueError(f"Failed to convert audio file: {e}")

def extract_mfcc(file_path: str, model_type: str) -> np.ndarray:
    if model_type not in MODEL_CONFIGS:
        raise ValueError(f"Unknown model type: {model_type}")
    
    config = MODEL_CONFIGS[model_type]
    sr = config["sample_rate"]
    
    # Convert to WAV if not already in that format
    if not file_path.endswith('.wav'):
        wav_path = convert_to_wav(file_path)
    else:
        wav_path = file_path

    # Load audio
    audio, _ = librosa.load(wav_path, sr=sr, duration=3, mono=True)
    if len(audio) < 3 * sr:
        audio = np.pad(audio, (0, 3 * sr - len(audio)))

    hop_length = config["hop_length"](sr)
    win_length = config["win_length"](sr)
    
    mfcc = librosa.feature.mfcc(
        y=audio,
        sr=sr,
        n_mfcc=config["n_mfcc"],
        n_fft=config["n_fft"],
        hop_length=hop_length,
        win_length=win_length,
        window=config["window"],
        n_mels=config["n_mels"]
    )
    
    if config["normalize"]:
        mfcc = (mfcc - config["mean"]) / config["std"]
    return mfcc.reshape(config["output_shape"])

def predict(file_path: str, model, model_type: str) -> dict:
    mfcc = extract_mfcc(file_path, model_type)
    prediction = model.predict(mfcc)[0]
    emotion_labels = ["HAP", "NEU", "SAD"]
    predicted_index = int(np.argmax(prediction))
    return {
        "label": emotion_labels[predicted_index],
        "confidence": float(prediction[predicted_index]),
        "model_used": model_type
    }

import socket
import wave
import time

ESP32_IP = "IP_ADDRESS_OF_ESP32"
PORT = "PORT_NUMBER_OF_ESP32"
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2
BUFFER_SIZE = 4096
UPLOAD_DIR = "FOLDER_TO_SAVE_AUDIO"

def receive_audio_from_esp32(duration=6):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        output_filename = os.path.join(UPLOAD_DIR, f"esp32_audio_{int(time.time())}.wav")
        try:
            s.connect((ESP32_IP, PORT))
            print("Connected to ESP32...")

            frames = b''
            start_time = time.time()

            expected_bytes = SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS * duration
            received_bytes = 0
            frames = b''
            while received_bytes < expected_bytes:
                data = s.recv(BUFFER_SIZE)
                if not data:
                    break
                frames += data
                received_bytes += len(data)
                print(f"Receive: {len(data)} bytes, Total: {received_bytes} / {expected_bytes} bytes")
            # audio_data = np.frombuffer(frames, dtype=np.int16)
            audio_data = np.frombuffer(frames, dtype=np.int16)
            with wave.open(output_filename, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(SAMPLE_WIDTH)
                wf.setframerate(SAMPLE_RATE)
                # wf.writeframes(frame)
                wf.writeframes(audio_data.tobytes())
            print(f"Saved: {output_filename}, Total time: {time.time() - start_time:.2f} seconds")
            return output_filename
        except socket.timeout:
            print("ESP32 not responding, try again later.")