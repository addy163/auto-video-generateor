"""
## 免费的自动视频生成

全部用免费的资源实现，体现完整流程和初步效果。

### 相关文档
[千帆ModelBuilder 部分ERNIE系列模型免费开放公告 - 千帆大模型平台 | 百度智能云文档 (baidu.com)](https://cloud.baidu.com/doc/WENXINWORKSHOP/s/wlwg8f1i3)
[ERNIE-Speed-128K - 千帆大模型平台 | 百度智能云文档 (baidu.com)](https://cloud.baidu.com/doc/WENXINWORKSHOP/s/6ltgkzya5)
[如何用GPT直接生成AI绘画？ - 知乎 (zhihu.com)](https://zhuanlan.zhihu.com/p/639471405)
[2.8k star! 用开源免费的edge-tts平替科大讯飞的语音合成服务 - 知乎 (zhihu.com)](https://zhuanlan.zhihu.com/p/685186002)
"""
import json
import re
import tempfile
import time

import gradio as gr
import pydub
import requests
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
from pydub.silence import detect_leading_silence

import tqdm

# import edge_tts

import warnings
import logging
import jieba

from common_utils import *
from common_utils import _root_dir

# 忽略特定警告
warnings.filterwarnings("ignore", category=UserWarning, module="moviepy.video.io.ffmpeg_reader")
# 或者降低 moviepy 的日志级别
logging.getLogger("moviepy.video.io.ffmpeg_reader").setLevel(logging.ERROR)


# 示例故事文本
def generate_story(prompt, template='{}', code_name="", story="", request: gr.Request = None):
    if request:
        code_name = f'{request.username}/{code_name}'
    get_savepath(code_name, '', mkdir_ok=True)
    story_file = get_savepath(code_name, 'story.txt', mkdir_ok=False)

    prompt_chat = template.format(prompt)
    if prompt:
        if os.path.isfile(story_file):
            story = open(story_file, encoding='utf8').read()
        else:
            story = chat(prompt_chat)
    elif not story:
        story = chat(pathlib.Path(code_name).name)
    else:
        story = story
    with open(story_file, 'wt', encoding='utf8') as fout:
        fout.write(story)
    print(f"generate_story 输入: {prompt}")
    print(f"generate_story 输出: {story}")
    return story


def save_story(story="", code_name="", request: gr.Request = None):
    if request:
        code_name = f'{request.username}/{code_name}'
    get_savepath(code_name, '', mkdir_ok=True)
    story_file = get_savepath(code_name, 'story.txt', mkdir_ok=False)

    with open(story_file, 'wt', encoding='utf8') as fout:
        fout.write(story)
    return story


# 分句
def split_sentences(story, code_name=""):
    # text_dir = get_savepath(code_name, 'text', mkdir_ok=True)

    # sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|。|！|？)\s*', story)
    # sentences = re.split(r'(["\'(\[“‘（【《]*.+?["\')\]”’）】》]*[\n。？?！!；;—…：:]+\s*)', story)
    # sentences = [w.strip() for sen in sentences for w in re.split(r"(.{10,56}\W+)", sen)
    #              if re.search(r'\w', w.strip())]
    # for i, sentence in enumerate(tqdm.tqdm(sentences, desc="split_sentences")):
    #     text_path = f'{text_dir}/text_{i + 100}.txt'
    #     with open(text_path, 'wt', encoding='utf8') as fout:
    #         fout.write(sentence)
    sentences = split_text(story, max_length=47)
    sentences = [w.strip() for w in sentences if re.search(r'\w', w.strip())]
    print(f"split_sentences 输入: {story}")
    print(f"split_sentences 输出: {sentences}")
    return sentences


