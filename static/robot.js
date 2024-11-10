// 初始化状态为 stand
let isHappy = false;
let isRecording = false;
let mediaRecorder;
let audioChunks = [];

// 点击页面事件
$('.in-page').on('click', function() {
    if (!isHappy) {
        // 如果当前是 stand 状态，切换到 happy，并播放音频
        $('.page').removeClass('bot-stand-by');
        $('.page').addClass('bot-happy');
        $('.page').addClass('bot-happy-start');
        isHappy = true;  // 更新状态

        // 显示麦克风图标
        $('.mic-container').show();  // 显示图标

        // 播放欢迎音频
        const welcomeAudio = new Audio('/static/welcome.mp3');
        welcomeAudio.play().then(() => {
            console.log('欢迎语音播放成功');
            const recordButton = document.getElementById('recordButton');  // 获取录音按钮
            if (recordButton) {
                recordButton.disabled = false;  // 启用录音按钮
            }
        }).catch(error => {
            console.error('播放欢迎语音错误:', error);
        });

        // 监听麦克风图标的点击事件，开始录音
        $('#micButton').off('click touchstart').on('click touchstart', function() {
            if (!isRecording) {
                startRecording();  // 开始录音
            } else {
                stopRecording();   // 停止录音并发送音频
            }
        });

    } else {
        // 如果当前是 happy 状态，切换回 stand
        $('.page').removeClass('bot-happy');
        $('.page').removeClass('bot-happy-start');
        $('.page').addClass('bot-stand-by');
        isHappy = false;  // 更新状态

        // 隐藏麦克风图标
        $('.mic-container').hide();  // 隐藏图标
    }
});

// 导航按钮点击事件，只处理 stand 和 happy
$('nav span').on('click', function() {
    var a = $(this),
        el = a.data('href');  // 获取点击的表情状态 (stand 或 happy)

    $('nav .act').removeClass('act');
    $(a).addClass('act');
    $('.page').attr('class', 'page bot-' + el);  // 根据状态切换 class 为 bot-stand 或 bot-happy
    isHappy = (el === 'happy');  // 根据点击的按钮更新状态

    // 根据状态更新麦克风图标的显示
    if (isHappy) {
        $('.mic-container').show();  // 显示图标
        const welcomeAudio = new Audio('/static/welcome.mp3');
        welcomeAudio.play().then(() => {
            console.log('欢迎语音播放成功');
            const recordButton = document.getElementById('recordButton');
            if (recordButton) {
                recordButton.disabled = false;  // 启用录音按钮
            }
        }).catch(error => {
            console.error('播放欢迎语音错误:', error);
        });

        // 监听麦克风点击事件，开始录音或结束录音
        $('#micButton').off('click touchstart').on('click touchstart', function() {
            if (!isRecording) {
                startRecording();  // 开始录音
            } else {
                stopRecording();   // 停止录音并发送音频
            }
        });
    } else {
        $('.mic-container').hide();  // 隐藏图标
    }
});

// 录音相关函数
function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
            mediaRecorder.start();
            isRecording = true;
            $('#micButton').addClass('recording'); // 添加录音状态的样式
            $('#conversation').val('开始对话...\n');

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
            $('#conversation').val('录音错误：' + error + '\n');
        });
}

function stopRecording() {
    mediaRecorder.stop();
    isRecording = false;
    $('#micButton').removeClass('recording'); // 移除录音状态的样式
    $('#conversation').val('结束录音，正在处理...\n');
    $('#loading').show();
}

function sendAudioToServer(audioBlob) {
    const formData = new FormData();
    formData.append('audio_data', audioBlob, 'audio.webm');

    // 获取选择的语音类型（通过自定义的单选按钮）
    const selectedVoice = document.querySelector('input[name="voiceSelector"]:checked').value;
    formData.append('voice', selectedVoice);

    console.log('Sending POST request to /upload_audio with voice:', selectedVoice); // 输出所选的语音

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
        $('#loading').hide();
        if (data.error) {
            $('#conversation').val('错误: ' + data.error + '\n');
        } else {
            $('#conversation').val('AI: ' + data.ai_response + '\n');
            // 播放合成的语音
            playAudio('/get_audio');
        }
    })
    .catch(error => {
        console.error('发送音频时出错:', error);
        $('#conversation').val('发生错误：' + error + '\n');
        $('#loading').hide();
    });
}

function playAudio(url) {
    const audio = new Audio(url + '?t=' + new Date().getTime());
    audio.play().catch(error => {
        console.error('播放音频错误:', error);
        $('#conversation').val('播放音频时出错：' + error + '\n');
    });
}
