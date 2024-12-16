import json
import logging
import os
import random
from __main__ import bot

from dotenv import load_dotenv


async def send_funny_fallback_msg(ctx):
    load_dotenv("../.env")
    helper_user = bot.get_user(int(os.getenv('target_user_id')))
    await ctx.send(
        f"{ctx.author.mention}, wybacz ale coś sie schrzaniło :/ {helper_user.mention} przyłaź tu i mnie napraw!")


def remove_polish_chars(text):
    mapping = {
        'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
        'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z'
    }
    return ''.join(mapping.get(char, char) for char in text)


def get_busy_response():
    responses = [
        "Aaaa, co tam się dzieje? Czekaj, bo mam teraz pełne ręce roboty z tymi 'Sztauwajerami'. Zaraz wracam, obiecuję!",
        "Ho ho ho, nie ma czasu na wygłupy! 💼 Chwila, bo muszę sprawdzić, gdzie się zapodziała moja kawa. Wracam zaraz!",
        "Co? Znowu coś chcesz? To się dobrze zastanów, bo teraz to mam pełno roboty! Będę za chwilę!",
        "Ugh, no nie! 😤 Już mi się tu rypie! Daj mi chwilę, bo na pewno znajdę chwilę na przerwę od tego chaosu.",
        "Jeszcze jedna prośba, a od razu wyskoczę na Spodek! 😏 Zajmę się tym, ale to za chwilę, bo mam teraz coś do ogarnięcia."
    ]
    return random.choice(responses)


def load_resources_from_file(file_name):
    if file_name:
        current_path = os.path.abspath(__file__)
        current_directory = os.path.dirname(current_path)
        file_path = os.path.join(current_directory, '..', 'resources', file_name)
        if file_path.endswith('.json'):
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    config_data = json.load(file)
                    return config_data
            except json.JSONDecodeError as e:
                logging.error(f'Error during open json file {file_name}: {e}')
                return
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    config_data = file.read()
                    return config_data.splitlines()
            except Exception as e:
                logging.error(f'Error during open normal file {file_name}: {e}')
            return
