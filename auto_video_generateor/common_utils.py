import os
import time
import pathlib

import gradio
import qianfan

import logging
import re
import json
import requests

# 自行在环境变量设置千帆的参数
# os.environ["QIANFAN_ACCESS_KEY"] = "ALTAKc5yYaLe5QS***********"
# os.environ["QIANFAN_SECRET_KEY"] = "eb058f32d47a4c5*****************"

t_now = time.strftime('%Y-%m-%d_%H.%M.%S')

# 保存材料的目录请自行设定，暂用时间戳区分不同项目
_root_dir = os.path.dirname(os.path.dirname(__file__))
_save_dir = os.path.join(_root_dir, f'mnt/materials/{t_now}')

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

DEEPSEEK_PAYLOAD = {
    "model": "deepseek-chat",
    # "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.1,
    "max_tokens": 5000
}


def get_savepath(code_name, sub_name, mkdir_ok=True, request: gradio.Request = None):
    if request:
        code_name = f'{request.username}/{code_name}'  # or time.strftime('%Y-%m-%d_%H.%M.%S')

    # 保存材料的目录请自行设定，暂用时间戳区分不同项目
    _save_dir = os.path.join(_root_dir, f'mnt/materials/{code_name}')

    savepath = f'{_save_dir}/{sub_name}'.replace('\\', '/')
    savepath.rstrip('/')
    if mkdir_ok:
        os.makedirs(savepath, exist_ok=True)
    # print(dict(savepath=savepath))
    return savepath


def get_relpath(code_name, abspath, request: gradio.Request = None):
    _save_dir = get_savepath(code_name, '', mkdir_ok=False, request=request)
    relpath = '/'.join(pathlib.Path(abspath).relative_to(_save_dir).parts)
    return relpath


def get_abspath(code_name, relpath, request: gradio.Request = None):
    _save_dir = get_savepath(code_name, '', mkdir_ok=False, request=request)
    abspath = '/'.join(pathlib.Path(_save_dir).joinpath(relpath).parts)
    return abspath


# os.makedirs(_save_dir, exist_ok=True)
def chat_qianfan(prompt):
    """
    调用千帆免费大语言模型生成文本。
    :param prompt:
    :return:
    """
    chat_comp = qianfan.ChatCompletion()
    # 指定特定模型
    resp = chat_comp.do(model="ERNIE-Speed", messages=[{
        "role": "user",
        "content": prompt
    }])
    # {'id': 'as-dtxjmpmmvi', 'object': 'chat.completion', 'created': 1723638188, 'result': '你好！有什么我可以帮助你的吗？', 'is_truncated': False, 'need_clear_history': False, 'usage': {'prompt_tokens': 1, 'completion_tokens': 8, 'total_tokens': 9}}
    text = resp["body"]["result"]
    return text


