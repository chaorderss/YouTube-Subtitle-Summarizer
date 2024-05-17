from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from groq import Groq
import os
import re
import time
chat_language = "chinese"
# default_model = "gpt-4o"
default_model = "gpt-3.5-turbo"
base_url = "https://openai.shopsde.uk/v1"
english_first_user_content = """
                        Use english to summarize the below subtitles and list the key points and explain each key point in as much detail as possible,
                        in [] is the second of each sentence begin and end,
                        for example 'hi![1:00,4:00]' the [1:01,4:02] is the hi! subtitle begin at 1 minus and 1 second and end at 4 minus and 2 second of the video.
                        """
chinese_first_user_content = "用中文总结下面的字幕，详细的列出重点的内容"
english_system_content = "You are a highly skilled YouTube subtitle summarizer. Your job is to help users save a lot of time when watching videos. You never miss the key content of the video, and you also fully explain every detail in the subtitles."
chinese_system_content = """
                    你是一个非常厉害的youtube字幕总结大师,
                    你的工作是帮助用户在观看视频时节省很多时间,
                    你从来不会漏掉视频的关键内容,
                    你也会充分的说明字幕中的每一个细节，
                    方括号 [] 表示每个句子字幕的起止时间。例如，“你好！[1:01,4:02]” 表示“你好!”字幕在视频的第1分1秒开始,第 4分2秒结束.
                    """

first_user_content = eval(chat_language + "_first_user_content")
system_content = eval(chat_language + "_system_content")
transcript_len_allowed = 16000

def has_gpt_number_turbo_format(text):
  """
  This function checks if a string has the format "gpt-<number>-turbo" where <number> can be any number and returns True or False.

  Args:
      text: The string to be checked.

  Returns:
      True if the string has the format "gpt-<number>-turbo", False otherwise.
  """
  pattern = r"gpt-\d+(\.\d+)?-turbo"
  return bool(re.search(pattern, text))

def seconds_to_minutes_seconds(start_time, end_time):
  """
  将 [秒, 秒] 格式的时间转换为 [分:秒 - 分:秒] 格式，保留小数点后一位。

  Args:
    start_time: 开始时间（秒）。
    end_time: 结束时间（秒）。

  Returns:
    [-分:秒 - 分:秒] 格式的时间字符串。
  """

  start_minutes = int(start_time // 60)
  start_seconds = start_time % 60
  end_minutes = int(end_time // 60)
  end_seconds = end_time % 60

  return f"[{start_minutes}:{start_seconds:.1f}-{-end_minutes}:{end_seconds:.1f}]"

def generate_transcript(id):
    available_languages = YouTubeTranscriptApi.list_transcripts(id)
    default_language = None
    for transcript in available_languages:
        print(
            transcript.video_id,
            transcript.language,
            transcript.language_code,
            transcript.is_generated,
        )

    if transcript.language_code:
        transcript = YouTubeTranscriptApi.get_transcript(id, languages=(transcript.language_code,))
        script = []

        for text in transcript:
            t = text["text"]
            start = text['start']
            duration = text['duration']
            snt = f"{t}{seconds_to_minutes_seconds(start,start+duration)}"
            script.append(snt)

        return "\n".join(script)
    else:
        raise Exception("No default subtitles found for this video.")


def get_youtube_transcript():
    video_id = input("Enter the YouTube video ID: ")
    transcript = generate_transcript(video_id)
    return transcript

def  chat_with_model(message_list,model="gpt-4-turbo",streaming=True):

        if not has_gpt_number_turbo_format(model):
            client = Groq(
                api_key=os.environ.get("GROQ_API_KEY"),
            )
        else:
            client = OpenAI(base_url=base_url)
        response_all = ""
        for message in message_list:

            if not streaming:

                response = client.chat.completions.create(
                    model=model,
                    messages=message
                )
                response = response.choices[0].message.content

            else:
                response = ""
                stream = client.chat.completions.create(
                    model=model,
                    messages=message,
                    stream=True,
                )
                for chunk in stream:
                    chunk = chunk.choices[0].delta.content
                    if  chunk is not None:
                        response = response + chunk
                        print(chunk, end="")
                response = response + "\n"

            response_all = response_all + response

        return response_all

def generate_message(transcript="",ai_response="",additional_input=""):
    message_list = []
    messages = [
            {
                "role": "system",
                "content": system_content
            }
        ]
    if transcript != "":
        s_len = len(transcript)

        for trans_number in range(s_len // transcript_len_allowed + 1):
            part_transcript = transcript[trans_number * transcript_len_allowed:(trans_number + 1) * (s_len if s_len < transcript_len_allowed else transcript_len_allowed)]

            messages.append(
                {
                    "role": "user",
                    "content":  first_user_content + '\n' + part_transcript + '\n'
                }
            )

            if ai_response !="":
                messages.append(
                    {
                        "role": "assistant",
                        "content": ai_response
                    }
                )
            if additional_input != "":
                messages.append(
                    {
                        "role": "user",
                        "content":  additional_input
                    }
                )

            message_list.append(messages)
            messages = [
            {
                "role": "system",
                "content": system_content
            }
            ]
    else:
        if ai_response !="":
            messages.append(
                {
                    "role": "assistant",
                    "content": ai_response
                }
            )
        if additional_input != "":
            messages.append(
                {
                    "role": "user",
                    "content":  additional_input
                }
            )
        message_list.append(messages)

    return message_list

def main():
    mode = input("Enter '1' for YouTube transcript summarization or '2' for chatting: ")

    if mode == '1':
        # 运行字幕总结模式
        while True:
            if mode == "3":
                t_mode = input("\n Enter '1' contiue to chat or '2' for other YouTube transcript or other id:")
                if t_mode == "1":
                    user_question = input("Q:")
                    message_list = generate_message(additional_input = user_question)
                elif t_mode == "2":
                    transcript = get_youtube_transcript()
                else:
                    print("\nTranscript:")
                    print(transcript + "\n")
                    transcript = generate_transcript(t_mode)
                    message_list = generate_message(transcript = transcript)
                    mode = '3'
            else:
                transcript = get_youtube_transcript()
                print("\nTranscript:")
                print(transcript + "\n")
                message_list = generate_message(transcript = transcript)

                mode = '3'
            print("transcript len:%d" %len(transcript))

            # if len(transcript) < 8192:
            #     response = chat_with_model(message_list,model="llama3-70b-8192")
            # else:
            # response = chat_with_model(message_list,model="gpt-3.5-turbo")
            response = chat_with_model(message_list,model=default_model)

            message_list = generate_message(ai_response = response)



    elif mode == '2':
        # 运行聊天模式
        messages = [
            {"role": "system", "content": "You are now chatting with the AI. If the user input is not Chinese, answer it first, then translate the respond to Chinese. If prompt is Chinese, answer it with Chinese."}
        ]
        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                break
            messages.append({"role": "user", "content": user_input})
            response = chat_with_model(messages)

            messages.append({"role": "assistant", "content": response})

    else:
        print("Invalid mode selected. Exiting program.")
        return
if __name__ == "__main__":
    main()