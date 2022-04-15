import os
import subprocess
import sys
import traceback

import yaml
import re

import discord
from discord.ext import commands

import logging.config

VERSION = '0.1.0'

logger = logging.getLogger('yomiage')

if 1 < len(sys.argv):
    config_path = sys.argv[1]
else:
    config_path = os.path.abspath('config.yml')

if not os.path.isfile(config_path):
    logger.error(f'Config yaml file ({config_path}) does not exist.')
    sys.exit(1)
else:
    with open(config_path, 'r', encoding="utf-8") as yml:
        config = yaml.safe_load(yml)
        logging.config.dictConfig(config)


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


def initialize():
    """ 初期化処理
    ボットの実行前に必要な初期化処理を行う

    :return: None
    """
    # バイナリディレクトリにパスを通す(コマンド実行に必要)
    os.environ["PATH"] += os.pathsep + os.path.join(root_path(), 'resource')
    if not discord.opus.is_loaded():
        # opus(コーデック)読み込み
        discord.opus.load_opus(resource_path('libopus.dll'))


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
    return text.split('\n')[0]


def remove_custom_emoji(text):
    pattern = r'<:[a-zA-Z0-9_]+:[0-9]+>'
    return re.sub(pattern, '', text)


def url_abb(text):
    pattern = "https?://[\w/:%#\$&\?\(\)~\.=\+\-]+"
    return re.sub(pattern, 'ゆーあーるえる', text)


def make_speakable(text):
    text = remove_multi_line(text)
    text = url_abb(text)
    return remove_custom_emoji(text)


def create_wav(input_text):
    input_file = 'input.txt'

    with open(input_file, 'w', encoding='shift_jis') as file:
        file.write(input_text)

    command = 'open_jtalk.exe -x {x} -m {m} -r {r} -ow {ow} {input_file}'

    # 辞書のPath
    x = resource_path('dic')

    # ボイスファイルのPath
    m = resource_path('htsvoice/nitech_jp_atr503_m001.htsvoice')
    # m = 'C:/open_jtalk/bin/mei/mei_sad.htsvoice'
    # m = 'C:/open_jtalk/bin/mei/mei_angry.htsvoice'
    # m = 'C:/open_jtalk/bin/mei/mei_bashful.htsvoice'
    # m = 'C:/open_jtalk/bin/mei/mei_happy.htsvoice'
    # m = 'C:/open_jtalk/bin/mei/mei_normal.htsvoice'

    # 発声のスピード
    r = '1.0'

    # 出力ファイル名　and　Path
    ow = 'output.wav'

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
        print('==========================================================')
        print(f'version: {VERSION}')
        print(f'cmd_prefix: {config["app"]["cmd_prefix"]}')
        print(f'bot user: {client.user.id}/{client.user.name}')
        print('==========================================================')


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
                    logger.info(f'Already in users voice channel ({user_vc.id}/{user_vc.name}).')
                    return
                else:
                    logger.info(f'Disconnecting from voice channel ({bot_vc.id}/{bot_vc.name}).')
                    await bot_vc_cl.disconnect()
            logger.info(f'Connecting users voice channel ({user_vc.id}/{user_vc.name})')
            await user_vc.connect()
        else:
            logger.info('User is not in voice channel.')


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
            logger.info(f'Not in voice channel.')


    @client.event
    async def on_message(message):
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
                source = discord.FFmpegPCMAudio("output.wav")
                bot_vc_cl.play(source)
            else:
                pass
        await client.process_commands(message)


    @client.event
    async def on_error(event, *args, **kwargs):
        logger.error(event)
        logger.error(traceback.format_exc())


    @client.event
    async def on_command_error(ctx, error):
        logger.error(error)
        if isinstance(error, commands.CommandInvokeError):
            orig_error = getattr(error, "original", error)
            logger.error(''.join(traceback.TracebackException.from_exception(orig_error).format()))


    client.run(config['app']['token'])