def split_text(text, max_length=30):
    """
    文本切分算法

    参数:
        text: 要切分的文本
        max_length: 最大切分长度，默认为60

    返回:
        切分后的文本列表
    """
    # sentences = re.split(r'(["\'(\[“‘（【《]*.+?["\')\]”’）】》]*[\n。？?！!；;—…：:]+\s*)', story)

    # 如果文本长度小于等于最大长度，直接返回
    if len(text) <= max_length:
        return [text]

    # 第一级切分：按完整句子切分（句号、问号、感叹号等）
    sentences = re.split(r'([\n。？?！!；;…])', text)

    # 重新组合句子，保留标点
    result = []
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            sentence = sentences[i] + sentences[i + 1]
            if sentence.strip():  # 忽略空字符串
                result.append(sentence)

    # 处理最后一个可能不完整的句子
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        result.append(sentences[-1])

    # 检查每个句子长度，如果超过最大长度，进行第二级切分
    final_result = []
    for sentence in result:
        if len(sentence) <= max_length:
            final_result.append(sentence)
        else:
            # 第二级切分：按短句标点切分（分号、冒号等）
            sub_sentences = re.split(r'([：:，,—])', sentence)

            sub_result = []
            for j in range(0, len(sub_sentences) - 1, 2):
                if j + 1 < len(sub_sentences):
                    sub_sentence = sub_sentences[j] + sub_sentences[j + 1]
                    if sub_sentence.strip():
                        sub_result.append(sub_sentence)

            if len(sub_sentences) % 2 == 1 and sub_sentences[-1].strip():
                sub_result.append(sub_sentences[-1])

            # 检查每个子句长度，如果超过最大长度，进行第三级切分
            for sub_sentence in sub_result:
                if len(sub_sentence) <= max_length:
                    final_result.append(sub_sentence)
                else:
                    # 第三级切分：按停顿符号切分（逗号、顿号等）
                    clauses = re.split(r'(\W)', sub_sentence)

                    clause_result = []
                    for k in range(0, len(clauses) - 1, 2):
                        if k + 1 < len(clauses):
                            clause = clauses[k] + clauses[k + 1]
                            if clause.strip():
                                clause_result.append(clause)

                    if len(clauses) % 2 == 1 and clauses[-1].strip():
                        clause_result.append(clauses[-1])

                    # 检查每个子句长度，如果超过最大长度，进行第四级切分
                    for clause in clause_result:
                        if len(clause) <= max_length:
                            final_result.append(clause)
                        else:
                            # 第四级切分：按词边际切分
                            # 使用正则表达式匹配中文词语边界
                            words = jieba.cut(clause)

                            # 将词语组合成不超过最大长度的片段
                            current_chunk = ""
                            for word in words:
                                if len(current_chunk) + len(word) <= max_length:
                                    current_chunk += word
                                else:
                                    if current_chunk:
                                        final_result.append(current_chunk)
                                    current_chunk = word

                            if current_chunk:
                                final_result.append(current_chunk)

    return final_result


def get_tts_voices_edge_tts():
    """
Name: zh-CN-XiaoxiaoNeural
Gender: Female

Name: zh-CN-XiaoyiNeural
Gender: Female

Name: zh-CN-YunjianNeural
Gender: Male

Name: zh-CN-YunxiNeural
Gender: Male

Name: zh-CN-YunxiaNeural
Gender: Male

Name: zh-CN-YunyangNeural
Gender: Male

Name: zh-CN-liaoning-XiaobeiNeural
Gender: Female

Name: zh-CN-shaanxi-XiaoniNeural
Gender: Female

Name: zh-HK-HiuGaaiNeural
Gender: Female

Name: zh-HK-HiuMaanNeural
Gender: Female

Name: zh-HK-WanLungNeural
Gender: Male

Name: zh-TW-HsiaoChenNeural
Gender: Female

Name: zh-TW-HsiaoYuNeural
Gender: Female

Name: zh-TW-YunJheNeural
Gender: Male

    :return:
    """
    voices = ['zh-CN-XiaoxiaoNeural/Female', 'zh-CN-XiaoyiNeural/Female', 'zh-CN-YunjianNeural/Male',
              'zh-CN-YunxiNeural/Male',
              'zh-CN-YunxiaNeural/Male', 'zh-CN-YunyangNeural/Male', 'zh-CN-liaoning-XiaobeiNeural/Female',
              'zh-CN-shaanxi-XiaoniNeural/Female', 'zh-HK-HiuGaaiNeural/Female', 'zh-HK-HiuMaanNeural/Female',
              'zh-HK-WanLungNeural/Male', 'zh-TW-HsiaoChenNeural/Female', 'zh-TW-HsiaoYuNeural/Female',
              'zh-TW-YunJheNeural/Male']
    return voices


