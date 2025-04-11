# Emotion Recognition using CNN
### Overview
This project focuses on recognizing emotions from speech using Convolutional Neural Networks (CNNs). We extract features using MFCC (Mel-Frequency Cepstral Coefficients). The dataset includes CREMA-D, TESS, RAVDESS and additional self-collected data to improve model performance.

### Feauture Extraction
MFCC

Captures vocal characteristics important for speech and emotion recognition.
Compact and effective for extracting meaningful features.

### Model Architecture
Use a CNN-based model to classify emotions

### Results & Findings
The results of the two models achieved around 80% - 90% accuracy. This is a decent accuracy for such a complex task, as even humans have difficulty recognizing a specific emotion from a 2-4 second audio file.

### Challenges in Embedded Deployment
However, deploying models to embedded devices is limited because their memory is low and processing capabilities are not optimized.

Therefore, we integrate the model into a python server so that Esp32 can transmit data to the expected server

### Optimization Strategies
Reduced feature complexity to fit embedded constraints.
Used a lightweight CNN model to balance performance and efficiency.
Explored techniques like quantization and model pruning.
