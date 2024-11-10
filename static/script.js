let isRecording = false;
let mediaRecorder;
let audioChunks = [];
let currentAudio = null; // 用于跟踪当前播放的音频对象

const playButton = document.getElementById('playButton');
const recordButton = document.getElementById('recordButton');
const conversation = document.getElementById('conversation');
const voiceSelector = document.getElementById('voiceSelector');
const loading = document.getElementById('loading');

playButton.addEventListener('click', function() {
    const welcomeAudio = new Audio('/static/welcome.mp3');
    welcomeAudio.play().then(() => {
        console.log('欢迎语音播放成功');
        recordButton.disabled = false;  // 启用录音按钮
    }).catch(error => {
        console.error('播放欢迎语音错误:', error);
    });
});

recordButton.addEventListener('click', function() {
    if (!isRecording) {
        startRecording();
    } else {
        stopRecording();
    }
});

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
            mediaRecorder.start();
            isRecording = true;
            recordButton.textContent = '结束对话';
            conversation.value += '开始对话...\n';
            loading.style.display = 'none';

            mediaRecorder.addEventListener('dataavailable', event => {
                audioChunks.push(event.data);
            });

            mediaRecorder.addEventListener('stop', () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                audioChunks = [];

                // 发送音频到服务器
                sendAudioToServer(audioBlob);
            });
        })
        .catch(error => {
            console.error('录音错误:', error);
            conversation.value += '录音错误：' + error + '\n';
        });
}

function stopRecording() {
    mediaRecorder.stop();
    isRecording = false;
    recordButton.textContent = '开始对话';
    conversation.value += '结束录音，正在处理...\n';
    loading.style.display = 'block';
}

function sendAudioToServer(audioBlob) {
    const formData = new FormData();
    formData.append('audio_data', audioBlob, 'audio.webm');
    formData.append('voice', voiceSelector.value);

    console.log('Sending POST request to /upload_audio');

    fetch('/upload_audio', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('网络响应不正常: ' + response.statusText);
        }
        return response.json();
    })
    .then(data => {
        loading.style.display = 'none';
        if (data.error) {
            conversation.value += '错误: ' + data.error + '\n';
        } else {
            conversation.value += 'AI: ' + data.ai_response + '\n';
            // 播放音频，使用新的 URL
            playAudio('/get_audio');  // 确保这个 URL 正确指向合成的音频
        }
    })
    .catch(error => {
        console.error('Fetch error:', error);
        conversation.value += '发生错误：' + error + '\n';
        loading.style.display = 'none';
    });
}


function playAudio(url) {
    // 如果有正在播放的音频，先停止它
    if (currentAudio) {
        currentAudio.pause(); // 停止之前的音频
        currentAudio.currentTime = 0; // 重置播放时间
    }

    // 添加随机查询参数以避免缓存
    const newUrl = `${url}?t=${new Date().getTime()}`;
    currentAudio = new Audio(newUrl); // 创建新的音频对象
    currentAudio.play().catch(error => {
        console.error('播放音频错误:', error);
        conversation.value += '播放音频时出错：' + error + '\n';
    });
}

