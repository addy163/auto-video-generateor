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
