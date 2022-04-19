import asyncio
import json
import os
import subprocess
import sys
import traceback
from asyncio import Task
from dataclasses import dataclass, field
from logging import Logger

import yaml
import re
import discord
from discord import VoiceChannel, VoiceClient, Message, TextChannel
from discord.ext import commands
import logging.config

from discord.ext.commands import Context

VERSION = '0.1.0'
"""
VERSION
    アプリケーションバージョン
"""

REPOSITORY = 'https://github.com/zosan777/discordbot-yomiage'


def get_logo() -> str:
    """ ロゴ表示

    :return: None
    """
    return f"""
██╗   ██╗ ██████╗ ███╗   ███╗██╗ █████╗  ██████╗ ███████╗
╚██╗ ██╔╝██╔═══██╗████╗ ████║██║██╔══██╗██╔════╝ ██╔════╝
 ╚████╔╝ ██║   ██║██╔████╔██║██║███████║██║  ███╗█████╗  
  ╚██╔╝  ██║   ██║██║╚██╔╝██║██║██╔══██║██║   ██║██╔══╝  
   ██║   ╚██████╔╝██║ ╚═╝ ██║██║██║  ██║╚██████╔╝███████╗
   ╚═╝    ╚═════╝ ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
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
声質略記名とファイル名のマップ
"""

BACK_SLASH = '\n'
"""
BACK_SLASH
    改行文字
"""


@dataclass
class User:
    """ ユーザー
    ユーザーの個別設定を保持するクラス
    """
    id: int = 0
    name: str = ''
    voice_type: str = ''


@dataclass
class VoiceSource:
    """ 音声化元
    音声化を行う元情報
    """
    user: User = None
    text: str = ''


@dataclass
class Server:
    """ サーバー
    VC接続後、1サーバーに対して1つ割り当てられるインスタンス
    """
    id: int = 0
    text_channel: TextChannel = None
    voice_channel: VoiceChannel = None
    users: dict[int, User] = field(default_factory=dict)
    voice_que = asyncio.Queue()
    play_next_voice = asyncio.Event()
    task: Task = None

    def toggle_next_voice(self, error: Exception) -> None:
        """ 再生終了コールバック
        音声再生終了後に呼び出される

        :param error: 例外
        :return: None
        """
        client.loop.call_soon_threadsafe(self.play_next_voice.set)

    async def voice_play_task(self):
        """ 再生タスク
        サーバーごとに常駐するタスク
        voice_queに新しいキューが入ると処理を実行し、
        再生の終了を待ち合わせる

        :return: None
        """
        input_file = resource_path(f'{self.id}.txt')
        output_file = resource_path(f'{self.id}.wav')
        while True:
            self.play_next_voice.clear()
            current = await self.voice_que.get()
            try:
                create_wav(current, input_file, output_file)
                source = discord.FFmpegPCMAudio(output_file)
                self.voice_channel.guild.voice_client.play(source, after=self.toggle_next_voice)
                await self.play_next_voice.wait()
            except:
                logger.exception('Exception in voice play task.')
                tb = tb = traceback.format_exc()
                if self.text_channel:
                    await error_message(self.text_channel, app.config.msg.task.e_failed, None, str(sys.exc_info()), tb)


class App:
    token: str = ''
    cmd_prefix: str = '.'
    voice_type: str = 'n'


class Color:
    success: int = 0
    warning: int = 0
    error: int = 0


class CommonMsg:
    success: str
    warning: str
    error: str


class JoinMsg:
    s_yomiage_started: str
    w_user_not_in_vc: str
    w_nothing_to_do: str


class ByeMsg:
    w_bot_not_in_vc: str
    s_yomiage_stopped: str


class VoiceMsg:
    s_voice_changed: str
    w_bot_not_joined: str
    w_arg_not_valid: str


class DefaultMsg:
    s_user_has_no_own_config: str
    w_nothing_to_do: str


class TaskMsg:
    e_failed: str


class CommandMsg:
    e_not_found: str
    e_failed: str