def get_tts_voices():
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

    voice_type_list = []
    for line in voice_type_desc.split('\n'):
        zh, en = line.strip().split('\t')
        voice_type_list.append(f'{en}/{zh}')
    return voice_type_list


zh_voices = get_tts_voices()

import pyttsx3

tts_engine = pyttsx3.init()

# 获取语音属性
rate = tts_engine.getProperty('rate')
volume = tts_engine.getProperty('volume')
voices = tts_engine.getProperty('voices')

# 设置语音属性（可选）
tts_engine.setProperty('voice', voices[0].id)  # 音色
tts_engine.setProperty('rate', rate)  # 语速
tts_engine.setProperty('volume', volume)  # 音量


# from gtts import gTTS


def synthesize_speech(sentences, voice="zh-CN-YunxiNeural", rate='+0%', volume='+0%', pitch='+0Hz', code_name="",
                      save_path=''):
    if save_path:
        sentences = [sentences]

    audio_dir = get_savepath(code_name, 'audio', mkdir_ok=True)

    voice = voice.split('/')[0]
    rate = "+{}%".format((rate - 50) * 2).replace('+-', '-')
    volume = "+{}%".format((volume - 50) * 2).replace('+-', '-')
    pitch = "+{}Hz".format((pitch - 50)).replace('+-', '-')

    audio_files = []
    for i, sentence in enumerate(tqdm.tqdm(sentences, desc="synthesize_speech")):
        if not sentence:
            continue
        if save_path:
            audio_path = save_path
        else:
            audio_path = f"{audio_dir}/audio_{i + 100}.wav"
            if os.path.isfile(audio_path):
                audio_files.append(audio_path)
                yield audio_path
                continue
        sentence = re.sub(r'[\s"\'\-=\{\}]+', ' ', sentence)

        # edge-tts --pitch=-50Hz --voice zh-CN-YunyangNeural --text "大家好，欢迎关注我的微信公众号：AI技术实战，我会在这里分享各种AI技术、AI教程、AI开源项目。" --write-media hello_in_cn.mp3
        # fixme edge-tts废了，语音合成方面自行调大厂TTS接口或者自行部署模型吧！
        # os.system(
        #     f'edge-tts --voice {voice} --rate={rate} --volume={volume} --pitch={pitch} --text "{sentence}" --write-media "{audio_path}"')
        # communicate = edge_tts.Communicate(sentence, voice=voice, rate=rate, volume=volume, pitch=pitch)
        # await communicate.save(audio_path)

        # try:
        #     # 用谷歌TTS，要科学上网！！！
        #     tts = gTTS(text=sentence, lang="zh")
        #     tts.save(audio_path)
        # except Exception as e:
        #     print(e)

        tts(text=sentence, speaker=voice, save_path=audio_path)

        # 如果edge-tts合成失败，则用默认声音
        if not os.path.isfile(audio_path) or os.path.getsize(audio_path) < 1024:
            tts_engine.save_to_file(text=sentence, filename=audio_path)
            tts_engine.runAndWait()

        # seg = pydub.AudioSegment.from_file(audio_path)
        # sil_head = detect_leading_silence(seg, silence_threshold=-64)
        # sil_tail = detect_leading_silence(seg.reverse(), silence_threshold=-64)
        # seg = seg[max(0, sil_head - 200): max(1, len(seg) - sil_tail + 200)]
        # seg.export(audio_path, format='wav')

        audio_files.append(audio_path)
        yield audio_path
    # print(f"synthesize_speech 输入: {sentences}")
    # print(f"synthesize_speech 输出: {audio_files}")
    # return audio_files


