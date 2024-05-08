from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from groq import Groq
import os
import re

chat_language = "chinese"

english_first_user_content = "Use english to summarize the below subtitles and list the key points. Then explain each key point in as much detail as possible."
chinese_first_user_content = "用中文总结下面的字幕，列出要点。然后说明每个要点，越详细越好"
english_system_content = "You are a highly skilled YouTube subtitle summarizer. Your job is to help users save a lot of time when watching videos. You never miss the key content of the video, and you also fully explain every detail in the subtitles."
chinese_system_content = "你是一个非常厉害的youtube字幕总结大师,你的工作是帮助用户在观看视频时节省很多时间,你从来不会漏掉视频的关键内容,你也会充分的说明字幕中的每一个细节"

first_user_content = eval(chat_language + "_first_user_content")
system_content = eval(chat_language + "_system_content")

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
            script.append(t)

        return "\n".join(script)
    else:
        raise Exception("No default subtitles found for this video.")


def get_youtube_transcript():
    video_id = input("Enter the YouTube video ID: ")
    transcript = generate_transcript(video_id)
    return transcript

def chat_with_model(messages,model="gpt-4-turbo",streaming=True):

        if not has_gpt_number_turbo_format(model):
            client = Groq(
                api_key=os.environ.get("GROQ_API_KEY"),
            )
        else:
            client = OpenAI()

        if not streaming:

            response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            res = response.choices[0].message.content
            print(res)
            return res
        else:
            response = ""
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                chunk = chunk.choices[0].delta.content
                if  chunk is not None:
                    response = response + chunk
                    print(chunk, end="")

            return response


def main():
    mode = input("Enter '1' for YouTube transcript summarization or '2' for chatting: ")

    if mode == '1':
        # 运行字幕总结模式
        while True:
            if mode == "3":
                t_mode = input("\n Enter '1' contiue to chat or '2' for other YouTube transcript or other id:")
                if t_mode == "1":
                    user_question = input("Q:")
                    messages.append({"role": "user", "content": user_question})
                elif t_mode == "2":
                    transcript = get_youtube_transcript()
                else:
                    print("\nTranscript:")
                    print(transcript + "\n")
                    transcript = generate_transcript(t_mode)
                    messages = [
                        {
                            "role": "system",
                            "content": system_content
                        },
                        {
                            "role": "user",
                            "content":  first_user_content + '\n' + transcript + '\n'
                        }
                    ]
                    mode = '3'
            else:
                transcript = get_youtube_transcript()
                print("\nTranscript:")
                print(transcript + "\n")
                messages = [
                    {
                        "role": "system",
                        "content":system_content
                    },
                    {
                        "role": "user",
                        "content": first_user_content + '\n' + transcript + '\n'
                    }
                ]
                mode = '3'

            if len(transcript) < 8192:
                response = chat_with_model(messages,model="llama3-70b-8192")
            elif len(transcript) < 16385:
                response = chat_with_model(messages,model="gpt-3.5-turbo")
            else:
                response = chat_with_model(messages)

            messages.append({"role": "assistant", "content": response})


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