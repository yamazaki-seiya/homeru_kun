# pyright: reportPrivateImportUsage = false
import datetime
import inspect
import os
import re
from datetime import timedelta
from typing import Dict, List

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

SLACK_TOKEN = os.environ['SLACK_TOKEN']
CHANNEL_ID = os.environ['CHANNEL_ID']
CLIENT = WebClient(token=SLACK_TOKEN)
_TRACE_BACK_DAYS = 7
_EXTRACT_USER_PATTERN = re.compile(r'(<@\w*>)|(<\!subteam\^.*>)')


def post_award_best_home_weekly() -> None:
    """実行日から過去7日間の投稿を取得し最もリアクションの多かった投稿を表彰する"""
    try:
        most_reacted_posts = _extract_most_reacted_posts(_TRACE_BACK_DAYS)
        _post_start_message()

        for post in most_reacted_posts:
            _post_award_message(post)

        _post_end_message()

    except SlackApiError as e:
        print('Error creating conversation: {}'.format(e))


def _extract_most_reacted_posts(trace_back_days: int) -> List[Dict]:
    """リアクション付き投稿リストのうちで最もリアクション数の多かった投稿を抽出する"""
    posts_with_reaction = _get_posts_with_reaction(trace_back_days)
    max_reaction_cnt = max([post['reactions_cnt'] for post in posts_with_reaction])
    most_reacted_posts = [
        post for post in posts_with_reaction if post['reactions_cnt'] == max_reaction_cnt
    ]
    return most_reacted_posts


def _get_posts_with_reaction(trace_back_days: int) -> List[Dict]:
    """指定された日数遡った期間のリアクション付き投稿（botからの投稿は除く）を1投稿1辞書型のリストとして取得する"""

    oldest_day = datetime.datetime.now() - timedelta(days=trace_back_days)
    # extracted_posts = []

    # 実行日からtrace_back_days日前までの投稿を取得
    result = CLIENT.conversations_history(
        channel=CHANNEL_ID, oldest=str(oldest_day.timestamp()), limit=100000
    )
    extracted_posts: list = result['messages']  # type: ignore
    print(f'{len(extracted_posts)} messages found')

    # リアクションされた投稿のみを抽出
    extracted_posts_with_reaction = [
        {
            'ts': post['ts'],
            'text': post['text'],
            'reactions_cnt': sum(reaction['count'] for reaction in post['reactions']),
            'user': post['user'],
        }
        for post in extracted_posts
        if ('bot_id' not in post.keys())
        & ('reactions' in post.keys())  # botからの投稿とreactionのない投稿を除外する
    ]
    print(f'extracted_posts_with_reaction:\n{extracted_posts_with_reaction}')

    return extracted_posts_with_reaction


def _post_start_message() -> None:
    """レポート最初のコメントを投稿する"""
    message = '''
        やっほー:blossom:ノビルくんの妹やで:ribbon:
        うちからウィークリーレポートをおしらせするで:laughing:
        先週もみんなようがんばってくれたみたいでほんま嬉しいわ～:sunflower:
        みんなが送ってくれた「褒め言葉」の中で、一番多くのスタンプを集めたウィークリーベスト褒めエピソードはこれや！:cv2_res_pect:
    '''
    _post_message(message)


def _post_award_message(post: Dict) -> None:
    """最もリアクションが多かった投稿をしたユーザ、メンションされたユーザ、投稿へのリンクを投稿する"""
    chat_link = _get_post_link(post['ts'])
    homember_list = _get_homember_list(post['text'])
    message = f'''
        最もリアクションの多かった褒めをした人：<@{post['user']}>
        最も褒められたメンバー：{', '.join(homember_list)}
        {chat_link}
    '''
    _post_message(message)


def _get_post_link(ts: str) -> str:
    """timestampの一致する投稿のリンクを取得する"""
    chat = CLIENT.chat_getPermalink(token=SLACK_TOKEN, channel=CHANNEL_ID, message_ts=ts)
    return chat['permalink']  # type: ignore


def _get_homember_list(message: str) -> List[str]:
    """投稿内でメンションされているユーザのリストを取得"""
    homember_list = re.findall(_EXTRACT_USER_PATTERN, message)
    print(homember_list)
    return homember_list


def _post_end_message() -> None:
    """レポートを締めるコメントを投稿する"""
    message = '今週もぎょうさん褒めに褒めまくって、伸ばし合っていこか！'
    _post_message(message)


def _post_message(message: str) -> None:
    """
    CHANNEL_IDのチャンネルにメッセージを送信する

    Args:
        message: 送信メッセージ
        メッセージの前後はtrimされる
        その他空行やタブ文字などがあると変換されるため注意
        https://docs.python.org/ja/3/library/inspect.html#inspect.cleandoc
    """
    CLIENT.chat_postMessage(channel=CHANNEL_ID, text=inspect.cleandoc(message))


if __name__ == '__main__':
    post_award_best_home_weekly()