class Msg:
    common: CommonMsg = CommonMsg()
    join: JoinMsg = JoinMsg()
    bye: ByeMsg = ByeMsg()
    voice: VoiceMsg = VoiceMsg()
    default: DefaultMsg = DefaultMsg()
    task: TaskMsg = TaskMsg()
    command: CommandMsg = CommandMsg()


class Config:
    """ 設定
    yaml設定内容を保持する
    """
    app: App = App()
    color: Color = Color()
    msg: Msg = Msg()


class Yomiage:
    """ アプリケーション
    内部状態のルートクラス
    """
    config: Config = Config()

    servers: dict[int, Server] = {}

    def __init__(self):
        """ 初期化処理
        アプリケーションの実行前に必要とな処理を行う
        ・標準出力へのロゴ表示
        ・設定ファイルの読み込み
            引数で指定があればそのパスを設定ファイルとして読み込む
            指定が無い場合は、config.ymlを設定ファイルとして読み込む
            設定ファイルが存在しない場合はエラーとする
        ・ロガー初期化
            読み込んだ設定ファイルでロガーを初期化する
        ・環境変数の設定
            外部.exeの実行に必要となる
        ・コーデック読み込み
        """
        print(get_logo())
        print('Initializing application...')
        if 1 < len(sys.argv):
            config_path = os.path.abspath(sys.argv[1])
        else:
            config_path = os.path.abspath('config.yml')

        if not os.path.isfile(config_path):
            logger.error(f'Config yaml file ({config_path}) does not exist.')
            sys.exit(1)
        else:
            with open(config_path, 'r', encoding="utf-8") as yml:
                config_dict = yaml.safe_load(yml)
                logging.config.dictConfig(config_dict)

                self.config.app.token = config_dict['app']['token']
                self.config.app.cmd_prefix = config_dict['app']['cmd_prefix']
                vt = config_dict['app']['voice_type']
                if vt in VOICE_TYPES:
                    self.config.app.voice_type = vt
                else:
                    logger.warning(f'Voice Type ({vt}) does not exist. Replaced to (n).')

                # Color
                self.config.color.success = config_dict['color']['success']
                self.config.color.warning = config_dict['color']['warning']
                self.config.color.error = config_dict['color']['error']

                # Msg Common
                self.config.msg.common.success = config_dict['msg']['common']['success']
                self.config.msg.common.warning = config_dict['msg']['common']['warning']
                self.config.msg.common.error = config_dict['msg']['common']['error']

                # Msg Join
                self.config.msg.join.s_yomiage_started = config_dict['msg']['join']['s_yomiage_started']
                self.config.msg.join.w_nothing_to_do = config_dict['msg']['join']['w_nothing_to_do']
                self.config.msg.join.w_user_not_in_vc = config_dict['msg']['join']['w_user_not_in_vc']

                # Msg Bye
                self.config.msg.bye.s_yomiage_stopped = config_dict['msg']['bye']['s_yomiage_stopped']
                self.config.msg.bye.w_bot_not_in_vc = config_dict['msg']['bye']['w_bot_not_in_vc']

                # Msg Voice
                self.config.msg.voice.s_voice_changed = config_dict['msg']['voice']['s_voice_changed']
                self.config.msg.voice.w_arg_not_valid = config_dict['msg']['voice']['w_arg_not_valid']
                self.config.msg.voice.w_bot_not_joined = config_dict['msg']['voice']['w_arg_not_valid']

                # Msg Default
                self.config.msg.default.s_user_has_no_own_config = config_dict['msg']['default'][
                    's_user_has_no_own_config']
                self.config.msg.default.w_nothing_to_do = config_dict['msg']['default']['w_nothing_to_do']

                # Msg Task
                self.config.msg.task.e_failed = config_dict['msg']['task']['e_failed']

                # Msg Command
                self.config.msg.command.e_not_found = config_dict['msg']['command']['e_not_found']
                self.config.msg.command.e_failed = config_dict['msg']['command']['e_failed']

        # バイナリディレクトリにパスを通す(コマンド実行に必要)
        os.environ["PATH"] += os.pathsep + os.path.join(root_path(), 'resource')

        # opus(コーデック)読み込み
        if not discord.opus.is_loaded():
            discord.opus.load_opus(resource_path('libopus.dll'))


