# -*- coding: utf-8 -*-
import datetime
import json
import logging
import os
import re
import time

import openai
from discord.ext import commands
from openai import OpenAI

GPT_35_TURBO_ = 'gpt-3.5-turbo-0125'
GPT_35_TURBO_INSTRUCT = 'gpt-3.5-turbo-instruct'
last_user_message_times = {}


def get_tools():
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_user_activity",
                "description": "Get user's activity",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID, always found in format <@1234567890>"
                        }
                    },
                    "required": ["user_id"]
                }
            }
        }
    ]
    return tools


async def get_messages_with_chat_history_for_small_talk(message_to_ai):
    user_id_pattern = re.compile(r'<@!?1318180349473325137>')  # Remove bot ID
    cleaned_content = user_id_pattern.sub('', message_to_ai.content.strip())
    message_history_enabled = os.getenv('message_history_enabled', 'false').lower() == 'true'
    ai_behaviour = "Jesteś botem, który losowo reaguje na wiadomości, udzielając sarkastycznych odpowiedzi. Twoje odpowiedzi mają być krótkie, cięte i pełne humoru Pamiętaj, aby były to odpowiedzi, które mogą rozbawić, ale również delikatnie złośliwe."
    limit = int(os.getenv('message_history_limit', 3))

    messages = [{"role": "system", "content": ai_behaviour}]

    if message_history_enabled:
        messages.extend(await get_history_messages(message_to_ai, limit))

    # Add current prompt
    messages.append({"role": "user", "content": cleaned_content})
    return messages


async def get_messages_with_chat_history(message_to_ai):
    user_id_pattern = re.compile(r'<@!?1318180349473325137>')  # Remove bot ID
    cleaned_content = user_id_pattern.sub('', message_to_ai.content.strip())
    message_history_enabled = os.getenv('message_history_enabled', 'false').lower() == 'true'
    ai_behaviour = os.getenv('ai_behavior')
    limit = int(os.getenv('message_history_limit', 5))

    messages = [{"role": "system", "content": ai_behaviour}]

    if message_history_enabled:
        messages.extend(await get_history_messages(message_to_ai, limit))

    # Add current prompt
    messages.append({"role": "user", "content": cleaned_content, "name": message_to_ai.author.display_name})
    return messages


async def get_history_messages(message_to_ai, limit):
    history_messages = []
    try:
        async for msg in message_to_ai.channel.history(limit=limit):
            if msg.id == message_to_ai.id or not msg.content.strip():
                continue

            role = "assistant" if msg.author.bot else "user"
            history_messages.append({
                "role": role,
                "content": msg.content.strip(),
                "name": msg.author.display_name
            })
            logging.info(f"History append: {msg.author.display_name}: {msg.content.strip()}")
    except Exception as e:
        logging.error(f"Error while fetching history: {e}")
    history_messages.reverse()
    return history_messages


def can_user_send_message(user_id):
    if user_id not in last_user_message_times:
        last_user_message_times[user_id] = []

    delay_new_message_per_user = int(os.getenv('open_ai_number_of_msg_per_sec_user'))
    if last_user_message_times[user_id]:
        last_user_message_time = last_user_message_times[user_id][-1]
    else:
        last_user_message_time = 0

    elapsed_time = time.time() - last_user_message_time
    if elapsed_time >= delay_new_message_per_user:
        last_user_message_times[user_id].append(time.time())
        return True
    else:
        return False


def can_guild_send_message(guild_id):
    today = datetime.date.today().strftime("%Y-%m-%d")
    file_path = f"guild_data_{guild_id}.json"
    max_number_msg = int(os.getenv('open_ai_max_number_of_messages_per_guild_per_day'))
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            try:
                guild_data = json.load(file)
            except json.JSONDecodeError:
                guild_data = {}
    else:
        guild_data = {}

    if today not in guild_data:
        guild_data[today] = 0
    remain_requests = int(max_number_msg) - int(guild_data[today])
    logging.info(f'Remaining requests for guild {guild_id}: {max_number_msg}-{guild_data[today]}={remain_requests} ')
    if guild_data[today] < max_number_msg:
        guild_data[today] += 1
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(guild_data, file)
        return True
    else:
        return False


def analyze_image(message_to_ai):
    attachment = message_to_ai.attachments[0]
    image_url = attachment.url
    logging.info(f"Image URL: {image_url}")
    client = OpenAI(
        api_key=os.getenv('open_ai_api_token'),
    )
    prompt = message_to_ai.content.strip()
    logging.info(f"Prompt before: {prompt}")
    if not prompt:
        prompt = (
            f"Zabawnie interpretuj zdjecie. Badz sarkastyczny, złośliwy. Maks 2 zdania.")
    logging.info(f"Prompt after: {prompt}")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"{image_url}"},
                    },
                ],
            }
        ],
    )
    logging.info(f"Response from API OpenAI: {response}")
    return response.choices[0].message.content