def text2image(text, prompt, size="1280x720/抖音B站"):
    """
    `![Image](https://image.pollinations.ai/prompt/{prompt}?width=<Number>&height=<Number>)`

你应该将prompt替换为上面的文字，并配上合适的宽高尺寸。请注意尺寸最多不超过1024px。同时，你需要将URL Encode处理，最终的结果就像下面这样：

![Image](https://image.pollinations.ai/prompt/A%20beautiful%2022-year-old%20Chinese%20woman%20with%20long%20black%20hair,%20big%20eyes,%20and%20a%20pair%20of%20dimples,%20smiling%20at%20the%20camera?width=768&height=512)

在使用Pollinations.ai进行图像生成时，输入控制字段通常涉及以下几个步骤：

访问Pollinations.ai平台：首先，您需要打开浏览器并访问Pollinations.ai的官方网站。

选择模型：如果平台提供了多个AI模型，选择一个适合您需求的模型来进行图像生成。

输入描述：在提供的文本框中输入描述性文本，这将作为AI生成图像的主要依据。描述应尽可能详细，包括场景、颜色、风格、主题等元素。

设置参数：如果需要，您可以设置图像的宽度、高度、随机种子等参数。这些参数可以帮助您控制图像的尺寸和确保生成的一致性。

选择风格和流派：根据需要，选择图像的视觉风格（如现实主义、卡通等）和流派（如科幻、奇幻等）。

艺术家参考：如果需要，您可以指定一个艺术家或风格作为参考，以便AI生成的图像具有特定的艺术风格。

提交生成请求：完成所有设置后，点击生成按钮提交您的请求。

查看和保存结果：AI将根据您提供的描述和参数生成图像。生成完成后，您可以查看图像，并根据需要进行保存或进一步编辑。

以下是一个示例，展示如何构建一个请求：

https://image.pollinations.ai/prompt/%5Bdescription%5D?width=1920&height=1080&seed=12345&style=realistic&genre=scifi&artist=Vincent_van_Gogh
在这个例子中：

%5Bdescription%5D 是URL编码后的描述字段，实际使用时应替换为具体的描述文本。
width 和 height 分别设置了图像的宽度和高度。
seed 是随机种子，用于生成图像的一致性。
style 指定了图像的风格，这里是“realistic”（现实主义）。
genre 指定了图像的流派，这里是“scifi”（科幻）。
artist 指定了参考的艺术家，这里是“Vincent_van_Gogh”（文森特·梵高）。
    :param prompt:
    :return:
    """
    # sentence = re.sub(r'[\s"\'\-=\{\}]+', ' ', sentence)
    prompt_image = re.sub(r'[\s"\'\-=\{\}&?]+', " ", prompt.format(text) if '{}' in prompt else prompt)
    wxh, desc = size.split('/')
    width, height = wxh.split('x')
    seed = ord(desc[-1])
    if prompt_image.startswith('@model#'):
        g = re.match(r'@model#(\w+?)#(.+)$', prompt_image)
        if g:
            model = g.group(1)
            prompt_image = g.group(2)
        else:
            model = 'flux'
    else:
        model = 'flux'  # turbo
    img_url = (f'https://image.pollinations.ai'
               f'/prompt/{prompt_image}'
               f'?width={width}&height={height}&seed={seed}&model={model}&nologo=true')
    try:
        response = requests.get(img_url, verify=False, timeout=(30, 60))
    except Exception as e:
        print(dict(img_url=img_url, error=e))
        import traceback
        traceback.print_exc()
        response = None

    if response and response.status_code == 200:
        img_data = response.content
    else:
        print(dict(response=response, img_url=img_url))
        text = re.sub(r'(\W*\w{1,20}\W+|\w{10,20})', r'\1\n', text)  # 短句单独成行
        # text = re.sub(r'(\w+?\W+)', r'\1\n', text)
        # 自动设置默认字体大小，一般为图像宽度的1/32
        font_size = int(wxh.split('x')[0]) // 28
        img_path = add_subtitle(text, image=f'{wxh}/73-109-137', font=f"msyh.ttc+{font_size}", location=(0.5, 0.5),
                                color=(255, 255, 255), image_output='')
        img_data = open(img_path, 'rb').read()
    return img_data