class JapaneseHelpCommand(commands.DefaultHelpCommand):
    def __init__(self):
        super().__init__()
        self.commands_heading = "コマンド:"
        self.no_category = "その他"
        self.command_attrs["help"] = "コマンド一覧と簡単な説明を表示"

    def get_ending_note(self):
        return f'各コマンドの説明: {app.config.app.cmd_prefix}help <コマンド名>'


app: Yomiage
logger: Logger


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
    text = text.split(BACK_SLASH)[0]
    # メンションの削除
    text = re.sub(r'@\d{18}', '', text)
    # URLの置換
    text = re.sub(r"https?://[\w/:%#$&?()~.=+\-]+", 'ゆーあーるえる', text)
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
    vt = app.config.app.voice_type
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


async def success_message(ctx, text, text_param):
    message = ''
    if text:
        message = text
        if text_param:
            message = message.format(**text_param)

    await ctx.send(embed=discord.Embed(
        color=app.config.color.success,
        title=app.config.msg.common.success,
        description=message))


async def warning_message(ctx, text, text_param):
    message = ''
    if text:
        message = text
        if text_param:
            message = message.format(**text_param)

    await ctx.reply(embed=discord.Embed(
        color=app.config.color.warning,
        title=app.config.msg.common.warning,
        description=message))


async def error_message(ctx, text, text_param, error_text, traceback_text):
    message = ''
    if text:
        message = text
        if text_param:
            message = message.format(**text_param)

    embed = discord.Embed(
        color=app.config.color.error,
        title=app.config.msg.common.error,
        description=message)

    if error_text and traceback_text:
        embed.add_field(name='ERROR', value=error_text)
        embed.add_field(name='TRACEBACK', value=traceback_text)

    if isinstance(ctx, Context):
        await ctx.reply(embed=embed)
    elif isinstance(ctx, TextChannel):
        await ctx.send(embed=embed)


