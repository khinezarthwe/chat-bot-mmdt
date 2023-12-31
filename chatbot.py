import os

import gradio as gr
import requests
from dotenv import load_dotenv, find_dotenv
from text_generation import Client

requests.adapters.DEFAULT_TIMEOUT = 60


_ = load_dotenv(find_dotenv()) # read local .env file
hf_api_key = os.environ['HF_API_KEY']
hf_end_point = os.environ['HF_API_FALCOM_BASE']

client = Client(hf_end_point, headers={"Authorization": f"Bearer {hf_api_key}",
                                       "Content-Type": "application/json"},
                timeout=120)


def format_chat_prompt(message, chat_history, instruction):
    prompt = f"System:{instruction}"
    for turn in chat_history:
        user_message, bot_message = turn
        prompt = f"{prompt}\nUser: {user_message}\nAssistant: {bot_message}"
    prompt = f"{prompt}\nUser: {message}\nAssistant:"
    return prompt


def respond(message, chat_history, instruction, temperature=0.7):
    prompt = format_chat_prompt(message, chat_history, instruction)
    chat_history = chat_history + [[message, ""]]
    stream = client.generate_stream(prompt,
                                      max_new_tokens=1024,
                                      stop_sequences=["\nUser:", "<|endoftext|>"],
                                      temperature=temperature)
                                      #stop_sequences to not generate the user answer
    acc_text = ""
    #Streaming the tokens
    for idx, response in enumerate(stream):
            text_token = response.token.text

            if response.details:
                return

            if idx == 0 and text_token.startswith(" "):
                text_token = text_token[1:]

            acc_text += text_token
            last_turn = list(chat_history.pop(-1))
            last_turn[-1] += acc_text
            chat_history = chat_history + [last_turn]
            yield "", chat_history
            acc_text = ""


with gr.Blocks() as demo:
    chatbot = gr.Chatbot(height=240) #just to fit the notebook
    msg = gr.Textbox(label="Do you wanna ask something to us?")
    with gr.Accordion(label="Advanced options", open=False):
        system = gr.Textbox(label="System message", lines=2,
                            value="A conversation between a user and an LLM-based AI assistant. The assistant gives helpful and honest answers.")
        temperature = gr.Slider(label="temperature", minimum=0.1, maximum=1, value=0.7, step=0.1)
    btn = gr.Button("Submit")
    clear = gr.ClearButton(components=[msg, chatbot], value="Clear console")

    btn.click(respond, inputs=[msg, chatbot, system], outputs=[msg, chatbot])
    msg.submit(respond, inputs=[msg, chatbot, system], outputs=[msg, chatbot]) #Press enter to submit
gr.close_all()
demo.queue().launch(share=True, server_port=int(os.environ['PORT']))


