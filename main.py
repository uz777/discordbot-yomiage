import os
import subprocess
import sys
import traceback
import yaml
import re
import discord
from discord.ext import commands
import logging.config


def print_logo():
    """ ロゴ表示

    :return: None
    """
    print("""
██╗   ██╗ ██████╗ ███╗   ███╗██╗ █████╗  ██████╗ ███████╗
╚██╗ ██╔╝██╔═══██╗████╗ ████║██║██╔══██╗██╔════╝ ██╔════╝
 ╚████╔╝ ██║   ██║██╔████╔██║██║███████║██║  ███╗█████╗  
  ╚██╔╝  ██║   ██║██║╚██╔╝██║██║██╔══██║██║   ██║██╔══╝  
   ██║   ╚██████╔╝██║ ╚═╝ ██║██║██║  ██║╚██████╔╝███████╗
   ╚═╝    ╚═════╝ ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
    """)


"""
VERSION
    アプリケーションバージョン
"""
VERSION = '0.1.0'

"""
VOICE_TYPES
    声質略記名とファイル名のマップ
"""
VOICE_TYPES = {
    'n': 'nitech_jp_atr503_m001.htsvoice',
    'ma': 'mei_angry.htsvoice',
    'mb': 'mei_bashful.htsvoice',
    'mh': 'mei_happy.htsvoice',
    'mn': 'mei_normal.htsvoice',
    'ms': 'mei_sad.htsvoice',
    'ta': 'takumi_angry.htsvoice',
    'th': 'takumi_happy.htsvoice',
    'tn': 'takumi_normal.htsvoice',
    'ts': 'takumi_sad.htsvoice',
}

"""
logger
    アプリケーションロガー
"""
logger = logging.getLogger('yomiage')

"""
グローバル初期化処理
    アプリケーションの初期化前に必要となる処理を行う
    設定ファイルの読み込み
        引数で指定があればそのパスを設定ファイルとして読み込む
        指定が無い場合は、config.ymlを設定ファイルとして読み込む
        設定ファイルが存在しない場合はエラーとする。
    ロガー初期化
        読み込んだ設定ファイルでロガーを初期化する
"""
if 1 < len(sys.argv):
    config_path = os.path.abspath(sys.argv[1])
else:
    config_path = os.path.abspath('config.yml')

if not os.path.isfile(config_path):
    logger.error(f'Config yaml file ({config_path}) does not exist.')
    sys.exit(1)
else:
    with open(config_path, 'r', encoding="utf-8") as yml:
        config = yaml.safe_load(yml)
        logging.config.dictConfig(config)


def initialize():
    """ 初期化処理
    ボットの実行前に必要な初期化処理を行う

    :return: None
    """
    # バイナリディレクトリにパスを通す(コマンド実行に必要)
    os.environ["PATH"] += os.pathsep + os.path.join(root_path(), 'resource')

    # opus(コーデック)読み込み
    if not discord.opus.is_loaded():
        discord.opus.load_opus(resource_path('libopus.dll'))

    # 声質設定が正常値でなければ、デフォルトへ置き換え
    vt = config['app']['voice_type']
    if vt not in VOICE_TYPES:
        logger.warning(f'Voice Type ({vt}) does not exist. Replaced to (n).')
        config['app']['voice_type'] = 'n'


def root_path():
    """ ルートパス取得
    スクリプト実行パス(.exe実行の場合は展開されたディレクトリのパス)を取得する

    :return: ルートパス
    """
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.abspath('.')


def resource_path(relative_path):
    """ パス変換
    resouceディレクトリからの相対パスを、
    絶対パスへ変換して返却する

    :param relative_path: resouceディレクトリからの相対パス
    :return: 絶対パス
    """
    return os.path.join(root_path(), 'resource', relative_path)


def remove_multi_line(text):
    """ 2行目除去
    2行目以降の文字列を除去して返却する

    :param text: 変換前文字列
    :return: 変換後文字列
    """
    return text.split('\n')[0]


def remove_custom_emoji(text):
    """ 絵文字削除
    絵文字を削除して返却する

    :param text: 変換前文字列
    :return: 変換後文字列
    """
    pattern = r'<:[a-zA-Z0-9_]+:[0-9]+>'
    return re.sub(pattern, '', text)


def remove_mention(text):
    """ メンション削除
    メンションを削除して返却する
    
    :param text: 変換前文字列
    :return: 変換後文字列
    """
    pattern = r'@[0-9]{18}'
    return re.sub(pattern, '', text)


def url_abb(text):
    """ url置換
    URLにパターンマッチする箇所を「ゆーあーるえる」へ置換して返却する

    :param text: 変換前文字列
    :return: 変換後文字列
    """
    pattern = "https?://[\w/:%#\$&\?\(\)~\.=\+\-]+"
    return re.sub(pattern, 'ゆーあーるえる', text)


def big_num_abb(text):
    """ 長い数字の除去
    5桁以上の数字を「たくさん」に置換して返却する

    :param text: 変換前文字列
    :return: 変換後文字列
    """
    pattern = "[0-9]{5,}"
    return re.sub(pattern, 'たくさん', text)


