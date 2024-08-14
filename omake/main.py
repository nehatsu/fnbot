import discord
from discord.ext import commands,tasks
from discord import app_commands
import asyncio
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
import motor.motor_asyncio
from datetime import datetime, timedelta
import json

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


bot = commands.Bot(command_prefix='!', intents=intents)


voting_active = False

vote_data = {}

MONGO_URI = "mongodb://localhost:27017/"
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client["linksetting"]
settings_collection = db["link_settings"]

@bot.event
async def on_ready():
    latency = bot.latency * 1000
    count = len(bot.guilds)
    await bot.tree.sync()
    await bot.change_presence(activity=discord.Game(name=f"やる気{count}%")) 
    load_recruitments()

    print(f"{bot.user.name} がログインしました！ping値{latency}導入数{count}")
    invite_link = discord.utils.oauth_url(
        bot.user.id,
        permissions=discord.Permissions(administrator=True),
        scopes=("bot", "applications.commands")
    )
    print(f"your url: {invite_link}")

@bot.tree.command(name="servervote", description="サーバー投票を開始します")
@app_commands.describe(duration="投票時間（秒）", topic="投票内容")
async def servervote(interaction: discord.Interaction, duration: int, topic: str):
    global voting_active, vote_data

    if voting_active:
        return await interaction.response.send_message("既に投票が実行されています。", ephemeral=True)

    voting_active = True
    vote_data = {
        "topic": topic,
        "votes": {"agree": 0, "disagree": 0, "abstain": 0},
        "voters": []
    }

    async def end_vote():
        await asyncio.sleep(duration)

        if voting_active:
            await show_results(interaction)

    # ボタンを定義
    view = discord.ui.View(timeout=duration)
    agree_button = discord.ui.Button(label="賛成", style=discord.ButtonStyle.blurple, custom_id="agree")
    disagree_button = discord.ui.Button(label="反対", style=discord.ButtonStyle.red, custom_id="disagree")
    abstain_button = discord.ui.Button(label="投票放棄", style=discord.ButtonStyle.green, custom_id="abstain")

    async def button_callback(interaction: discord.Interaction, button_id: str):
        if interaction.user.id in vote_data["voters"]:
            await interaction.response.send_message("既に投票済みです。", ephemeral=True)
            return

        vote_weight = 1
        for role in interaction.user.roles:
            if role.name == "鯖主":
                vote_weight += 500
            elif role.name == "管理者":
                vote_weight += 100
            elif role.name == "古参":
                vote_weight += 50
            elif role.name == "Server Booster":
                vote_weight += 30
            elif role.name == "BZC":
                vote_weight += 10
            elif role.name == "VIP":
                vote_weight += 10
            elif role.name == "常連":
                vote_weight += 5
            elif role.name == "アズカBAN":
                vote_weight *= 0

        vote_data["votes"][button_id] += vote_weight
        vote_data["voters"].append(interaction.user.id)
        await interaction.response.send_message(f"{button_id}に投票しました。(投票力: {vote_weight})", ephemeral=True)

    async def agree_callback(interaction: discord.Interaction):
        await button_callback(interaction, "agree")

    async def disagree_callback(interaction: discord.Interaction):
        await button_callback(interaction, "disagree")

    async def abstain_callback(interaction: discord.Interaction):
        await button_callback(interaction, "abstain")

    agree_button.callback = agree_callback
    disagree_button.callback = disagree_callback
    abstain_button.callback = abstain_callback

    view.add_item(agree_button)
    view.add_item(disagree_button)
    view.add_item(abstain_button)

    await interaction.response.send_message(f"**投票開始:** {topic}\n時間制限: {duration}秒", view=view)
    bot.loop.create_task(end_vote())

@bot.tree.command(name="endvote", description="投票を終了します")
async def endvote(interaction: discord.Interaction):
    global voting_active

    if not voting_active:
        return await interaction.response.send_message("現在投票は行われていません。", ephemeral=True)

    voting_active = False
    await show_results(interaction)

