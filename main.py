import discord
from discord.ext import commands
import json
import os
import random
import datetime
from keep_alive import keep_alive

keep_alive()

PREFIX = '!'
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS", "").split(",")))

# Botインスタンス
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # メンバー情報にアクセスするために必要
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

bot.remove_command('help')

XP_DATA_FILE = 'xp_data.json'


def load_xp_data():
    """XPデータをファイルからロードする関数"""
    try:
        with open(XP_DATA_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}  # ファイルが見つからなかった場合は空の辞書を返す
    except json.JSONDecodeError:
        return {}  # JSONエラーの場合も空の辞書を返す


def save_xp_data(data):
    """XPデータをファイルに保存する関数"""
    with open(XP_DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)


# 初回データロード
xp_data = load_xp_data()


@bot.command()
async def xp(ctx, action: str, target: str, value: int = None):
    """XP管理コマンド (add, remove, clear)"""
    if not ctx.author.guild_permissions.administrator and not ctx.author.permissions_in(
            ctx.channel).administrator:
        await ctx.send("このコマンドを実行するには、サーバー管理者権限またはBotの管理者権限が必要です。")
        return

    if action not in ["add", "remove", "clear"]:
        await ctx.send("無効なアクションです。`add`, `remove`, `clear` のいずれかを指定してください。")
        return

    if action == "add" or action == "remove":
        if value is None:
            await ctx.send("`value`（XPの増減値）を指定してください。")
            return

        if action == "add":
            xp_data[target] = xp_data.get(target, 0) + value
            save_xp_data(xp_data)
            await ctx.send(
                f"{target}のXPが{value}増加しました。現在のXP: {xp_data[target]}")
        elif action == "remove":
            xp_data[target] = xp_data.get(target, 0) - value
            save_xp_data(xp_data)
            await ctx.send(
                f"{target}のXPが{value}減少しました。現在のXP: {xp_data[target]}")

    elif action == "clear":
        if value is not None:
            await ctx.send("`clear`アクションでは`value`は無視されます。")

        if target == "all":
            xp_data.clear()
            save_xp_data(xp_data)
            await ctx.send("すべてのXPデータが初期化されました！")
        elif target.isdigit():
            target = str(target)
            if target in xp_data:
                del xp_data[target]
                save_xp_data(xp_data)
                await ctx.send(f"{target}のXPデータが初期化されました！")
            else:
                await ctx.send(f"指定されたID({target})は存在しません。")
        else:
            await ctx.send(
                "無効な引数です。`!xp clear <all | user_ID | server_ID>` の形式で指定してください。"
            )


def add_xp(user_id, amount):
    """XPとレベルを管理する関数"""
    user_id = str(user_id)
    if user_id not in xp_data:
        xp_data[user_id] = {"xp": 0, "level": 1}

    xp_data[user_id]["xp"] += amount
    xp_needed = xp_data[user_id]["level"] * 100

    if xp_data[user_id]["xp"] >= xp_needed:
        xp_data[user_id]["xp"] -= xp_needed
        xp_data[user_id]["level"] += 1
        save_xp_data(xp_data)
        return True
    save_xp_data(xp_data)
    return False


@bot.command()
async def rank(ctx):
    user_id = str(ctx.author.id)
    if user_id not in xp_data:
        await ctx.send("まだ経験値がありません！")
        return

    level = xp_data[user_id]["level"]
    xp = xp_data[user_id]["xp"]
    xp_needed = level * 100

    embed = discord.Embed(title=f"{ctx.author.name} のランク",
                          color=discord.Color.blue())
    embed.add_field(name="レベル", value=str(level), inline=True)
    embed.add_field(name="XP", value=f"{xp}/{xp_needed}", inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def levels(ctx):
    with open('xp_data.json', 'r') as f:
        xp_data = json.load(f)

    user_data = {}

    # ユーザーごとのレベルとXPを取得
    for user_id, data in xp_data.items():
        level = data['level']
        xp = data['xp']
        user_data[user_id] = {'level': level, 'xp': xp}

    # レベルが高い順、次にXPが高い順、最終的に名前順でソート
    sorted_users = sorted(user_data.items(),
                          key=lambda item:
                          (item[1]['level'], item[1]['xp'], item[0]),
                          reverse=True)

    # Embedを作成
    embed = discord.Embed(title="Top 10 Levels",
                          description="User ranking by level and XP",
                          color=discord.Color.blue())

    # 上位10人を表示
    for i, (user_id, data) in enumerate(sorted_users[:10], 1):
        user = await bot.fetch_user(user_id)  # ユーザー情報を取得
        embed.add_field(name=f"{i}. User: {user.name}",
                        value=f"Lv. {data['level']} XP {data['xp']}",
                        inline=False)

    # Embedを送信
    await ctx.send(embed=embed)

    try:
        with open('xp_data.json', 'r') as f:
            xp_data = json.load(f)
    except FileNotFoundError:
        xp_data = {}


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)
    xp_gained = random.randint(5, 15)

    if add_xp(user_id, xp_gained):
        await message.channel.send(f"🎉 {message.author.mention} がレベルアップ！ 🎉")
    await bot.process_commands(message)


# メッセージ送信時にXPを加算
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)
    xp_gained = random.randint(5, 15)

    if add_xp(user_id, xp_gained):
        await message.channel.send(f"🎉 {message.author.mention} がレベルアップ！ 🎉")
    await bot.process_commands(message)


