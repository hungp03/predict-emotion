import React, { useState, useRef, useEffect } from 'react';
import { 
  Tabs, Button, Select, Upload, Card, Progress, 
  Typography, Spin, message, Alert
} from 'antd';
import { UploadOutlined, AudioOutlined, PlayCircleOutlined } from '@ant-design/icons';
import './App.css';

const { TabPane } = Tabs;
const { Title, Text } = Typography;
const { Option } = Select;

function App() {
  const [model, setModel] = useState('normal');
  const [loading, setLoading] = useState(false);
  const [audioFile, setAudioFile] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [countdown, setCountdown] = useState(null);
  const [preparingCountdown, setPreparingCountdown] = useState(null);
  const [fileList, setFileList] = useState([]);
  
  const streamRef = useRef(null);
  const recorderRef = useRef(null);

  // Handle model selection change
  const handleModelChange = (value) => {
    setModel(value);
  };
  
  // Handle file upload
  const handleFileUpload = ({ file, fileList }) => {
    if (file.status !== 'uploading') {
      setFileList(fileList);
      if (file.status === 'done' || file.status === undefined) {
        setAudioFile(file.originFileObj || file);
        const url = URL.createObjectURL(file.originFileObj || file);
        setAudioUrl(url);
        message.success(`${file.name} ready for analysis`);
      }
    }
  };
  
  // Submit audio file for prediction
  const handleSubmit = async () => {
    if (!audioFile) {
      message.warning('Please upload or record an audio file first.');
      return;
    }
    
    setLoading(true);
    setPrediction(null);
    
    try {
      const formData = new FormData();
      formData.append('file', audioFile);
      formData.append('model_type', model);
      
      const response = await fetch('http://localhost:8000/predict/', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      
      const result = await response.json();
      if (result.error) {
        throw new Error(result.error);
      }
      
      setPrediction(result);
    } catch (error) {
      console.error('Error:', error);
      message.error(`Failed to get prediction: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, [audioUrl]);
  
  // Handle recording preparation and countdown
  const prepareRecording = () => {
    setPreparingCountdown(5);
    
    const prepInterval = setInterval(() => {
      setPreparingCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(prepInterval);
          startRecording();
          return null;
        }
        return prev - 1;
      });
    }, 1000);
  };
  
  // Start audio recording with MediaRecorder
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      recorderRef.current = new MediaRecorder(stream);
      const chunks = [];

      recorderRef.current.ondataavailable = (e) => chunks.push(e.data);
      recorderRef.current.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/webm' });
        const fileName = `recording_${new Date().getTime()}.webm`;
        const audioFile = new File([blob], fileName, { type: 'audio/webm' });
        setAudioFile(audioFile);
        setAudioUrl(URL.createObjectURL(blob));
        setFileList([{ uid: '-1', name: fileName, status: 'done', originFileObj: audioFile }]);
        message.success('Recording completed successfully');
      };

      recorderRef.current.start();
      setIsRecording(true);
      setCountdown(3);

      const countInterval = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(countInterval);
            stopRecording();
            return null;
          }
          return prev - 1;
        });
      }, 1000);

      setTimeout(() => {
        if (isRecording) {
          stopRecording();
        }
      }, 5000);

    } catch (error) {
      console.error('Error accessing microphone:', error);
      message.error('Failed to access microphone. Please check permissions and try again.');
      setIsRecording(false);
      setPreparingCountdown(null);
    }
  };
  
  const stopRecording = () => {
    if (!recorderRef.current || !streamRef.current) return;

    recorderRef.current.stop();
    streamRef.current.getTracks().forEach(track => track.stop());
    setIsRecording(false);
  };
  
  const playAudio = () => {
    if (audioUrl) {
      const audio = new Audio(audioUrl);
      audio.play().catch(error => {
        console.error('Error playing audio:', error);
        message.error('Failed to play audio.');
      });
    }
  };
  
  const renderPrediction = () => {
    if (!prediction) return null;
    
    const emotionColors = {
      'HAP': '#52c41a',
      'SAD': '#1890ff',
      'NEU': '#faad14',
    };
    
    const emotionNames = {
      'HAP': 'Happy',
      'SAD': 'Sad',
      'NEU': 'Neutral',
    };
    
    return (
      <Card className="prediction-card">
        <Title level={4}>Prediction Result</Title>
        <div className="prediction-content">
          <div className="emotion-result">
            <Alert
              message={`Emotion: ${emotionNames[prediction.label] || prediction.label}`}
              type="success"
              style={{ backgroundColor: emotionColors[prediction.label] || '#1890ff', color: 'white' }}
            />
            <div className="confidence">
              <Text>Confidence: </Text>
              <Progress 
                percent={Math.round(prediction.confidence * 100)} 
                status="active" 
                strokeColor={emotionColors[prediction.label] || '#1890ff'}
              />
            </div>
          </div>
          <Text strong>Model Used: {prediction.model_used}</Text>
        </div>
      </Card>
    );
  };

  return (
    <div className="app-container">
      <Title level={2}>Voice Emotion Recognition</Title>
      
      <div className="model-selector">
        <Text strong>Select Model:</Text>
        <Select value={model} onChange={handleModelChange} style={{ width: 120 }}>
          <Option value="normal">Normal</Option>
          <Option value="mini">Mini</Option>
        </Select>
      </div>
      
      <Tabs defaultActiveKey="1" className="main-tabs">
        <TabPane tab="Upload Audio" key="1">
          <div className="upload-container">
            <Upload
              accept="audio/*"
              fileList={fileList}
              beforeUpload={() => false}
              onChange={handleFileUpload}
              maxCount={1}
              onRemove={() => {
                setFileList([]);
                setAudioFile(null);
                setAudioUrl(null);
              }}
            >
              <Button icon={<UploadOutlined />}>Select Audio File</Button>
            </Upload>
            
            {audioUrl && (
              <div className="audio-controls">
                <Button 
                  type="primary" 
                  icon={<PlayCircleOutlined />} 
                  onClick={playAudio}
                >
                  Play Audio
                </Button>
              </div>
            )}
            
            <Button 
              type="primary" 
              onClick={handleSubmit} 
              disabled={!audioFile || loading}
              loading={loading}
            >
              Submit for Analysis
            </Button>
          </div>
        </TabPane>
        
        <TabPane tab="Record Audio" key="2">
          <div className="record-container">
            {!isRecording && !preparingCountdown && (
              <Button 
                type="primary" 
                icon={<AudioOutlined />} 
                onClick={prepareRecording}
                disabled={loading}
              >
                Start Recording
              </Button>
            )}
            
            {preparingCountdown && (
              <div className="countdown">
                <Text strong>Preparing to record in: {preparingCountdown}s</Text>
                <Progress percent={((5 - preparingCountdown) / 5) * 100} showInfo={false} />
              </div>
            )}
            
            {isRecording && countdown && (
              <div className="countdown">
                <Text strong type="danger">Recording... {countdown}s</Text>
                <Progress percent={((5 - countdown) / 5) * 100} strokeColor="#ff4d4f" showInfo={false}/>
              </div>
            )}
            
            {audioUrl && !isRecording && !preparingCountdown && (
              <div className="audio-controls">
                <Button 
                  type="primary" 
                  icon={<PlayCircleOutlined />} 
                  onClick={playAudio}
                >
                  Play Recorded Audio
                </Button>
              </div>
            )}
            
            {audioFile && !isRecording && !preparingCountdown && (
              <Button 
                type="primary" 
                onClick={handleSubmit} 
                disabled={loading}
                loading={loading}
              >
                Submit for Analysis
              </Button>
            )}
          </div>
        </TabPane>
      </Tabs>
      
      {loading && (
        <div className="loading-container">
          <Spin size="large" />
          <Text>Analyzing audio...</Text>
        </div>
      )}
      
      {renderPrediction()}
    </div>
  );
}

export default App;