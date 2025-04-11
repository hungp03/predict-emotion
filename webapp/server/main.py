# import os
# from fastapi import FastAPI, UploadFile, File, Form
# from fastapi.middleware.cors import CORSMiddleware
# import shutil
# import uuid
# from utils import predict, load_model, update_prediction_to_firebase

# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# @app.post("/predict/")
# async def predict_audio(
#     file: UploadFile = File(...),
#     model_type: str = Form(...),
# ):
#     temp_path = f"temp_{file.filename}"
    
#     # Lưu file tạm thời
#     with open(temp_path, "wb") as buffer:
#         buffer.write(await file.read())
    
#     try:
#         model = load_model(model_type)
#         result = predict(temp_path, model, model_type)
#         update_prediction_to_firebase(result)
#         return result
#     except Exception as e:
#         return {"error": str(e)}
#     finally:
#         # Xóa file tạm thời
#         if os.path.exists(temp_path):
#             os.remove(temp_path)
#         converted_path = temp_path.rsplit('.', 1)[0] + '_converted.wav'
#         if os.path.exists(converted_path):
#             os.remove(converted_path)

import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil
import uuid
from utils import predict, load_model, update_prediction_to_firebase, receive_audio_from_esp32
from dotenv import load_dotenv
load_dotenv()
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/predict/")
async def predict_audio(
    file: UploadFile = File(...),
    model_type: str = Form("normal"),
):
    print(f"Received file: {file.filename}, model_type: {model_type}")
    temp_path = f"temp_{uuid.uuid4().hex}.wav"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        model = load_model(model_type)
        result = predict(temp_path, model, model_type)
        
    except Exception as e:
        return {"error": str(e)}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    update_prediction_to_firebase(result)
    return result


import time
@app.post("/predict/esp32/")
async def predict_audio_from_esp32(
    model_type: str = Form("normal"),
    duration: int = Form(6)
):
    try:
        audio_path = receive_audio_from_esp32(duration=duration)
        time.sleep(1)
        model = load_model(model_type)
        result = predict(audio_path, model, model_type)
    except Exception as e:
        return {"error": str(e)}
    update_prediction_to_firebase(result)
    return result
