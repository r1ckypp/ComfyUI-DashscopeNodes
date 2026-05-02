# URL paths
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com"
DASHSCOPE_SYNC_PATH = "/api/v1/services/aigc/multimodal-generation/generation"
DASHSCOPE_ASYNC_CREATE_PATH = "/api/v1/services/aigc/image-generation/generation"
DASHSCOPE_VIDEO_GENERATION_PATH = "/api/v1/services/aigc/video-generation/video-synthesis"
DASHSCOPE_TTS_PATH = "/api/v1/services/audio/tts/SpeechSynthesizer"
DASHSCOPE_TASK_PATH = "/api/v1/tasks"

# Upload constants
DASHSCOPE_IMAGE_URL = "https://dashscope.aliyuncs.com"
DASHSCOPE_UPLOAD_PATH = "/api/v1/uploads"

# Image generation
SIZES = ["1K", "2K", "4K"]
T2I_MODELS = ["wan2.7-image-pro", "wan2.7-image"]

# Video generation
RESOLUTIONS = ["720P", "1080P"]
RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4"]
T2V_MODELS = ["happyhorse-1.0-t2v"]
I2V_MODELS = ["happyhorse-1.0-i2v"]
R2V_MODELS = ["happyhorse-1.0-r2v"]
VED_MODELS = ["happyhorse-1.0-video-edit"]
UPLOAD_MODELS = T2V_MODELS + I2V_MODELS + R2V_MODELS + VED_MODELS

# Qwen Omni
OMNI_MODELS = ["qwen3.5-omni-plus", "qwen3-omni-flash"]

# Qwen TTS
QWEN_TTS_MODELS = ["qwen3-tts-flash", "qwen3-tts-instruct-flash", "qwen-tts"]
QWEN_TTS_VOICES = ["Cherry"]
QWEN_TTS_LANGUAGES = ["Auto", "Chinese", "English", "German", "Italian", "Portuguese",
                      "Spanish", "Japanese", "Korean", "French", "Russian"]

# MiniMax Speech
MINIMAX_SPEECH_MODELS = [
    "MiniMax/speech-2.8-hd",
    "MiniMax/speech-02-hd",
    "MiniMax/speech-2.8-turbo",
    "MiniMax/speech-02-turbo",
]
MINIMAX_AUDIO_FORMATS = ["mp3", "pcm", "flac", "wav"]
MINIMAX_SAMPLE_RATES = [8000, 16000, 22050, 24000, 32000, 44100]
MINIMAX_EMOTIONS = ["none", "happy", "sad", "angry", "fearful", "disgusted", "surprised", "calm", "whisper"]
MINIMAX_CLONE_MODELS = MINIMAX_SPEECH_MODELS
MINIMAX_CLONE_LANGUAGES = [
    "Chinese", "English", "Arabic", "Russian", "Spanish", "French",
    "Portuguese", "German", "Japanese", "Korean", "Thai", "Hindi",
    "Indonesian", "Vietnamese", "Turkish", "Italian", "auto",
]

# CosyVoice
COSYVOICE_MODELS = [
    "cosyvoice-v3.5-plus",
    "cosyvoice-v3.5-flash",
    "cosyvoice-v3-plus",
    "cosyvoice-v3-flash",
    "cosyvoice-v2",
]
COSYVOICE_FORMATS = ["mp3", "pcm", "wav", "opus"]
COSYVOICE_SAMPLE_RATES = [8000, 16000, 22050, 24000, 44100, 48000]
COSYVOICE_VOICES = [
    "longxiaochun", "longxiaohe", "longlong", "siyue",
    "longdangdang", "longyao", "yina", "aina", "longanyang",
]
