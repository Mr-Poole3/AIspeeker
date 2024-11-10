from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import asyncio
import warnings
import whisper
import edge_tts
from pydub import AudioSegment
import SparkApi  # 您需要根据实际情况实现或配置这个模块
from werkzeug.security import generate_password_hash, check_password_hash
import webbrowser
from face_check import *
from mongodb import *
import json
from werkzeug.utils import secure_filename
import os
from face_add import add_face

# 忽略特定的警告（可选）
warnings.filterwarnings("ignore", category=FutureWarning, module="torch")
warnings.filterwarnings("ignore", message="Torch was not compiled with flash attention.")

app = Flask(__name__)

# 设置上传文件夹
UPLOAD_FOLDER = 'uploaded_photos/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 检查并创建上传目录（如果不存在）
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

CORS(app)  # 允许跨域请求，如果前端和后端在同一域名和端口上，可以省略
# 配置参数
DOMAIN = "4.0Ultra"  # Max版本
SPARK_URL = "wss://spark-api.xf-yun.com/v4.0/chat"  # Max服务地址
APPID = "1a0857f3"  # 请替换为实际的App ID
API_KEY = "42e60ecb7d40e6c3bf8978c00fa46884"  # 请替换为实际的API Key
API_SECRET = "YmJkMmZjMzQyY2RlZDA2MmYwYjA2YjVm"  # 请替换为实际的API Secret

# 初始上下文内容，当前可传system、user、assistant 等角色
def load_prompt(file_path='prompt/AI_prompt.txt'):
    """加载并解析 prompt 文件"""
    with open(file_path, 'r', encoding='utf-8') as file:
        text_context = json.load(file)
    return text_context

# 加载 prompt 内容
text_context = load_prompt()

@app.route('/get_prompt', methods=['GET'])
def get_prompt():
    return jsonify(text_context)

def append_text(role, content):
    """添加对话内容并检查长度"""
    global text_context
    text_context.append({"role": role, "content": content})
    text_context = trim_context(text_context)
    return text_context

def get_total_length(texts):
    """计算当前上下文的总长度"""
    return sum(len(entry["content"]) for entry in texts)

def trim_context(texts, max_length=8000):
    """当上下文长度超过max_length时，删除最早的对话"""
    while get_total_length(texts) > max_length and len(texts) > 1:
        del texts[0]
    return texts

async def synthesize_speech(text, voice="en-US-AvaNeural", output_file="output.mp3"):
    """将文本合成为语音并保存"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)
    return output_file

# 加载 Whisper 模型
try:
    model = whisper.load_model("small.en")  # 根据需要选择模型
    print("Whisper 模型加载成功。")
except Exception as e:
    print(f"加载 Whisper 模型出错: {e}")
    model = None

# 登录页面
@app.route('/login')
def login_page():
    return render_template('log_in.html')

# 注册页面
@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    # 获取表单数据
    username = request.form.get("username")
    password = request.form.get("password")
    email = request.form.get("email")
    photo = request.files.get("photo")  # 获取照片文件

    # 检查必填字段
    if not username or not password or not email or not photo:
        return jsonify({"message": "请填写所有字段并上传照片"}), 400

    # 检查用户名是否已存在
    if check_user_exists(username):
        return jsonify({"message": "用户名已存在"}), 400

    # 保存照片
    filename = secure_filename(photo.filename)
    photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    photo.save(photo_path)

    # 添加用户信息到数据库
    hashed_password = generate_password_hash(password)
    add_user(username, hashed_password, email)

    # 调用 face_add.py 中的 add_face 函数，将用户照片添加到 CompreFace
    add_face(photo_path, username)

    # 删除上传的照片文件
    try:
        os.remove(photo_path)
    except Exception as e:
        print(f"删除文件失败: {e}")

    return jsonify({"message": "注册成功"}), 201

# 登录路由
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = get_user(username)
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "用户名或密码错误"}), 401

    return jsonify({"message": "登录成功"}), 200

# robot 页面
@app.route('/robot')
def robot():
    return render_template('robot.html')


@app.route('/favicon.ico')
def favicon():
    # 可选：返回空响应或提供一个 favicon.ico 文件
    return '', 204

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    if model is None:
        return jsonify({'error': 'Whisper 模型未加载成功。'}), 500
    try:
        print("Received /upload_audio POST request")

        # 获取上传的音频文件
        if 'audio_data' not in request.files:
            print("No audio_data in request.files")
            return jsonify({'error': '未上传音频文件。'}), 400

        audio_file = request.files['audio_data']
        voice = request.form.get('voice', 'en-US-AvaNeural')  # 获取语音选择
        print(f"Voice selected: {voice}")

        # 保存音频文件
        audio_webm_path = 'uploaded_audio.webm'
        audio_wav_path = 'uploaded_audio.wav'
        audio_file.save(audio_webm_path)
        print(f"Audio file saved as {audio_webm_path}")

        # 转换音频为wav格式
        try:
            audio = AudioSegment.from_file(audio_webm_path)
            audio.export(audio_wav_path, format='wav')
            print(f"Audio file converted to {audio_wav_path}")
        except Exception as e:
            print(f"音频格式转换出错: {e}")
            return jsonify({'error': f'音频格式转换出错: {e}'}), 500

        # 转录
        try:
            result = model.transcribe(audio_wav_path, language='English', fp16=False)
            user_text = result.get("text", "").strip()
            print(f"Transcribed text: {user_text}")
            if not user_text:
                return jsonify({'error': '未检测到有效的语音输入。'}), 400
            append_text("user", user_text)
        except Exception as e:
            print(f"转录出错: {e}")
            return jsonify({'error': f'转录出错: {e}'}), 500

        # 获取AI回答
        try:
            SparkApi.answer = ""
            SparkApi.main(APPID, API_KEY, API_SECRET, SPARK_URL, DOMAIN, text_context)
            ai_response = SparkApi.answer.strip()
            print(f"AI response: {ai_response}")
            if not ai_response:
                return jsonify({'error': '未收到AI的回答。'}), 500
            append_text("assistant", ai_response)
        except Exception as e:
            print(f"调用 SparkApi 出错: {e}")
            return jsonify({'error': f'调用 AI 接口出错: {e}'}), 500

        # 语音合成
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            output_audio_file = loop.run_until_complete(synthesize_speech(ai_response, voice=voice))
            print(f"语音合成完成，保存为 {output_audio_file}")
        except Exception as e:
            print(f"语音合成出错: {e}")
            return jsonify({'error': f'语音合成出错: {e}'}), 500

        # 返回AI的文字回复和音频文件的URL
        return jsonify({'ai_response': ai_response, 'audio_url': '/get_audio'})

    except Exception as e:
        print(f"Error in /upload_audio: {e}")
        return jsonify({'error': f'处理过程中出错: {e}'}), 500

@app.route('/get_audio')
def get_audio():
    try:
        return send_file('output.mp3', as_attachment=False)
    except Exception as e:
        print(f"Error in /get_audio: {e}")
        return jsonify({'error': f'无法获取音频文件: {e}'}), 500

if __name__ == '__main__':
    # 启动 Flask 服务器之前，自动打开浏览器并访问登录页面
    webbrowser.open("http://127.0.0.1:5000/login")
    # 运行 Flask 应用
    app.run(debug=False, host='0.0.0.0', port=5000)