def add_subtitle(text, image="1280x720/73-109-137", font="msyh.ttc+32", location=(0.5, 0.85), color=(255, 255, 255),
                 image_output=''):
    if re.match(r'\d+x\d+/\d+-\d+-\d+', image):
        size, desc = image.split('/')
        width, height = size.split('x')
        red, green, blue = desc.split('-')
        img_path = image

        img = Image.new('RGB', (int(width), int(height)), color=(int(red), int(green), int(blue)))
    else:
        img_path = image
        img = Image.open(img_path)

        width, height = img.size

    d = ImageDraw.Draw(img)

    font_name, font_size = font.split('+')
    if font_size == '-1':
        font_size = int(width) // 32
    if int(font_size):
        # 使用Windows系统中的微软雅黑字体
        font_path = f"C:/Windows/Fonts/{font_name}"  # 微软雅黑字体文件路径
        if not os.path.isfile(font_path):
            font_path = os.path.join(_root_dir, f'static/fonts/{font_name}')
        font_file = ImageFont.truetype(font_path, int(font_size))
        bbox = d.textbbox((0, 0), text, font=font_file)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        width, height = img.size
        x = (width - text_w) * location[0]
        y = (height - text_h) * location[1]
        d.text((x, y), text, font=font_file, fill=color)
        outpath = image_output or (
            img_path if os.path.isfile(img_path) else
            tempfile.NamedTemporaryFile(prefix='subtitle-', suffix='.png', delete=False).name)
        img.save(outpath)
    else:
        # 如果字幕size为0，则不显示字幕
        outpath = img_path
    return outpath


def generate_images(sentences, size="1280x720/抖音B站", font="msyh.ttc+40", person="{}", code_name="", save_path=''):
    if save_path:
        sentences = [sentences]

    image_dir = get_savepath(code_name, 'image', mkdir_ok=True)

    # prompt_chat = f'内容：{"".join(sentences)}\n\n请分析以上内容，生成4个词左右的描述图像风格词语，分别从色彩、风格、内容等角度描述，最后仅输出12字以下的文字，输出样例：清新色调，山水画风格，中国寓言故事。'
    # prompt_kw = chat(prompt_chat)
    images = []
    for i, sentence in enumerate(tqdm.tqdm(sentences, desc="generate_images")):
        if not sentence:
            continue
        if save_path:
            img_path = save_path
        else:
            img_path = f"{image_dir}/image_{i + 100}.png"
            if os.path.isfile(img_path):
                images.append(img_path)
                yield img_path
                continue
        # prompt_chat = f'请把以下正文内容翻译为英文，仅输出翻译后的英文内容。正文内容：{sentence}'
        # prompt_chat = f'请把根据内容生成简明扼要的描述内容场景的句子，不能包含人物，输出内容不能包含除场景描述外的其他文字，仅输出场景描述。正文内容：{sentence}'
        # prompt_img = chat(prompt_chat)
        # f'图像风格：{prompt_kw} 图像内容：{sentence} 注意：图中所有人物都用{person}代替，用{person}替换人，去除各种文字，不要任何文字！'

        # prompt_path = f"{image_dir}/image_{i}_prompt.txt"
        # with open(prompt_path, 'wt', encoding='utf8') as fout:
        #     fout.write(prompt_image)

        img_data = text2image(sentence, person, size)

        with open(img_path, 'wb') as fout:
            fout.write(img_data)

        text = re.sub(r'(\W*.{1,24}\W+|\w{12,24})', r'\1\n', sentence)  # 短句单独成行
        # text = re.sub(r'(["\'(\[“‘（【《]*\w+?["\')\]”’）】》]*[。？?！!；;—…：:，,.\-~|/\\]+\s*)', r'\1\n', sentence)
        img_path = add_subtitle(text, image=img_path, font=font, location=(0.5, 0.85),
                                color=(255, 255, 255), image_output=img_path)

        images.append(img_path)

        yield img_path
    # print(f"generate_images 输入: {sentences}")
    # print(f"generate_images 输出: {images}")
    # return images


