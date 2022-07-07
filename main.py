import argparse
import asyncio

import random
import json

from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.session import defer_call, info as session_info, run_async, run_js

from config import ADMIN_NAME, ADMIN_PASSWORD, GAMES, GAME_CROCODILE_WORDS, GAME_WHO_WORDS


def start(event=None):
    global chat_msgs, online_users, is_started, WHN_dict, CROCODILE_dict, WHO_dict, MAX_MESSAGES_COUNT, games

    chat_msgs = []
    online_users = set()
    is_started = False

    WHN_dict = {
        'is_started': False,
        'current_state': None,
        'current_user': None,
        'task': None,
        'score': {},
        'scored': 0
    }

    random.shuffle(GAME_CROCODILE_WORDS)
    random.shuffle(GAME_WHO_WORDS)

    CROCODILE_dict = {
        'words': GAME_CROCODILE_WORDS.copy(),
        'task': None,
        'current_state': None,
        'current_user': None,
        'current_word': None,
        'users': None,
        'users_showed': [],
        'answered': 0
    }

    WHO_dict = {
        'words': GAME_WHO_WORDS.copy(),
        'task': None,
        'current_state': None,
        'current_user': None,
        'current_word': None,
        'users': None,
        'users_showed': [],
        'answered': 0
    }

    MAX_MESSAGES_COUNT = 100

    games = [None]

    if event:
        run_js('document.location.reload();')


start()


def start_game(sender, **args):
    global is_started
    is_started = True


async def main():
    global chat_msgs
    role: str = await radio("Роль:", required=True,  options=['Игрок', 'Ведущий'])

    if role == 'Ведущий':
        name = ADMIN_NAME
        password: str = await input(
            "Пароль:", required=True, type=PASSWORD, validate=lambda p: "Неверный пароль!" if p != ADMIN_PASSWORD else None)
        game: str = await radio("Игра:", options=GAMES, required=True)
        games[0] = game
        chat_msgs.append(('📢', f'GAME: {game}'))
    else:
        name: str = await input("Имя:", type=TEXT, required=True,
                                validate=lambda n: "Такой ник уже используется!" if (n, role) in online_users else None)
    online_users.add((name, role))

    msg_box = output()
    put_scrollable(msg_box, height=300, keep_bottom=True)

    chat_msgs.append(('📢', f'`{name}` присоединился к игре!'))
    refresh_task = run_async(refresh_lobbies(name, msg_box))

    if role == 'Ведущий':
        put_buttons(['Start'], onclick=start_game)
        put_buttons(['End'], onclick=start)
    try:
        game = game if game else None
    except:
        game = None
    check_is_started_task = run_async(check_is_started(msg_box, name, game))


