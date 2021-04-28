import csv
import os
import random
import re

from slackbot.bot import listen_to

GCP_TOKEN = os.getenv('GCP_TOKEN')
OWM_TOKEN = os.getenv('OWM_TOKEN')


def add_bot_message_subtype(message):
    """ ボットのメッセージだとわかるように判別をつける """
    message.body['subtype'] = 'bot_message'
    return message


def validation_bot_subtype(message):
    """ ボットのメッセージか判定する """
    if 'subtype' in message.body and message.body['subtype'] == 'bot_message':
        return True
    return False


def create_random_element_list(path, user_num):
    """メッセージの元ファイルを読み出して、ランダムなユーザー数分のテキストリストを生成する"""
    with open(path, newline='') as csvfile:
        text_list = [s[0] for s in csv.reader(csvfile)]

    random.shuffle(text_list)

    # 倍数分だけテキストリストの要素を増やす
    scale_num = user_num / len(text_list)
    if scale_num > 1:
        for i in range(int(scale_num)):
            text_list += random.sample(text_list, len(text_list))

    return text_list[:user_num]


def extract_users(message):
    """メッセージからメンションするためのユーザーのリストを抽出する"""
    m = re.compile(r'<@.*>')

    # コメント内のメンションのsplit_stringとして現状以下のパターンが大多数を占める
    #   - ' '（半角スペース）, '\xa0'（ノーブレークスペース）
    split_character = '[\xa0| |,|;]'
    splitted_message = re.split(split_character, message)
    print(f'splitted_message:{splitted_message}')

    # TODO:メンションされたユーザーが重複する場合に返答は1回にするかを検討する
    user_list = []
    for words in splitted_message:
        mo = m.match(words)
        if mo is not None:
            user_list.append(mo.group())

    return user_list


@listen_to(r'.*@.*')
def homeru_post(message):
    """
    メンション付きの投稿がされた場合に、メッセージ内のメンションされた人をほめる機能
    """

    # TODO: validationする

    text = message.body['text']
    print(f'ポストされたメッセージ: {text}')
    user_list = extract_users(text)
    homeru_text_list = create_random_element_list(
        'resources/homeru_message_text.csv', len(user_list)
    )
    homeru_stamp_list = create_random_element_list(
        'resources/homeru_message_stamp.csv', len(user_list)
    )

    print(f'user_num: {len(user_list)}')
    for user, text, stamp in zip(user_list, homeru_text_list, homeru_stamp_list):
        # スレッド内のユーザーの返信に、スレッドの外で反応すると会話の流れがわかりにくいため
        if 'thread_ts' in message.body:
            message.send(f'{user} {text}{stamp}', thread_ts=message.body['thread_ts'])
        else:
            message.send(f'{user} {text}{stamp}')
