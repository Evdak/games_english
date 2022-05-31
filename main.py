import asyncio

from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.session import defer_call, info as session_info, run_async, run_js

from config import ADMIN_NAME, ADMIN_PASSWORD, GAMES

chat_msgs = []
online_users = set()
is_started = False

MAX_MESSAGES_COUNT = 100

games = [None]


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
    # msg_box.append(put_markdown(f'📢 `{name}` присоединился к игре!'))
    refresh_task = run_async(refresh_lobbies(name, msg_box))

    if role == 'Ведущий':
        put_buttons(['Start'], onclick=start_game)
    try:
        game = game if game else None
    except:
        game = None
    check_is_started_task = run_async(check_is_started(msg_box, name, game))
    # while True:
    #     await asyncio.sleep(1)
    #     if check_is_started_task.closed():
    #         if games[0] == 'ЧБД':
    #             print('da')
    #             run_async(WHN(msg_box, name))
    #         break

    # while not check_is_started_task.closed():
    #     pass

    # data = await input_group("💭 Новое сообщение", [
    #     input(placeholder="Текст сообщения ...", name="msg"),
    #     actions(name="cmd", buttons=["Отправить", {
    #             'label': "Выйти из чата", 'type': 'cancel'}])
    # ], validate=lambda m: ('msg', "Введите текст сообщения!") if m["cmd"] == "Отправить" and not m['msg'] else None)

    # if data is None:
    #     break

    # msg_box.append(put_markdown(f"`{name}`: {data['msg']}"))
    # chat_msgs.append((name, data['msg']))

    # refresh_task.close()
    # chat_msgs.append(('📢', f'Игра началась!'))


async def refresh_lobbies(name, msg_box):
    global chat_msgs
    last_idx = 0

    while True:
        await asyncio.sleep(1)

        for m in chat_msgs[last_idx:]:
            if m[0] != name:  # if not a message from current user
                msg_box.append(put_markdown(f"`{m[0]}`: {m[1]}"))

        # remove expired
        if len(chat_msgs) > MAX_MESSAGES_COUNT:
            chat_msgs = chat_msgs[len(chat_msgs) // 2:]

        last_idx = len(chat_msgs)


async def check_is_started(msg_box, name, game=None):
    global chat_msgs, is_started

    while True:
        await asyncio.sleep(1)

        if is_started:
            msg_box.append(put_markdown(f"Игра началась!"))
            if games[0] == 'ЧБД':
                print('da')
                run_async(WHN(msg_box, name))
            break


async def WHN(msg_box, name):
    while True:
        data = await input_group("💭 Новое сообщение", [
            input(placeholder="Текст сообщения ...", name="msg"),
            actions(name="cmd", buttons=["Отправить", {
                'label': "Выйти из чата", 'type': 'cancel'}])
        ], validate=lambda m: ('msg', "Введите текст сообщения!") if m["cmd"] == "Отправить" and not m['msg'] else None)

        if data is None:
            break

        msg_box.append(put_markdown(f"`{name}`: {data['msg']}"))
        chat_msgs.append((name, data['msg']))

        if name == ADMIN_NAME and data['msg'].lower() == 'start':
            for i in range(6):
                chat_msgs.append(
                    ('Осталось времени', f"{(180-(i*30))/60} мин."))
                await asyncio.sleep(30)

if __name__ == "__main__":
    start_server(main, debug=True, port=8080, cdn=False)