if __name__ == '__main__':
    app = Yomiage()
    logger = logging.getLogger('yomiage')
    client = commands.Bot(command_prefix=app.config.app.cmd_prefix, help_command=JapaneseHelpCommand())


    @client.event
    async def on_ready() -> None:
        """ 待機開始
        コマンドを受付可能となった際に実行される
        設定状態などをログに出力する
        """
        logger.info(f'VERSION: {VERSION}')
        logger.info(f'REPOSITORY: {REPOSITORY}')
        logger.info('==========================================================')
        logger.info(f'cmd_prefix: {app.config.app.cmd_prefix}')
        logger.info(f'voice_type: {app.config.app.voice_type} ({VOICE_TYPES[app.config.app.voice_type]})')
        logger.info(f'bot_user: {client.user.id}/{client.user.name}')
        logger.info('==========================================================')
        logger.info('Application successfully　launched. Now waiting users operation.')


    @client.command()
    async def version(ctx) -> None:
        """ バージョン情報表示
        バージョン情報を表示します
        """

        logger.info(f'Received [version] cmd from user ({ctx.author.name}).')
        embed = discord.Embed(
            color=app.config.color.success,
            title=app.config.msg.common.success,
            description='バージョン情報')
        embed.add_field(name='APPNAME', value='yomiage')
        embed.add_field(name='VERSION', value=VERSION)
        embed.add_field(name='REPOSITORY', value=REPOSITORY)

        await ctx.send(embed=embed)


    @client.command()
    async def join(ctx) -> None:
        """ 接続・読み上げ開始
        ユーザーが参加しているボイスチャンネルにbotを参加させ、
        コマンドを実行したテキストチャンネルの読み上げを開始します
        ボイスチャンネル・テキストチャンネルを変更したい場合は、
        目的のボイスチャンネルに参加したうえで、目的のテキストチャンネルからコマンドを再実行してください
        """
        logger.info(f'Received [join] cmd from user ({ctx.author.name}).')

        bot_vc: VoiceChannel = None
        bot_vc_cl: VoiceClient = ctx.voice_client
        if bot_vc_cl:
            bot_vc = bot_vc_cl.channel

        user_vc: VoiceChannel = None
        if ctx.author.voice:
            user_vc = ctx.author.voice.channel

        if not user_vc:
            logger.warning('User is not in voice channel.')
            await warning_message(ctx, app.config.msg.join.w_user_not_in_vc, {
                'cmd_prefix': app.config.app.cmd_prefix
            })
            return

        if bot_vc:
            if bot_vc.id == user_vc.id:
                server = app.servers[ctx.guild.id]
                if server.text_channel.id == ctx.channel.id:
                    logger.warning(f'Nothing to do.')
                    await warning_message(ctx, app.config.msg.join.w_nothing_to_do, {
                        'cmd_prefix': app.config.app.cmd_prefix,
                        'text_channel': ctx.channel.name,
                        'voice_channel': user_vc.name
                    })
                    return
                else:
                    logger.info(f'Change text channel ({server.text_channel.name}) to ({ctx.channel.name})')
                    await success_message(ctx, app.config.msg.join.s_yomiage_started, {
                        'text_channel': ctx.channel.name,
                        'voice_channel': user_vc.name
                    })
                    server.text_channel = ctx.channel
                return
            else:
                logger.info(f'Disconnecting from voice channel ({bot_vc.name}).')
                await bot_vc_cl.disconnect()

        logger.info(f'Connecting users voice channel ({user_vc.name})')
        await user_vc.connect()

        if ctx.guild.id in app.servers:
            server = app.servers[ctx.guild.id]
            server.voice_channel = user_vc
            server.text_channel = ctx.channel
        else:
            server = Server()
            server.id = ctx.guild.id
            server.voice_channel = user_vc
            server.text_channel = ctx.channel
            server.task = client.loop.create_task(server.voice_play_task())
            app.servers[ctx.guild.id] = server

        await success_message(ctx, app.config.msg.join.s_yomiage_started, {
            'text_channel': ctx.channel.name,
            'voice_channel': user_vc.name
        })


    @client.command()
    async def bye(ctx: Context) -> None:
        """ 切断・読み上げ停止
        botを接続中のボイスチャンネルから切断し、
        テキストチャンネルからの読み上げを停止します
        """

        logger.info(f'Received [bye] cmd from user ({ctx.author.name}).')
        bot_vc_cl: VoiceClient = ctx.voice_client
        if bot_vc_cl:
            bot_vc: VoiceChannel = bot_vc_cl.channel
            if bot_vc:
                logger.info(f'Disconnecting from voice channel ({bot_vc.id}/{bot_vc.name}).')

                await ctx.voice_client.disconnect()
                if ctx.guild.id in app.servers:
                    server = app.servers[ctx.guild.id]
                    server.task.cancel()
                    await success_message(ctx, app.config.msg.bye.s_yomiage_stopped, {
                        'text_channel': server.text_channel.name,
                        'voice_channel': server.voice_channel.name
                    })
                    del app.servers[ctx.guild.id]
        else:
            logger.warning(f'Not in voice channel.')
            await warning_message(ctx, app.config.msg.bye.w_bot_not_in_vc, None)


    @client.command()
    async def voice(ctx: Context, arg: str) -> None:
        """ ユーザー個別声質変更
        ユーザーの声質を、引数で指定したものへ変更します
        本設定はユーザーごとに、接続～切断の間保持されます
        切断すると設定は破棄されます
        また、未接続状態では設定できません
        <arg>に設定可能な値は以下の通りです
        n : 男性１通常
        ma: 女性１怒り
        mb: 女性１照れ
        mh: 女性１喜び
        mn: 女性１通常
        ms: 女性１悲しみ
        ta: 男性１怒り
        th: 男性１喜び
        tn: 男性１通常
        ts: 男性１悲しみ
        """
        logger.info(f'Received [voice] cmd from user ({ctx.author.name}).')

        if ctx.guild.id not in app.servers:
            logger.warning(f'Not joined yet.')
            await warning_message(ctx, app.config.msg.voice.w_bot_not_joined, {
                'cmd_prefix': app.config.app.cmd_prefix
            })
            return

        if arg not in VOICE_TYPES:
            logger.warning(
                f'Argument ({arg}) does not exist in voice types. setting app default ({app.config.app.voice_type})')
            arg = app.config.app.voice_type
            await warning_message(ctx, app.config.msg.voice.w_arg_not_valid, {
                'arg': arg,
                'cmd_prefix': app.config.app.cmd_prefix
            })
            return

        server = app.servers[ctx.guild.id]
        if ctx.author.id in server.users:
            user = server.users[ctx.author.id]
            user.id = ctx.author.id
            user.name = ctx.author.name
            user.voice_type = arg
        else:
            server.users[ctx.author.id] = User(ctx.author.id, ctx.author.name, arg)

        await success_message(ctx, app.config.msg.voice.s_voice_changed, {
            'voice_type_name': arg
        })


    @client.command()
    async def default(ctx: Context) -> None:
        """ ユーザー個別設定削除
        ユーザー個別設定を削除し、デフォルト状態へ戻します
        """
        logger.info(f'Received [default] cmd from user ({ctx.author.name}).')
        if ctx.guild.id in app.servers:
            server = app.servers[ctx.guild.id]
            if ctx.author.id in server.users:
                del server.users[ctx.author.id]
                await success_message(ctx, app.config.msg.default.s_user_has_no_own_config, None)
                return
        logger.warning(f'Already default.')
        await warning_message(ctx, app.config.msg.default.w_nothing_to_do, None)


    @client.command()
    async def status(ctx: Context) -> None:
        """ ボット状態確認
        ボットの内部状態を確認します
        """
        logger.info(f'Received [status] cmd from user ({ctx.author.name}).')

        if ctx.guild.id in app.servers:
            server = app.servers[ctx.guild.id]
            embed = discord.Embed(
                color=app.config.color.success,
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
                value=f"```{BACK_SLASH}{table if table else 'None'}{BACK_SLASH}```",
                inline=False
            )

            await ctx.send(embed=embed)


    @client.event
    async def on_message(message: Message) -> None:
        """ メッセージ受信
        テキストチャンネルでメッセージが投稿された際に呼び出される
        コマンド以外の文字列かつ読み上げ対象であれば、音声を再生する
        """

        while True:
            if message.author.bot:
                logger.debug('Ignored message from bot.')
                break
            if message.guild.id not in app.servers:
                logger.debug(f'Unknown server id.')
                break

            server = app.servers[message.guild.id]
            if not server.text_channel or not server.voice_channel:
                logger.debug(f'Not Joined')
                break
            if server.text_channel.id != message.channel.id:
                logger.debug(f'Received message from other channel.')
                break
            if message.content.startswith(app.config.app.cmd_prefix):
                logger.debug(f'Ignored starting with command prefix.')
                break

            bot_vc_cl = message.guild.voice_client
            if not bot_vc_cl:
                logger.debug(f'Has no Voice Client.')
                break

            logger.info(f'Received message from user ({message.author.id}/{message.author.name}).')
            logger.debug(f'Raw message content ({message.content.replace(BACK_SLASH, "/")})')
            text_for_speak = make_speakable(message.content)
            logger.debug(f'Converted message content ({text_for_speak})')

            source = VoiceSource(text=text_for_speak)
            if message.author.id in server.users:
                source.user = server.users[message.author.id]
            await server.voice_que.put(source)
            break

        await client.process_commands(message)


    @client.event
    async def on_error(event, *args, **kwargs) -> None:
        """ エラーハンドラ
        コマンド以外でエラーが発生した場合のハンドラ
        """
        logger.error(event)
        logger.error(traceback.format_exc())


    @client.event
    async def on_command_error(ctx: Context, error: Exception) -> None:
        """ コマンドエラーハンドラ
        コマンド内でエラーが発生した場合のハンドラ
        """
        logger.error(error)
        if isinstance(error, commands.CommandNotFound):
            await error_message(ctx, app.config.msg.command.e_not_found, {
                'cmd_prefix': app.config.app.cmd_prefix
            }, None, None)
            return

        orig_error = getattr(error, "original", error)
        tb = ''.join(traceback.TracebackException.from_exception(orig_error).format())
        logger.error(tb)
        await error_message(ctx, app.config.msg.command.e_failed, None, str(orig_error), tb)


    try:
        client.run(app.config.app.token)
    except:
        logger.exception('Running client interrupted with exception.')
