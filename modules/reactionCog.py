# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import os
import random
import re

from discord.ext import commands

from services.common import get_busy_response
from services.open_ai_service import OpenAIService, analyze_image, small_talk_with_gpt


async def send_response_in_parts(channel, response):
    try:
        if not response.strip():
            logging.warning("Response is empty, nothing to send.")
            return
        # sentences = re.split(r'(?<=[.!?])\s+', response)
        sentences = re.split(r'(?<=[a-zA-Z][.!?])\s+', response)
        sentences = [s for s in sentences if s.strip()]
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                async with channel.typing():
                    await asyncio.sleep(2)
                await channel.send(sentence)
    except Exception as e:
        logging.error(f"Error sending response in parts: {e}")


async def get_response_from_openai(enable_ai, message, open_ai_model):
    if enable_ai:
        open_ai_service = OpenAIService(open_ai_model)
        response_from_ai = await open_ai_service.chat_with_gpt(message)
        if response_from_ai is not None:
            await send_response_in_parts(message.channel, response_from_ai)
            # await message.reply(response_from_ai)
            logging.info(f"Response from OpenAi with msg: {message.content.strip()}:{response_from_ai}")
        else:
            await message.reply(get_busy_response())
            logging.info(f"Message was too long. Skipping API call.")
    else:
        await message.reply(get_busy_response())
        logging.info(f"OpenAi API is turned off. Sending default message.")


async def return_response_for_attachment():
    try:
        with open('resources/responses_to_image.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        random_reaction = random.choice(data['reactions'])
        return random_reaction
    except FileNotFoundError:
        logging.error("Error: File 'responses_to_image.json' not found.")
        return None


async def get_reaction_for_random_message(self, message):
    magic_random = random.random()
    if magic_random < 0.1:
        response = await small_talk_with_gpt(message)
        logging.info(f"Response from OpenAi with chance:{magic_random}, with msg: {message.content.strip()}:{response}")
        await message.channel.send(content=response)
    else:
        logging.info(f"No response - random.random():{magic_random} decided :)")


class ReactionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        """Event handler called when a message is received."""
        enable_ai = os.getenv("enabled_ai", 'False').lower() in ('true', '1', 't')
        open_ai_model = os.getenv('open_ai_model')
        enabled_image_ai_analyze = os.getenv("enabled_image_ai_analyze", 'False').lower() in ('true', '1', 't')
        channel_for_bot = os.getenv('channel_id_for_talking')
        int_channel_for_bot = [int(channel.strip()) for channel in channel_for_bot]

        # Ignore messages from bot
        if message.author.bot:
            return

        # If the message has attachments
        if message.attachments:
            list_of_emojis = ['🎨']
            random_emoji = random.choice(list_of_emojis)
            await message.add_reaction(random_emoji)

            if enabled_image_ai_analyze is True:
                async with message.channel.typing():
                    await asyncio.sleep(4)
                response = analyze_image(message)
                await send_response_in_parts(message.channel, response)
                return
            else:
                response = await return_response_for_attachment()
                async with message.channel.typing():
                    await asyncio.sleep(3)
                await message.reply(response)
                return

        # If the message has content and its on bot channel - send it to Open API gateway
        if message.channel.id in int_channel_for_bot and not message.author.bot:
            await get_response_from_openai(enable_ai, message, open_ai_model)
            return

        # If the message has content and the bot is mentioned - send it to Open API gateway
        if self.bot.user.mentioned_in(message):
            await get_response_from_openai(enable_ai, message, open_ai_model)
            return

        # Add random reaction to message with low chance
        if not message.author.bot:
            await get_reaction_for_random_message(self, message)


async def setup(bot):
    await bot.add_cog(ReactionCog(bot))