async def show_results(interaction: discord.Interaction):
    global vote_data
    result_message = f"**投票終了:** {vote_data['topic']}\n\n"

    agree_votes = vote_data["votes"]["agree"]
    disagree_votes = vote_data["votes"]["disagree"]
    abstain_votes = vote_data["votes"]["abstain"]

    max_votes = max(agree_votes, disagree_votes, abstain_votes)
    if max_votes == agree_votes:
        most_voted_option = "賛成"
    elif max_votes == disagree_votes:
        most_voted_option = "反対"
    else:
        most_voted_option = "投票放棄"

    public_message = f"**投票終了:** {vote_data['topic']}\n最も票を集めたのは: {most_voted_option}"

    detailed_result_message = result_message
    for choice, count in vote_data["votes"].items():
        detailed_result_message += f"{choice}: {count}票\n"

    await interaction.channel.send(public_message) 

    try:
        await interaction.user.send(detailed_result_message)
    except discord.errors.Forbidden:
        await interaction.response.send_message("結果を送信できませんでした。DMが無効になっている可能性があります。", ephemeral=True)
    
    vote_data = {}
@bot.tree.command(name="genshin", description="テストです。")
async def genshin_info(interaction: discord.Interaction, uid: int):
    await interaction.response.defer()
    """
    原神のユーザー情報を表示します。

    Args:
        uid: 検索したいユーザーのUID
    """

    try:
        # enka.network APIを呼び出す
        response = requests.get(f"https://enka.network/api/uid/{uid}?info")  
        response.raise_for_status()
        data = response.json()

        # APIのレスポンスから必要な情報を取得
        player_info = data.get("playerInfo", {})
        character_ids = [c['avatarId'] for c in data.get('avatarInfoList', [])]

        # キャラクター名を取得
        character_names = []
        for char_id in character_ids:
            char_data = next((c for c in player_info.get('showAvatarInfoList', []) if c['avatarId'] == char_id), None)
            if char_data:
                character_names.append(char_data.get('avatarName', '不明なキャラクター'))

        # Discordにメッセージを送信
        nickname = player_info.get('nickname', '不明なユーザー')
        level = player_info.get('level', '不明')
        world_level = player_info.get('worldLevel', '不明')
        signature = player_info.get('signature', 'なし')
        
        message = f"""
        **原神ユーザー情報**

        **ニックネーム:** {nickname}
        **UID:** {uid}
        **冒険ランク:** {level}
        **世界ランク:** {world_level}
        **紹介文:** {signature}
        **キャラクター:** {', '.join(character_names)}
        """

        await interaction.followup.send(message)

    except requests.exceptions.RequestException as e:
        await interaction.followup.send(f"エラーが発生しました: {e}")


@bot.tree.command(name="tr", description="Fortnite Trackerのプロフィールスクショを取得")
@discord.app_commands.describe(username="ユーザー名")
async def tr(interaction: discord.Interaction, username: str):  # ctx を interaction に変更

    await interaction.response.defer()

    try:
        # Chrome WebDriverをheadlessモードで起動
        options = Options()
        options.add_argument('--headless=new')
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

        url = f"https://fortnitetracker.com/profile/all/{username}"
        driver.get(url)

   
        driver.set_window_size(1936, 1048)


        total_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, 694)")

        # スクリーンショットを保存
        filepath = f"F:\\fnbot\\{username}_profile_screenshot.png"  # cogsフォルダを削除
        driver.save_screenshot(filepath)

        # ブラウザを閉じる
        driver.quit()

        # スクリーンショットをDiscordに送信
        with open(filepath, "rb") as f:
            picture = discord.File(f)
            await interaction.followup.send(file=picture)  # interaction.followup.send を使用

    except FileNotFoundError:
        await interaction.followup.send("ファイルが見つかりませんでした。パスを確認してください。")
    except discord.Forbidden:
        await interaction.followup.send("ファイルを送信する権限がありません。")
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {e}")

@bot.tree.command(name="setthing", description="botの細かな設定ができます。")
@app_commands.choices(
    setting_name=[
        app_commands.Choice(name="link", value="link")
    ]
)
async def setting_command(interaction: discord.Interaction, setting_name: str, value: str):
    if setting_name == "link":
        if value in ["true", "false"]:
            try:
                await settings_collection.update_one(
                    {"guild_id": interaction.guild.id},
                    {"$set": {setting_name: value == "true"}},
                    upsert=True
                )
                await interaction.response.send_message(f"リンク展開の設定を {value} に変更しました。")
            except Exception as e:
                await interaction.response.send_message(f"設定の変更中にエラーが発生しました: {e}")
        else:
            await interaction.response.send_message("設定値は 'true' または 'false' で指定してください。")
    else:
        await interaction.response.send_message("無効な設定名です。")


bot.run("")
