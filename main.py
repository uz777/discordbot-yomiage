import asyncio
import json
import os
import subprocess
import sys
import traceback
from asyncio import Task
from dataclasses import dataclass, field

import yaml
import re
import discord
from discord import VoiceChannel, VoiceClient, Message
from discord.ext import commands
import logging.config

from discord.ext.commands import Context


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


@dataclass
class User:
    id: int = 0
    name: str = ''
    voice_type: str = ''


@dataclass
class VoiceSource:
    user: User = None
    text: str = ''


@dataclass
class Server:
    id: int = 0
    text_channel: discord.TextChannel = None
    voice_channel: discord.VoiceChannel = None
    users: dict[int, User] = field(default_factory=dict)
    voice_que = asyncio.Queue()
    play_next_voice = asyncio.Event()
    task: Task = None

    def toggle_next_voice(self, error):
        client.loop.call_soon_threadsafe(self.play_next_voice.set)

    async def voice_play_task(self):
        input_file = resource_path(f'{self.id}.txt')
        output_file = resource_path(f'{self.id}.wav')
        while True:
            self.play_next_voice.clear()
            current = await self.voice_que.get()
            try:
                create_wav(current, input_file, output_file)
                source = discord.FFmpegPCMAudio(output_file)
                self.voice_channel.guild.voice_client.play(source, after=self.toggle_next_voice)
            except:
                logger.exception('Exception in voice play task.')
            await self.play_next_voice.wait()


servers: dict[int, Server] = {}


def initialize() -> None:
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


def root_path() -> str:
    """ ルートパス取得
    スクリプト実行パス(.exe実行の場合は展開されたディレクトリのパス)を取得する

    :return: ルートパス
    """
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.abspath('.')


def resource_path(relative_path: str) -> str:
    """ パス変換
    resouceディレクトリからの相対パスを、
    絶対パスへ変換して返却する

    :param relative_path: resouceディレクトリからの相対パス
    :return: 絶対パス
    """
    return os.path.join(root_path(), 'resource', relative_path)


def make_speakable(text: str) -> str:
    """ 文字列可読化
    文字列を読み上げ可能な状態へ加工して返却する

    :param text: 変換前文字列
    :return: 変換後文字列
    """
    # 2行目以降の削除
    text = text.split('\n')[0]
    # メンションの削除
    text = re.sub(r'@\d{18}', '', text)
    # URLの置換
    text = re.sub(r"https?://[\w/:%#\$&\?\(\)~\.=\+\-]+", 'ゆーあーるえる', text)
    # 5桁以上の数字の置換
    text = re.sub(r'\d{5,}', 'たくさん', text)
    # 絵文字の削除
    text = re.sub(r'<:\w+:\d+>', '', text)
    return text


def create_wav(source: VoiceSource, input_file: str, output_file: str) -> None:
    """ 読み上げ音声ファイル生成
    open_jtalkを使用し、文字列から読み上げ音声ファイルを生成する

    :param input_file:
    :param output_file:
    :param source: キュー
    :return: None
    """

    with open(input_file, 'w', encoding='shift_jis') as file:
        file.write(source.text)

    command = 'open_jtalk.exe -x {x} -m {m} -r {r} -ow {ow} {input_file}'

    # 辞書のPath
    x = resource_path('dic')

    # ボイスファイルのPath
    vt = config['app']['voice_type']
    if source.user:
        vt = source.user.voice_type

    m = resource_path(f'htsvoice\\{VOICE_TYPES[vt]}')

    # 発声のスピード
    r = '1.0'

    # 出力ファイル名　and　Path

    args = {'x': x, 'm': m, 'r': r, 'ow': output_file, 'input_file': input_file}

    cmd = command.format(**args)
    logger.debug(f'Execute open_jtalk command ({cmd})')

    subprocess.run(cmd)
    return True