async def refresh_lobbies(name, msg_box):
    global chat_msgs
    last_idx = 0

    while True:
        await asyncio.sleep(1)

        for m in chat_msgs[last_idx:]:
            if m[0] != name:
                msg_box.append(put_markdown(f"`{m[0]}`: {m[1]}"))

        if len(chat_msgs) > MAX_MESSAGES_COUNT:
            chat_msgs = chat_msgs[len(chat_msgs) // 2:]

        last_idx = len(chat_msgs)


async def check_is_started(msg_box, name, game=None):
    global chat_msgs, is_started

    while True:
        await asyncio.sleep(1)

        if is_started:
            msg_box.append(put_markdown(f"`📢`: Игра началась!"))
            if games[0] == 'ЧБД':
                msg_box.append(put_markdown(f"""`📢`: ПРАВИЛА ИГРЫ:
                Сейчас ведущий пришлет начало истории, затем запустится таймер (3 минуты).
                В это время вы можете начать записывать ваш вариант продолжения истории, затем когда наступит ваша очередь, запустится таймер на 5 минут и вы начнете отвечать."""))
                WHN_dict['is_started'] = True
                WHN_dict['task'] = run_async(WHN(msg_box, name))
                run_async(WHN_end(msg_box, name))

            if games[0] == 'Крокодил':
                msg_box.append(put_markdown(f"""`📢`: ПРАВИЛА ИГРЫ:
                Сейчас по очереди будут высвечиваться карточки со словами.
                Вы его описываете, а другие угадывают."""))

                run_async(crocodile(msg_box, name))

            if games[0] == 'Кто я? Что я?':
                msg_box.append(put_markdown(f"""`📢`: ПРАВИЛА ИГРЫ:
                ......"""))

                run_async(who(msg_box, name))

            break


async def taimer(time: int):
    if True:
        for i in range(time):
            if WHN_dict['current_state'] != 'skip':
                if i % 30 == 0:
                    chat_msgs.append(
                        ('Осталось времени', f"{(time-(i))/60} мин."))
                await asyncio.sleep(1)
            else:
                break


async def crocodile(msg_box, name):
    global CROCODILE_dict
    online_users_copy = list(online_users.copy())
    online_users_copy = [
        el for el in online_users_copy if el[1] != 'Ведущий']

    if CROCODILE_dict['users'] is None:
        CROCODILE_dict['users'] = online_users_copy.copy()

    style(put_scope('out'),
          """display:flex;
            justify-content:stretch;
            font-weight: 400;
            font-size: larger;
            flex-direction: column;
          """)

    while True:
        if CROCODILE_dict['answered'] != (len(online_users) - 1):
            if CROCODILE_dict['current_user'] is None:

                CROCODILE_dict['current_user'] = CROCODILE_dict['users'].pop(0)[
                    0]
                CROCODILE_dict['current_word'] = CROCODILE_dict['words'].pop(
                    0)

            else:
                pass

            if CROCODILE_dict['current_state'] != 'guessing' or \
                    len(CROCODILE_dict['users_showed']) != len(online_users):

                if name not in CROCODILE_dict['users_showed']:

                    if name == CROCODILE_dict['current_user']:
                        with use_scope('out'):
                            clear('out')
                            put_success(
                                f"""Слово - {CROCODILE_dict['current_word']} """)
                        CROCODILE_dict['current_state'] = 'guessing'

                        def make_guessed():
                            CROCODILE_dict['current_state'] = 'guessed'
                            CROCODILE_dict['answered'] += 1

                            CROCODILE_dict['current_user'] = None
                            CROCODILE_dict['current_word'] = None

                            CROCODILE_dict['users_showed'].clear()

                            return
                        with use_scope('out'):
                            style(put_button('Угадано', onclick=make_guessed),
                                  """
                                width: -webkit-fill-available;
                                font-size: larger;
                            """
                                  )

                    elif name == ADMIN_NAME:
                        with use_scope('out'):
                            clear('out')
                            put_success(
                                f"""Отвечает - {CROCODILE_dict['current_user']}\nСлово - {CROCODILE_dict['current_word']} """)

                    else:
                        with use_scope('out'):
                            clear('out')
                            put_success(
                                f"""Отвечает - {CROCODILE_dict['current_user']}""")

                    CROCODILE_dict['users_showed'].append(name)

                await asyncio.sleep(1)
            await asyncio.sleep(1)
        else:
            with use_scope('out'):
                clear('out')
            msg_box.append(put_markdown(f"`📢`: Игра окончена"))
            break


async def who(msg_box, name):
    global WHO_dict
    online_users_copy = list(online_users.copy())
    online_users_copy = [
        el for el in online_users_copy if el[1] != 'Ведущий']

    if WHO_dict['users'] is None:
        WHO_dict['users'] = online_users_copy.copy()

    style(put_scope('out'),
          """display:flex;
            justify-content:stretch;
            font-weight: 400;
            font-size: larger;
            flex-direction: column;
          """)

    while True:
        if WHO_dict['answered'] != (len(online_users) - 1):
            if WHO_dict['current_user'] is None:

                WHO_dict['current_user'] = WHO_dict['users'].pop(0)[
                    0]
                WHO_dict['current_word'] = WHO_dict['words'].pop(
                    0)

            else:
                pass

            if WHO_dict['current_state'] != 'guessing' or len(WHO_dict['users_showed']) != len(online_users):

                if name not in WHO_dict['users_showed']:

                    if name == WHO_dict['current_user']:

                        with use_scope('out'):
                            clear('out')
                            put_success(
                                f"""Ваш ход""")
                        WHO_dict['current_state'] = 'guessing'

                        def make_guessed():
                            WHO_dict['current_state'] = 'guessed'
                            WHO_dict['answered'] += 1

                            WHO_dict['current_user'] = None
                            WHO_dict['current_word'] = None

                            WHO_dict['users_showed'].clear()

                            return
                        with use_scope('out'):
                            style(put_button('Угадано', onclick=make_guessed),
                                  """
                                width: -webkit-fill-available;
                                font-size: larger;
                            """
                                  )

                    elif name == ADMIN_NAME:
                        with use_scope('out'):
                            clear('out')
                            put_success(
                                f"""Отвечает - {WHO_dict['current_user']}\nСлово - {WHO_dict['current_word']} """)

                    else:
                        with use_scope('out'):
                            clear('out')
                            put_success(
                                f"""Отвечает - {WHO_dict['current_user']}\nСлово - {WHO_dict['current_word']} """)

                    WHO_dict['users_showed'].append(name)

                await asyncio.sleep(1)
            await asyncio.sleep(1)
        else:
            with use_scope('out'):
                clear('out')
            msg_box.append(put_markdown(f"`📢`: Игра окончена"))
            break


async def WHN_end(msg_box, name):
    global taimer_tasks, WHN_dict
    while WHN_dict['current_state'] != 'score':
        await asyncio.sleep(1)

    online_users_copy = list(online_users.copy())
    online_users_copy = [
        el for el in online_users_copy if el[1] != 'Ведущий']
    inp = []
    for el in online_users_copy:
        inp.append(
            select(f'Вариант игрока {el[0]}', name=f'{el[0]}', options=[i for i in range(1, 6)]))
        WHN_dict['score'][el[0]] = 0
    score: dict = await input_group('Голосование', inp)

    for key, value in score.items():
        WHN_dict['score'][key] += value
        WHN_dict['scored'] += 1
        print(WHN_dict['score'])

    while WHN_dict['scored'] != (len(online_users_copy) * (len(online_users_copy)+1)):
        print(WHN_dict['scored'], len(online_users_copy))
        await asyncio.sleep(1)

    if WHN_dict['scored'] == (len(online_users_copy) * (len(online_users_copy)+1)):
        await asyncio.sleep(3)
        msg_box.append(put_markdown(f"`📢`: Игра окончена"))
        msg_box.append(put_markdown(f'`ВНИМАНИЕ`: РЕЗУЛЬТАТЫ ИГРЫ'))
        # chat_msgs.append(
        #     (f'ВНИМАНИЕ', f"РЕЗУЛЬТАТЫ ИГРЫ"))
        global max_score, winners
        max_score = 0
        winners = []
        for key, value in WHN_dict['score'].items():
            msg_box.append(put_markdown(f'`{key}`: {value} баллов'))
            # chat_msgs.append(
            #     (f'{key}', f"{value} баллов"))
            if value > max_score:
                winners = [key]
                max_score = value
            elif value >= max_score:
                winners.append(key)
                max_score = value
        msg_box.append(put_markdown(f"`ПОБЕДИТЕЛЬ`: {','.join(winners)}"))
        # chat_msgs.append(
        #     (f'ПОБЕДИТЕЛИ', f"{','.join(winners)}"))


async def WHN(msg_box, name):
    global taimer_tasks
    while True:
        if WHN_dict['current_state'] == 'score':
            break
        data = await input_group("💭 Новое сообщение", [
            input(placeholder="Текст сообщения ...", name="msg"),
            actions(name="cmd", buttons=[
                "Отправить", "Закончить ход", {'label': "Выйти из чата", 'type': 'cancel'}])
        ], validate=lambda m: ('msg', "Введите текст сообщения!") if m["cmd"] == "Отправить" and not m['msg'] else None)

        if data['cmd'] == "Закончить ход":
            if name == WHN_dict['current_user']:
                WHN_dict['current_state'] = 'skip'
            continue

        if data is None:
            break

        msg_box.append(put_markdown(f"`{name}`: {data['msg']}"))
        chat_msgs.append((name, data['msg']))

        if name == ADMIN_NAME and data['msg'].lower() == 'start':
            WHN_dict['current_state'] = 'waiting'
            if True:
                await taimer(5)

            online_users_copy = list(online_users.copy())
            online_users_copy = [
                el for el in online_users_copy if el[1] != 'Ведущий']

            while online_users_copy != []:
                WHN_dict['current_user'] = online_users_copy.pop(0)[0]
                WHN_dict['current_state'] = 'user_is_answering'
                chat_msgs.append(
                    ('Время вышло', f"Очередь - {WHN_dict['current_user']}"))

                if True:
                    await taimer(180)

            chat_msgs.append(
                ('Время вышло', f"Очередь - {ADMIN_NAME}"))
            WHN_dict['current_user'] = ADMIN_NAME
            WHN_dict['current_state'] = 'admin_is_answering'
            data = await input_group("💭 Новое сообщение", [
                input(placeholder="Текст сообщения ...", name="msg"),
                actions(name="cmd", buttons=[
                    "Отправить", "Закончить ход", {'label': "Выйти из чата", 'type': 'cancel'}])
            ], validate=lambda m: ('msg', "Введите текст сообщения!") if m["cmd"] == "Отправить" and not m['msg'] else None)

        if name == ADMIN_NAME and WHN_dict['current_state'] == 'admin_is_answering':
            WHN_dict['current_user'] = None
            WHN_dict['current_state'] = 'score'


if __name__ == "__main__":
    # start_server(main, debug=False, port=8080, cdn=False)
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=8080)
    args = parser.parse_args()

    start_server(main, port=args.port)
