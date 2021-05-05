import datetime
import os
import re
from datetime import timedelta

from slack_sdk import WebClient  # type : ignore
from slack_sdk.errors import SlackApiError  # type : ignore

SLACK_TOKEN = os.environ['SLACK_TOKEN']
CHANNEL_ID = os.environ['CHANNEL_ID']
CLIENT = WebClient(token=SLACK_TOKEN)


def _get_posts_w_reaction(trace_back_days: int = 7):
    """実行日から過去days（default 7）日間のリアクション付き投稿を1投稿1辞書型のリストとして取得する"""

    oldest_day = datetime.datetime.now() - timedelta(days=trace_back_days)
    extracted_posts = []

    # 実行日からtrace_back_days日前までの投稿を取得
    result = CLIENT.conversations_history(
        channel=CHANNEL_ID, oldest=oldest_day.timestamp(), limit=100000
    )
    extracted_posts = result['messages']
    print(f'{len(extracted_posts)} messages found')

    # リアクションされた投稿のみを抽出
    extracted_posts_w_reaction = [
        {'ts': d['ts'], 'text': d['text'], 'reactions': d['reactions'], 'user': d['user']}
        for d in extracted_posts
        if 'reactions' in d.keys()
    ]

    # リアクションの数を投稿ごとに集計
    for post in extracted_posts_w_reaction:
        cnt = 0
        for reaction in post['reactions']:
            cnt += reaction['count']
        post['reactions'] = cnt

    return extracted_posts_w_reaction


def _extract_most_reacted_posts(trace_back_days: int = 7):
    """リアクション付き投稿リストのうちで最もリアクション数の多かった投稿を抽出する"""
    posts_w_reaction = _get_posts_w_reaction(trace_back_days)
    max_reaction_cnt = max([d.get('reactions') for d in posts_w_reaction])
    most_reacted_posts = [
        post for post in posts_w_reaction if post['reactions'] == max_reaction_cnt
    ]
    return most_reacted_posts


def _get_post_link(ts):
    """ts(timestamp)の一致する投稿のリンクを取得する"""
    chat = CLIENT.chat_getPermalink(token=SLACK_TOKEN, channel=CHANNEL_ID, message_ts=ts)
    return chat


def _get_homember_list(message: str):
    """投稿内でメンションされているユーザのリストを取得"""
    m = re.compile(r'<@.*>')
    text_list = re.split(r'[\xa0| |,|;]', message)

    homember_list = [m.match(name).group() for name in text_list if m.match(name) is not None]
    return homember_list


def _post_start_message():
    """レポート最初のコメントを投稿する"""
    CLIENT.chat_postMessage(
        channel=CHANNEL_ID,
        text='先週もようがんばったな:kissing_cat:ノビルくんの弟からウィークリーレポートのお知らせやで～\n'
        + '先週みんなが送ってくれた「褒め言葉」の中で、一番多くのスタンプを集めたウィークリーベスト褒めエピソードはこれや！:cv2_res_pect:\n',
    )


def _post_award_message(post: dict):
    """最もリアクションが多かった投稿をしたユーザ、メンションされたユーザ、投稿へのリンクを投稿する"""
    chat = _get_post_link(post['ts'])
    homember_list = _get_homember_list(post['text'])

    CLIENT.chat_postMessage(
        channel=CHANNEL_ID,
        text=f'最もリアクションの多かった褒めをした人：<@{post["user"]}>\n'
        + f'最も褒められたメンバー：{", ".join(homember_list)}\n'
        + f'{chat["permalink"]}\n',
    )

    CLIENT.chat_postMessage(channel=CHANNEL_ID, text=f'{chat["permalink"]}\n')


def _post_end_message():
    """レポートを締めるコメントを投稿する"""
    CLIENT.chat_postMessage(channel=CHANNEL_ID, text='今週もぎょうさん褒めに褒めまくって、伸ばし合っていこか！')


def post_award_best_home_weekly():
    """実行日から過去7日間の投稿を取得し最もリアクションの多かった投稿を表彰する"""
    try:
        most_reacted_posts = _extract_most_reacted_posts(trace_back_days=7)
        _post_start_message()

        for post in most_reacted_posts:
            _post_award_message(post)

        _post_end_message()

    except SlackApiError as e:
        print('Error creating conversation: {}'.format(e))


if __name__ == '__main__':
    post_award_best_home_weekly()