# モデレートコマンド：BAN
@bot.command()
async def ban(ctx, member: discord.Member, *, reason=None):
    if not ctx.author.guild_permissions.ban_members:
        await ctx.send("あなたにはBAN権限がありません！")
        return
    await member.ban(reason=reason)
    await ctx.send(f"{member.name} がBANされました！理由: {reason}")


# モデレートコマンド：Kick
@bot.command()
async def kick(ctx, member: discord.Member, *, reason=None):
    if not ctx.author.guild_permissions.kick_members:
        await ctx.send("あなたにはKick権限がありません！")
        return
    await member.kick(reason=reason)
    await ctx.send(f"{member.name} がKickされました！理由: {reason}")


# モデレートコマンド：Mute
@bot.command()
async def mute(ctx, member: discord.Member, *, reason=None):
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("あなたにはMute権限がありません！")
        return

    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role,
                                          speak=False,
                                          send_messages=False)

    await member.add_roles(muted_role, reason=reason)
    await ctx.send(f"{member.name} がミュートされました！理由: {reason}")


# 警告システム
warnings = {}  # ユーザーIDをキーに警告リストを保持


@bot.command()
async def warn(ctx, member: discord.Member, *, reason=None):
    # 警告の追加
    user_id = str(member.id)
    now = datetime.datetime.utcnow()
    if user_id not in warnings:
        warnings[user_id] = []

    warnings[user_id].append(now)

    # 警告を表示
    await ctx.send(
        f"{member.mention} に警告が発行されました！理由: {reason or 'No reason provided'}.")

    # 1週間以内に警告が4回を超えたらBAN
    # 古い警告を削除
    warnings[user_id] = [
        warn_time for warn_time in warnings[user_id]
        if (now - warn_time).days <= 7
    ]

    if len(warnings[user_id]) >= 4:
        await member.ban(
            reason=
            f"4 warnings within a week ({', '.join([warn.strftime('%Y-%m-%d') for warn in warnings[user_id]])})"
        )
        await ctx.send(f"{member.mention} は違反が多すぎたため、BANされました！")
        warnings[user_id] = []  # BANされた場合は警告リストをリセット


STATUS_FILE = "status.json"  # ステータス履歴の保存ファイル
OWNER_ID = 1278860195627274282  # あなたのDiscord ID


# ステータスを保存する関数
def save_status(status_text):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump({"status": status_text}, f)


# ステータスを読み込む関数
def load_status():
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("status", None)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


@bot.event
async def on_ready():
    print(f"ログインしました: {bot.user}")

    # 起動時に最新のステータスを適用
    status_text = load_status()
    if status_text:
        await bot.change_presence(activity=discord.Game(name=status_text))
        print(f"前回のステータスを復元: {status_text}")


@bot.command()
async def setstatus(ctx, *, status_text: str):
    """カスタムステータスを設定（Botのオーナーのみ）"""
    if ctx.author.id != OWNER_ID:
        await ctx.send("このコマンドは管理者専用です。")
        return

    await bot.change_presence(activity=discord.Game(name=status_text))
    save_status(status_text)
    await ctx.send(f"ステータスを `{status_text}` に変更しました！")


@bot.command()
async def clearstatus(ctx):
    """カスタムステータスをクリア（Botのオーナーのみ）"""
    if ctx.author.id != OWNER_ID:
        await ctx.send("このコマンドは管理者専用です。")
        return

    # アクティビティを完全に削除する
    await bot.change_presence(activity=None, status=discord.Status.online)
    save_status("")  # 空のステータスを保存
    await ctx.send("カスタムステータスをクリアしました！")


# サポートサーバーのリンク
support_server_url = "https://discord.gg/A6Q3AcYTeC"


@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Bot コマンドリスト",
                          description="以下のコマンドを使用できます。",
                          color=discord.Color.blue())

    # 各コマンドの詳細を追加
    embed.add_field(name="!help", value="これを出す", inline=False)
    embed.add_field(name="!ping", value="生存確認用", inline=False)
    embed.add_field(name="!warn", value="警告付与", inline=False)
    embed.add_field(name="!mute", value="黙らせる。", inline=False)
    embed.add_field(name="!ban", value="二度と来れなくなる。", inline=False)
    embed.add_field(name="!kick", value="一回だけ退出させられる。", inline=False)
    embed.add_field(name="!rank", value="rankカードがEmbedで出る。", inline=False)
    embed.add_field(name="!levels", value="全体で上位１０人がEmbedで出る。", inline=False)

    # サポートサーバーのリンク
    embed.add_field(name="サポートサーバー",
                    value="https://discord.gg/A6Q3AcYTeC",
                    inline=False)

    await ctx.send(embed=embed)


# 再起動コマンド（管理者のみ）
@bot.command()
async def restart(ctx):
    if ctx.author.id == OWNER_ID:
        await ctx.send("Botを再起動します...")
        await bot.close()
    else:
        await ctx.send("再起動は管理者のみが実行できます。")


@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')


# デバッグ用: 確認のためオーナーIDを出力
print("オーナーID:", OWNER_IDS)

TOKEN = os.getenv("TOKEN")

# Botを実行
bot.run(TOKEN)