def chat(prompt, max_retries=3, retry_delay=2):
    """调用DeepSeek API，带重试机制"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        **DEEPSEEK_PAYLOAD,
        # "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        # "temperature": 0.2,
        # "max_tokens": 2000
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(DEEPSEEK_API_URL, headers=headers, data=json.dumps(payload), timeout=60)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            result = re.sub(r'<think>.*</think>\s*', '', content, flags=re.DOTALL)
            return result
        except requests.exceptions.RequestException as e:
            logger.warning(f"API调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"API响应解析失败: {e}")
            return None

    logger.error(f"API调用失败，已达最大重试次数")
    return None


import base64
import json
import uuid
import requests

# https://www.volcengine.com/docs/6561/163043
# 填写平台申请的appid, access_token以及cluster
appid = os.getenv("DOUBAO_TTS_APPID", "4816******")
access_token = os.getenv("DOUBAO_TTS_ACCESS_TOKEN", "49T570uTf3knO*********************")
cluster = "volcano_tts"

voice_type = "BV700_V2_streaming"
host = "openspeech.bytedance.com"
api_url = f"https://{host}/api/v1/tts"

header = {"Authorization": f"Bearer;{access_token}"}


def tts(text, speaker, save_path):
    request_json = {
        "app": {
            "appid": appid,
            "token": "access_token",
            "cluster": cluster
        },
        "user": {
            "uid": "388808087185088"
        },
        "audio": {
            "voice_type": speaker,
            "encoding": "mp3",
            "speed_ratio": 1.0,
            "volume_ratio": 1.0,
            "pitch_ratio": 1.0,
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "text_type": "plain",
            "operation": "query",
            "with_frontend": 1,
            "frontend_type": "unitTson"
        }
    }
    try:
        resp = requests.post(api_url, json.dumps(request_json), headers=header)
        # print(f"resp body: \n{resp.json()}")
        if "data" in resp.json():
            data = resp.json()["data"]
            file_to_save = open(save_path, "wb")
            file_to_save.write(base64.b64decode(data))
    except Exception as e:
        e.with_traceback()

voice_type_desc = """灿灿 2.0	BV700_V2_streaming
炀炀	BV705_streaming
擎苍 2.0	BV701_V2_streaming
通用女声 2.0	BV001_V2_streaming
灿灿	BV700_streaming
超自然音色-梓梓2.0	BV406_V2_streaming
超自然音色-梓梓	BV406_streaming
超自然音色-燃燃2.0	BV407_V2_streaming
超自然音色-燃燃	BV407_streaming
通用女声	BV001_streaming
通用男声	BV002_streaming
擎苍	BV701_streaming
阳光青年	BV123_streaming
反卷青年	BV120_streaming
通用赘婿	BV119_streaming
古风少御	BV115_streaming
霸气青叔	BV107_streaming
质朴青年	BV100_streaming
温柔淑女	BV104_streaming
开朗青年	BV004_streaming
甜宠少御	BV113_streaming
儒雅青年	BV102_streaming
甜美小源	BV405_streaming
亲切女声	BV007_streaming
知性女声	BV009_streaming
诚诚	BV419_streaming
童童	BV415_streaming
亲切男声	BV008_streaming
译制片男声	BV408_streaming
懒小羊	BV426_streaming
清新文艺女声	BV428_streaming
鸡汤女声	BV403_streaming
智慧老者	BV158_streaming
慈爱姥姥	BV157_streaming
说唱小哥	BR001_streaming
活力解说男	BV410_streaming
影视解说小帅	BV411_streaming
解说小帅-多情感	BV437_streaming
影视解说小美	BV412_streaming
纨绔青年	BV159_streaming
直播一姐	BV418_streaming
反卷青年	BV120_streaming
沉稳解说男	BV142_streaming
潇洒青年	BV143_streaming
阳光男声	BV056_streaming
活泼女声	BV005_streaming
小萝莉	BV064_streaming
奶气萌娃	BV051_streaming
动漫海绵	BV063_streaming
动漫海星	BV417_streaming
动漫小新	BV050_streaming
天才童声	BV061_streaming
促销男声	BV401_streaming
促销女声	BV402_streaming
磁性男声	BV006_streaming
新闻女声	BV011_streaming
新闻男声	BV012_streaming
知性姐姐-双语	BV034_streaming
温柔小哥	BV033_streaming
灿灿 2.0	BV700_V2_streaming
炀炀	BV705_streaming
擎苍 2.0	BV701_V2_streaming
通用女声 2.0	BV001_V2_streaming
灿灿	BV700_streaming
超自然音色-梓梓2.0	BV406_V2_streaming
超自然音色-梓梓	BV406_streaming
超自然音色-燃燃2.0	BV407_V2_streaming
超自然音色-燃燃	BV407_streaming
通用女声	BV001_streaming
通用男声	BV002_streaming
擎苍	BV701_streaming
阳光青年	BV123_streaming
反卷青年	BV120_streaming
通用赘婿	BV119_streaming
古风少御	BV115_streaming
霸气青叔	BV107_streaming
质朴青年	BV100_streaming
温柔淑女	BV104_streaming
开朗青年	BV004_streaming
甜宠少御	BV113_streaming
儒雅青年	BV102_streaming
甜美小源	BV405_streaming
亲切女声	BV007_streaming
知性女声	BV009_streaming
诚诚	BV419_streaming
童童	BV415_streaming
亲切男声	BV008_streaming
译制片男声	BV408_streaming
懒小羊	BV426_streaming
清新文艺女声	BV428_streaming
鸡汤女声	BV403_streaming
智慧老者	BV158_streaming
慈爱姥姥	BV157_streaming
说唱小哥	BR001_streaming
活力解说男	BV410_streaming
影视解说小帅	BV411_streaming
解说小帅-多情感	BV437_streaming
影视解说小美	BV412_streaming
纨绔青年	BV159_streaming
直播一姐	BV418_streaming
反卷青年	BV120_streaming
沉稳解说男	BV142_streaming
潇洒青年	BV143_streaming
阳光男声	BV056_streaming
活泼女声	BV005_streaming
小萝莉	BV064_streaming
奶气萌娃	BV051_streaming
动漫海绵	BV063_streaming
动漫海星	BV417_streaming
动漫小新	BV050_streaming
天才童声	BV061_streaming
促销男声	BV401_streaming
促销女声	BV402_streaming
磁性男声	BV006_streaming
新闻女声	BV011_streaming
新闻男声	BV012_streaming
知性姐姐-双语	BV034_streaming
温柔小哥	BV033_streaming
灿灿 2.0	BV700_V2_streaming
炀炀	BV705_streaming
擎苍 2.0	BV701_V2_streaming
通用女声 2.0	BV001_V2_streaming
灿灿	BV700_streaming
超自然音色-梓梓2.0	BV406_V2_streaming
超自然音色-梓梓	BV406_streaming
超自然音色-燃燃2.0	BV407_V2_streaming
超自然音色-燃燃	BV407_streaming
通用女声	BV001_streaming
通用男声	BV002_streaming
擎苍	BV701_streaming
阳光青年	BV123_streaming
反卷青年	BV120_streaming
通用赘婿	BV119_streaming
古风少御	BV115_streaming
霸气青叔	BV107_streaming
质朴青年	BV100_streaming
温柔淑女	BV104_streaming
开朗青年	BV004_streaming
甜宠少御	BV113_streaming
儒雅青年	BV102_streaming
甜美小源	BV405_streaming
亲切女声	BV007_streaming
知性女声	BV009_streaming
诚诚	BV419_streaming
童童	BV415_streaming
亲切男声	BV008_streaming
译制片男声	BV408_streaming
懒小羊	BV426_streaming
清新文艺女声	BV428_streaming
鸡汤女声	BV403_streaming
智慧老者	BV158_streaming
慈爱姥姥	BV157_streaming
说唱小哥	BR001_streaming
活力解说男	BV410_streaming
影视解说小帅	BV411_streaming
解说小帅-多情感	BV437_streaming
影视解说小美	BV412_streaming
纨绔青年	BV159_streaming
直播一姐	BV418_streaming
反卷青年	BV120_streaming
沉稳解说男	BV142_streaming
潇洒青年	BV143_streaming
阳光男声	BV056_streaming
活泼女声	BV005_streaming
小萝莉	BV064_streaming
奶气萌娃	BV051_streaming
动漫海绵	BV063_streaming
动漫海星	BV417_streaming
动漫小新	BV050_streaming
天才童声	BV061_streaming
促销男声	BV401_streaming
促销女声	BV402_streaming
磁性男声	BV006_streaming
新闻女声	BV011_streaming
新闻男声	BV012_streaming
知性姐姐-双语	BV034_streaming
温柔小哥	BV033_streaming
灿灿 2.0	BV700_V2_streaming
炀炀	BV705_streaming
擎苍 2.0	BV701_V2_streaming
通用女声 2.0	BV001_V2_streaming
灿灿	BV700_streaming
超自然音色-梓梓2.0	BV406_V2_streaming
超自然音色-梓梓	BV406_streaming
超自然音色-燃燃2.0	BV407_V2_streaming
超自然音色-燃燃	BV407_streaming
通用女声	BV001_streaming
通用男声	BV002_streaming
擎苍	BV701_streaming
阳光青年	BV123_streaming
反卷青年	BV120_streaming
通用赘婿	BV119_streaming
古风少御	BV115_streaming
霸气青叔	BV107_streaming
质朴青年	BV100_streaming
温柔淑女	BV104_streaming
开朗青年	BV004_streaming
甜宠少御	BV113_streaming
儒雅青年	BV102_streaming
甜美小源	BV405_streaming
亲切女声	BV007_streaming
知性女声	BV009_streaming
诚诚	BV419_streaming
童童	BV415_streaming
亲切男声	BV008_streaming
译制片男声	BV408_streaming
懒小羊	BV426_streaming
清新文艺女声	BV428_streaming
鸡汤女声	BV403_streaming
智慧老者	BV158_streaming
慈爱姥姥	BV157_streaming
说唱小哥	BR001_streaming
活力解说男	BV410_streaming
影视解说小帅	BV411_streaming
解说小帅-多情感	BV437_streaming
影视解说小美	BV412_streaming
纨绔青年	BV159_streaming
直播一姐	BV418_streaming
反卷青年	BV120_streaming
沉稳解说男	BV142_streaming
潇洒青年	BV143_streaming
阳光男声	BV056_streaming
活泼女声	BV005_streaming
小萝莉	BV064_streaming
奶气萌娃	BV051_streaming
动漫海绵	BV063_streaming
动漫海星	BV417_streaming
动漫小新	BV050_streaming
天才童声	BV061_streaming
促销男声	BV401_streaming
促销女声	BV402_streaming
磁性男声	BV006_streaming
新闻女声	BV011_streaming
新闻男声	BV012_streaming
知性姐姐-双语	BV034_streaming
温柔小哥	BV033_streaming"""

if __name__ == '__main__':
    tts(text='欢迎来到语音合成的世界。', speaker='BV700_V2_streaming', save_path='tmp_tts.mp3')