def create_resources(texts, prompts, audios, images, code_name):
    """
    ValueError: 'C:\\Users\\kuang\\AppData\\Local\\Temp\\gradio\\610284d670ce6bd048186063a1d5ab89baf955090d8040b446631762a77179ef\\audio_100.wav' is not in the subpath of 'C:\\Users\\kuang\\github\\kuangdd2024\\auto-video-generateor\\mnt\\materials\\abc\\斯坦福监狱实验104' OR one path is relative and the other is absolute.

    :param texts:
    :param prompts:
    :param audios:
    :param images:
    :param code_name:
    :return:
    """
    _save_dir = get_savepath(code_name, '', mkdir_ok=True)

    resource_dir = get_savepath(code_name, 'resource', mkdir_ok=True)

    results = []
    for i, (sen, pmt, aud, img) in enumerate(tqdm.tqdm(zip(texts, prompts, audios, images), desc='create_resources')):
        if not sen:
            continue
        res_path = f"{resource_dir}/resource_{i + 100}.json"

        # dt = dict(index=i, text=sen, prompt=pmt,
        #           audio=get_relpath(code_name, aud),
        #           image=get_relpath(code_name, img),
        #           resource=get_relpath(code_name, res_path))
        dt = dict(index=i, text=sen, prompt=pmt,
                  audio=f'audio/audio_{i + 100}.wav',  # os.path.basename(aud)
                  image=f'image/image_{i + 100}.png',  # os.path.basename(img)
                  resource=get_relpath(code_name, res_path))
        with open(res_path, 'wt', encoding='utf8') as fout:
            json.dump(dt, fout, ensure_ascii=False, indent=4)
        yield dt
        results.append([i, sen, pmt, aud, img, res_path])


# 生成视频
def create_video(results, code_name="", save_path='', request: gr.Request = None):
    # print(dict(save_path=save_path))
    if request:
        code_name = f'{request.username}/{code_name}'
    _save_dir = get_savepath(code_name, '', mkdir_ok=True)

    if not save_path:
        video_file = get_savepath(code_name, 'video.mp4', mkdir_ok=False)
        if os.path.isfile(video_file):
            return video_file
    else:
        video_file = save_path
    print(dict(video_file=video_file))
    # if not isinstance(results, list):
    #     results = results.to_numpy()
    clips = []
    for dt in tqdm.tqdm(results, desc="create_video"):
        try:
            audio = AudioFileClip(get_abspath(code_name, dt["audio"]))
            image = ImageClip(get_abspath(code_name, dt["image"]))
            video = image.set_duration(audio.duration).set_audio(audio)
        except Exception as e:
            time.sleep(500)
            print(e, dt)
            audio = AudioFileClip(get_abspath(code_name, dt["audio"]))
            image = ImageClip(get_abspath(code_name, dt["image"]))
            video = image.set_duration(audio.duration).set_audio(audio)
        # try:
        #     video.preview()  # 测试能否播放
        # except Exception as e:
        #     print("损坏的视频片段:", dt, e)

        f1, msg1 = is_video_renderable(video)
        f2, msg2 = check_audio_video_sync(video)
        if f1 and f2:
            clips.append(video)
        else:
            print("损坏的视频片段:", dt)
            print(msg1, msg1)

    final_video = concatenate_videoclips(clips, method="compose")
    final_video.write_videofile(video_file, fps=4)  # 24
    print(f"create_video 输入: {results}")
    print(f"create_video 输出: {video_file}")
    return video_file


def is_video_renderable(video):
    try:
        # 渲染第一帧并保存为临时图片
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            video.save_frame(tmp.name, t=0)  # t=0表示第一帧
        os.unlink(tmp.name)  # 验证后删除
        return True, "可正常渲染帧"
    except Exception as e:
        return False, f"渲染失败：{str(e)}"


def is_video_valid(video):
    try:
        # 检查时长（必须>0）
        if video.duration <= 0:
            return False, "视频时长异常（≤0）"

        # 检查尺寸（宽高必须>0）
        if video.size[0] <= 0 or video.size[1] <= 0:
            return False, "视频尺寸异常（宽高≤0）"

        # 检查帧率（通常≥1）
        if video.fps < 1:
            return False, "帧率异常（<1）"

        # 若有音频，检查音频属性
        if hasattr(video, 'audio') and video.audio is not None:
            if video.audio.duration <= 0:
                return False, "音频时长异常（≤0）"

        return True, "视频属性正常"
    except Exception as e:
        return False, f"属性检查失败：{str(e)}"