if __name__ == '__main__':

    initialize()
    client = commands.Bot(command_prefix=config['app']['cmd_prefix'])


    @client.event
    async def on_ready() -> None:
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
    async def join(ctx) -> None:
        """ 接続
        ユーザーが参加しているVCへbotを参加させる

        :param ctx: Context
        :return: None
        """
        logger.info(f'Received [join] cmd from user ({ctx.author.id}/{ctx.author.name}).')

        bot_vc: VoiceChannel = None
        bot_vc_cl: VoiceClient = ctx.voice_client
        if bot_vc_cl:
            bot_vc = bot_vc_cl.channel

        user_vc: VoiceChannel = ctx.author.voice.channel
        if not user_vc:
            logger.warning('User is not in voice channel.')
            return

        if bot_vc:
            if bot_vc.id == user_vc.id:
                server = servers[ctx.guild.id]
                if server.text_channel.id == ctx.channel.id:
                    logger.warning(f'Nothing to do.')
                else:
                    logger.info(f'Change text channel ({server.text_channel.name}) to ({ctx.channel.name})')
                    server.text_channel = ctx.channel
                return
            else:
                logger.info(f'Disconnecting from voice channel ({bot_vc.id}/{bot_vc.name}).')
                await bot_vc_cl.disconnect()

        logger.info(f'Connecting users voice channel ({user_vc.id}/{user_vc.name})')
        await user_vc.connect()

        if ctx.guild.id in servers:
            server = servers[ctx.guild.id]
            server.voice_channel = user_vc
            server.text_channel = ctx.channel
            server.voice_que = []
        else:
            server = Server()
            server.id = ctx.guild.id
            server.voice_channel = user_vc
            server.text_channel = ctx.channel
            server.task = client.loop.create_task(server.voice_play_task())
            servers[ctx.guild.id] = server


    @client.command()
    async def bye(ctx: Context) -> None:
        """ 切断
        botが接続中のVCから切断する

        :param ctx: Context
        :return: None
        """

        logger.info(f'Received [bye] cmd from user ({ctx.author.id}/{ctx.author.name}).')
        bot_vc_cl: VoiceClient = ctx.voice_client
        if bot_vc_cl:
            bot_vc: VoiceChannel = bot_vc_cl.channel
            if bot_vc:
                logger.info(f'Disconnecting from voice channel ({bot_vc.id}/{bot_vc.name}).')
                await ctx.voice_client.disconnect()

                if ctx.guild.id in servers:
                    servers[ctx.guild.id].task.cancel()
                    del servers[ctx.guild.id]

        else:
            logger.warning(f'Not in voice channel.')


    @client.command()
    async def voice(ctx: Context, arg: str) -> None:
        logger.info(f'Received [voice] cmd from user ({ctx.author.id}/{ctx.author.name}).')

        if ctx.guild.id not in servers:
            servers[ctx.guild.id] = Server(id=ctx.guild.id)

        if arg not in VOICE_TYPES:
            logger.warning(
                f'Argument ({arg}) does not exist in voice types. setting app default ({config["app"]["voice_type"]})')
            arg = config['app']['voice_type']

        server = servers[ctx.guild.id]
        if ctx.author.id in server.users:
            user = server.users[ctx.author.id]
            user.id = ctx.author.id
            user.name = ctx.author.name
            user.voice_type = arg
        else:
            server.users[ctx.author.id] = User(ctx.author.id, ctx.author.name, arg)


    @client.command()
    async def status(ctx: Context) -> None:
        logger.info(f'Received [status] cmd from user ({ctx.author.id}/{ctx.author.name}).')

        if ctx.guild.id in servers:
            server = servers[ctx.guild.id]
            embed = discord.Embed(
                title='ステータス',
                description='ボット内部状態')

            embed.add_field(
                name='TEXT',
                value=server.text_channel.name)
            embed.add_field(
                name='->',
                value='to')
            embed.add_field(
                name='VC',
                value=server.voice_channel.name)

            table = None
            if len(server.users) > 0:
                raw = {}
                for user in server.users.values():
                    raw[user.name] = user.voice_type

                table = json.dumps(raw, indent=2, ensure_ascii=False)

            embed.add_field(
                name='SPECIFIC VOICETYPE',
                value=f"```\n{table if table else 'None'}\n```",
                inline=False
            )

            await ctx.send(embed=embed)


    @client.event
    async def on_message(message: Message) -> None:
        """ メッセージ受信
        テキストチャンネルでメッセージが投稿された際に呼び出される
        コマンド以外の文字列かつ読み上げ対象であれば、音声を再生する

        :param message: メッセージ
        :return: None
        """

        while True:
            if message.author.bot:
                logger.debug('Ignored message from bot.')
                break
            if message.guild.id not in servers:
                logger.debug(f'Unknown guild id.')
                break

            server = servers[message.guild.id]
            if server.text_channel.id != message.channel.id:
                logger.debug(f'Received message from other channel.')
                break
            if message.content.startswith(config['app']['cmd_prefix']):
                logger.debug(f'Ignored starting with command prefix.')
                break

            bot_vc_cl = message.guild.voice_client
            if not bot_vc_cl:
                logger.debug(f'Has no Voice Client.')
                break

            logger.info(f'Received message from user ({message.author.id}/{message.author.name}).')
            logger.debug(f'Raw message content ({message.content})')
            text_for_speak = make_speakable(message.content)
            logger.debug(f'Converted message content ({text_for_speak})')

            source = VoiceSource()
            source.text = text_for_speak
            if message.author.id in server.users:
                source.user = server.users[message.author.id]
            await server.voice_que.put(source)
            break

        await client.process_commands(message)


    @client.event
    async def on_error(event, *args, **kwargs) -> None:
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
    async def on_command_error(ctx: Context, error: Exception) -> None:
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
