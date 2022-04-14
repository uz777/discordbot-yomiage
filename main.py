import os
import sys
import yaml

import discord
from discord.ext import commands

import logging
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(message)s',
    handlers=[RichHandler(rich_tracebacks=True)],
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if 1 < len(sys.argv):
    config_path = sys.argv[1]
else:
    config_path = os.path.abspath('config.yml')

if not os.path.isfile(config_path):
    logger.error(f'Config yaml file ({config_path}) does not exist.')
    sys.exit(1)
else:
    with open(config_path, 'r') as yml:
        config = yaml.safe_load(yml)


def initialize():
    """ 初期化処理
    ボットの実行前に必要な初期化処理を行う

    :return: None
    """
    if not hasattr(sys, '_MEIPASS'):
        # resourceディレクトリをパスに追加する
        # .exe実行の際は、main.specで予めパスを指定済なので不要
        sys.path.insert(0, os.path.join(os.path.abspath('.')))
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


if __name__ == '__main__':

    initialize()
    client = commands.Bot(command_prefix=config['app']['cmd_prefix'])


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


    client.run(config['app']['token'])