def check_audio_video_sync(video):
    if not hasattr(video, 'audio') or video.audio is None:
        return True, "无音频，无需同步"

    # 允许微小误差（如0.1秒内）
    if abs(video.duration - video.audio.duration) < 0.1:
        return True, "音视频时长匹配"
    else:
        return False, f"音视频时长不匹配（视频：{video.duration}s，音频：{video.audio.duration}s）"


def generate_results_base(story, size, font, person, voice_input, rate_input, volume_input, pitch_input, code_name=""):
    # global _save_dir
    _save_dir = get_savepath(code_name, '', mkdir_ok=True)
    metadata_file = get_savepath(code_name, 'metadata.json', mkdir_ok=False)

    sents = split_sentences(story, code_name=code_name)

    audios = synthesize_speech(sents, voice_input, rate_input, volume_input, pitch_input, code_name=code_name)
    audios = list(audios)

    images = generate_images(sents, size, font, person, code_name=code_name)
    images = list(images)

    results = create_resources(sents, prompts=[person for _ in sents], audios=audios, images=images,
                               code_name=code_name)
    results = list(results)

    with open(metadata_file, 'wt', encoding='utf8') as fout:
        dt = dict(
            topic='', template='',
            story=story,
            size=size, font=font, person=person,
            voice=voice_input, rate=rate_input, volume=volume_input, pitch=pitch_input,
            code_name=code_name, save_dir=_save_dir, resource_count=len(results)
        )
        json.dump(dt, fout, ensure_ascii=False, indent=4)

    return results


def one_click_pipeline(theme, template, size, font, person, voice_input, rate_input, volume_input, pitch_input,
                       code_name=""):
    get_savepath(code_name, 'text', mkdir_ok=True)

    story = generate_story(theme, template, code_name)
    yield story, None, None
    results = generate_results_base(story, size, font, person, voice_input, rate_input, volume_input, pitch_input,
                                    code_name)
    yield story, results, None
    video = create_video(results, code_name)
    yield story, results, video


from moviepy.editor import VideoFileClip, CompositeVideoClip
from moviepy.video.VideoClip import ImageClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import re
from datetime import datetime

import os
from pydub import AudioSegment
from pydub.utils import make_chunks
import math


def generate_subtitles_from_audio(audio_files, subtitles, output_path):
    """
    根据音频文件列表和对应的字幕生成SRT字幕文件

    参数:
    audio_files: 音频文件路径列表，按拼接顺序排列
    subtitles: 对应的字幕文本列表，长度应与audio_files相同
    output_path: 输出的SRT字幕文件路径
    silence_threshold: 静音检测阈值(dBFS)，低于此值被认为是静音
    min_silence_len: 最小静音长度(毫秒)，用于检测音频分段

    返回:
    无，直接生成SRT文件
    """

    # 检查输入参数
    if len(audio_files) != len(subtitles):
        raise ValueError("音频文件列表和字幕列表长度必须相同")

    # 初始化变量
    total_duration = 0  # 累计时长(毫秒)
    subtitle_entries = []  # 存储字幕条目

    # 处理每个音频文件
    for i, (audio_file, subtitle_text) in enumerate(zip(audio_files, subtitles)):
        # 检查音频文件是否存在
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"音频文件不存在: {audio_file}")

        # 加载音频文件
        audio = AudioSegment.from_file(audio_file)
        audio_duration = len(audio)  # 音频时长(毫秒)

        # 计算开始和结束时间
        start_time = total_duration
        end_time = total_duration + audio_duration

        # 添加到字幕条目
        subtitle_entries.append({
            'index': i + 1,
            'start': start_time,
            'end': end_time,
            'text': subtitle_text
        })

        # 更新累计时长
        total_duration = end_time

    # 将时间转换为SRT格式
    def format_time(ms):
        """将毫秒转换为SRT时间格式: HH:MM:SS,mmm"""
        hours = ms // 3600000
        ms %= 3600000
        minutes = ms // 60000
        ms %= 60000
        seconds = ms // 1000
        ms %= 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"

    # 生成SRT文件内容
    srt_content = ""
    for entry in subtitle_entries:
        start_str = format_time(entry['start'])
        end_str = format_time(entry['end'])
        srt_content += f"{entry['index']}\n{start_str} --> {end_str}\n{entry['text']}\n\n"

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)

    print(f"字幕文件已生成: {output_path}")