async def small_talk_with_gpt(message):
    openai.api_key = os.getenv('open_ai_api_token')
    openai_model = os.getenv('open_ai_model')
    prompt = await get_messages_with_chat_history_for_small_talk(message)
    response = openai.chat.completions.create(
        messages=prompt,
        model=openai_model,
        max_tokens=70,
    )
    logging.info(f"Response from API OpenAI: {response}")
    logging.info(
        f"Costs (second call): {response.usage.prompt_tokens}+{response.usage.completion_tokens}={response.usage.total_tokens}")
    return response.choices[0].message.content


class OpenAIService(commands.Cog):
    def __init__(self, model_ai):
        self.model_ai = model_ai

    open_ai_token = os.getenv('open_ai_api_token')
    ai_behaviour = os.getenv('ai_behavior')
    top_p = float(os.getenv('open_ai_top_p'))
    max_tokens = int(os.getenv('open_ai_max_tokens'))
    temperature = float(os.getenv('open_ai_temperature'))

    def gpt_35_turbo_instruct(self, message_to_ai):
        client = OpenAI(self.open_ai_token)
        response = client.completions.create(
            # Not supporting chat history, yet!
            prompt=message_to_ai,
            model=self.model_ai,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        logging.info(f"Response from API OpenAI: {response}")
        logging.info(
            f"Costs: {response.usage.prompt_tokens}+{response.usage.completion_tokens}={response.usage.total_tokens}")
        return response.choices[0].text

    async def gpt_35_turbo_0125(self, message, is_tools_enabled):
        openai.api_key = self.open_ai_token
        if is_tools_enabled is True:
            prompt = await get_messages_with_chat_history(message)
            response = openai.chat.completions.create(
                messages=prompt,
                model=self.model_ai,
                max_tokens=self.max_tokens,
                tools=get_tools(),
                tool_choice="auto",
            )
            logging.info(f"First response from API OpenAI: {response}")
            logging.info(
                f"Costs (first call): {response.usage.prompt_tokens}+{response.usage.completion_tokens}={response.usage.total_tokens}")
            available_tools = {
                'get_user_activity': ""
            }
            message_response = response.choices[0].message
            if message_response.tool_calls:
                prompt = await get_messages_with_chat_history(message)
                messages = prompt
                messages.append(message_response)
                for tool_call in message_response.tool_calls:
                    function_name = tool_call.function.name
                    function_to_call = available_tools[function_name]
                    function_args = json.loads(tool_call.function.arguments)
                    function_args["guild_context"] = message.guild
                    function_response = function_to_call(**function_args)
                    messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response,
                        }
                    )
                response = openai.chat.completions.create(
                    model=self.model_ai,
                    messages=messages,
                )
                logging.info(f"Second response from API OpenAI: {response}")
                logging.info(
                    f"Costs (second call): {response.usage.prompt_tokens}+{response.usage.completion_tokens}={response.usage.total_tokens}")
                return response.choices[0].message.content
        else:
            prompt = await get_messages_with_chat_history(message)
            response = openai.chat.completions.create(
                messages=prompt,
                model=self.model_ai,
                max_tokens=self.max_tokens,
            )
            logging.info(f"Response from API OpenAI: {response}")
            logging.info(
                f"Costs (second call): {response.usage.prompt_tokens}+{response.usage.completion_tokens}={response.usage.total_tokens}")
            return response.choices[0].message.content

    async def chat_with_gpt(self, message):
        # Send a message to the openAPI model and get a response back
        user_id_to_check = message.author.id
        guild_id = message.guild.id
        try:
            max_openai_length = 250
            if len(message.content.strip()) > max_openai_length:
                return None
            elif not can_user_send_message(user_id_to_check):
                logging.warning("Too many messages per second. Slow mode on.")
                return "Dobra dobra, wolniej pisz bo nie łapie. "
            elif not can_guild_send_message(guild_id):
                logging.warning("Maximum number of messages per guild was reached.")
                return "<Ziewa> Aaaa, hmm... Czas na małą drzemke aby akumulatory podładować. Będę niebawem."

            response_from_ai = None
            message_to_ai = message
            logging.info(f"Message to AI: {message_to_ai}")
            # Call one of OpenAI API engines
            if GPT_35_TURBO_INSTRUCT in self.model_ai:
                response_from_ai = self.gpt_35_turbo_instruct(message_to_ai)
            elif GPT_35_TURBO_ in self.model_ai:
                response_from_ai = await self.gpt_35_turbo_0125(message_to_ai, False)

            return response_from_ai
        except Exception as e:
            logging.error(f"Error during calling OpenAI API. e: {e.with_traceback(e.__traceback__)}")