def make_speakable(text):
    """ 文字列可読化
    文字列を読み上げ可能な状態へ加工して返却する

    :param text: 変換前文字列
    :return: 変換後文字列
    """
    text = remove_multi_line(text)
    text = remove_mention(text)
    text = url_abb(text)
    text = big_num_abb(text)
    return remove_custom_emoji(text)


def create_wav(input_text):
    """ 読み上げ音声ファイル生成
    open_jtalkを使用し、文字列から読み上げ音声ファイルを生成する

    :param input_text: 生成対象文字列
    :return: None
    """
    input_file = resource_path('input.txt')

    with open(input_file, 'w', encoding='shift_jis') as file:
        file.write(input_text)

    command = 'open_jtalk.exe -x {x} -m {m} -r {r} -ow {ow} {input_file}'

    # 辞書のPath
    x = resource_path('dic')

    # ボイスファイルのPath
    vt = config['app']['voice_type']
    m = resource_path(f'htsvoice\\{VOICE_TYPES[vt]}')

    # 発声のスピード
    r = '1.0'

    # 出力ファイル名　and　Path
    ow = resource_path('output.wav')

    args = {'x': x, 'm': m, 'r': r, 'ow': ow, 'input_file': input_file}

    cmd = command.format(**args)
    logger.debug(f'Execute open_jtalk command ({cmd})')

    subprocess.run(cmd)
    return True


if __name__ == '__main__':

    initialize()
    client = commands.Bot(command_prefix=config['app']['cmd_prefix'])


    @client.event
    async def on_ready():
        """ 待機開始
        コマンドを受付可能となった際に実行される
        ロゴや設定状態を表示する

        :return: None
        """
        print_logo()
        logger.info('==========================================================')
        logger.info(f'version: {VERSION}')
        logger.info(f'cmd_prefix: {config["app"]["cmd_prefix"]}')
        logger.info(f'voice_type: {config["app"]["voice_type"]} ({VOICE_TYPES[config["app"]["voice_type"]]})')
        logger.info(f'bot user: {client.user.id}/{client.user.name}')
        logger.info('==========================================================')


    @client.command()
    async def join(ctx):
        """ 接続
        ユーザーが参加しているVCへbotを参加させる

        :param ctx: Context
        :return: None
        """
        logger.info(f'Received [join] cmd from user ({ctx.author.id}/{ctx.author.name}).')
        bot_vc = None
        bot_vc_cl = ctx.voice_client
        if bot_vc_cl:
            bot_vc = bot_vc_cl.channel
        user_vc = ctx.author.voice.channel
        if user_vc:
            if bot_vc:
                if bot_vc.id == user_vc.id:
                    logger.warning(f'Already in users voice channel ({user_vc.id}/{user_vc.name}).')
                    return
                else:
                    logger.info(f'Disconnecting from voice channel ({bot_vc.id}/{bot_vc.name}).')
                    await bot_vc_cl.disconnect()
            logger.info(f'Connecting users voice channel ({user_vc.id}/{user_vc.name})')
            await user_vc.connect()
        else:
            logger.warning('User is not in voice channel.')


    @client.command()
    async def bye(ctx):
        """ 切断
        botが接続中のVCから切断する

        :param ctx: Context
        :return: None
        """
        logger.info(f'Received [bye] cmd from user ({ctx.author.id}/{ctx.author.name}).')
        bot_vc_cl = ctx.voice_client
        if bot_vc_cl:
            bot_vc = bot_vc_cl.channel
            if bot_vc:
                logger.info(f'Disconnecting from voice channel ({bot_vc.id}/{bot_vc.name}).')
                await ctx.voice_client.disconnect()
        else:
            logger.warning(f'Not in voice channel.')


    @client.event
    async def on_message(message):
        """ メッセージ受信
        テキストチャンネルでメッセージが投稿された際に呼び出される
        コマンド以外の文字列かつ読み上げ対象であれば、音声を再生する

        :param message: メッセージ
        :return: None
        """
        bot_vc_cl = message.guild.voice_client
        if message.content.startswith(config['app']['cmd_prefix']):
            pass
        else:
            if bot_vc_cl:
                logger.info(f'Received message from user ({message.author.id}/{message.author.name}).')
                logger.debug(f'Raw message content ({message.content})')
                text_for_speak = make_speakable(message.content)
                logger.debug(f'Converted message content ({text_for_speak})')
                create_wav(text_for_speak)
                source = discord.FFmpegPCMAudio(resource_path('output.wav'))
                bot_vc_cl.play(source)
            else:
                pass
        await client.process_commands(message)


    @client.event
    async def on_error(event, *args, **kwargs):
        """ エラーハンドラ
        コマンド以外でエラーが発生した場合のハンドラ

        :param event: event
        :param args: args
        :param kwargs: kwargs
        :return: None
        """
        logger.error(event)
        logger.error(traceback.format_exc())


    @client.event
    async def on_command_error(ctx, error):
        """ コマンドエラーハンドラ
        コマンド内でエラーが発生した場合のハンドラ

        :param ctx: Context
        :param error: error
        :return: None
        """
        logger.error(error)
        if isinstance(error, commands.CommandInvokeError):
            orig_error = getattr(error, "original", error)
            logger.error(''.join(traceback.TracebackException.from_exception(orig_error).format()))


    try:
        client.run(config['app']['token'])
    except:
        logger.exception('Running client interrupted with exception.')