def parse_srt(srt_file):
    """解析SRT字幕文件"""
    subtitles = []
    with open(srt_file, 'rt', encoding='utf-8') as f:
        content = f.read()

    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\d+\n|\n*$)'
    matches = re.findall(pattern, content, re.DOTALL)

    for match in matches:
        index, start, end, text = match
        text = re.sub(r'\s+', ' ', text.strip())

        start_time = datetime.strptime(start, '%H:%M:%S,%f')
        end_time = datetime.strptime(end, '%H:%M:%S,%f')

        start_seconds = start_time.hour * 3600 + start_time.minute * 60 + start_time.second + start_time.microsecond / 1000000
        end_seconds = end_time.hour * 3600 + end_time.minute * 60 + end_time.second + end_time.microsecond / 1000000

        subtitles.append((start_seconds, end_seconds, text))

    return subtitles


def create_subtitle_image(text, video_size=(1280, 720), font="msyh.ttc+-1", location=(0.5, 0.85),
                          color=(0, 0, 0)):
    width, height = video_size
    img = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))

    d = ImageDraw.Draw(img)

    font_name, font_size = font.split('+')
    if font_size == '-1':
        if len(text) < 32:
            font_size = int(width) // 32
        elif 32 <= len(text) < 40:
            font_size = int(width) // 40
        elif 40 <= len(text) < 48:
            font_size = int(width) // 48
        else:
            font_size = int(width) // 64

    if int(font_size):
        # 使用Windows系统中的微软雅黑字体
        font_path = f"C:/Windows/Fonts/{font_name}"  # 微软雅黑字体文件路径
        if not os.path.isfile(font_path):
            font_path = os.path.join(_root_dir, f'static/fonts/{font_name}')
        font_file = ImageFont.truetype(font_path, int(font_size))
        bbox = d.textbbox((0, 0), text, font=font_file)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        # width, height = img.size
        x = (width - text_w) * location[0]
        y = (height - text_h) * location[1]
        d.text((x, y), text, font=font_file, fill=color)

        # 先绘制白色描边
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx == 0 and dy == 0:
                    continue
                d.text((x + dx, y + dy), text, font=font_file, fill="white")

        # 再绘制黑色文本
        d.text((x, y), text, font=font_file, fill=color)

        # 转换为numpy数组
        return np.array(img)
    else:
        # 如果字幕size为0，则不显示字幕
        return np.array(img)


def add_subtitles_to_video(video_path, srt_path, output_path, font="msyh.ttc+-1",
                           location=(0.5, 0.9), color=(0, 0, 0)):
    """使用PIL为视频添加字幕"""
    # 加载视频
    video = VideoFileClip(video_path)
    video_width, video_height = video.size

    # 解析字幕文件
    subtitles = parse_srt(srt_path)

    # 创建字幕剪辑列表
    subtitle_clips = []

    for start, end, text in subtitles:
        # 创建字幕图像
        subtitle_img = create_subtitle_image(text, video_size=(video_width, video_height),
                                             font=font, location=location, color=color)

        # 创建图像剪辑
        img_clip = ImageClip(subtitle_img, duration=end - start)

        # 设置位置（底部）
        img_clip = img_clip.set_position(('center', 'center')).set_start(start)

        subtitle_clips.append(img_clip)

    # 将字幕合成到视频上
    final_video = CompositeVideoClip([video] + subtitle_clips)

    # 输出视频
    final_video.write_videofile(output_path, codec='libx264', audio_codec='aac')

    # 关闭视频对象
    video.close()
    final_video.close()
