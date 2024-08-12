from discord.ext import commands
import discord
import asyncio
import glob
import os
import traceback

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.voice_states = True

class MyBot(commands.Bot):
    async def setup_hook(self):
        # "cogs"ディレクトリ内のPythonファイルを対象にする
        for filepath in glob.glob(os.path.join("cogs", "*.py")):
            if os.path.basename(filepath) == "__init__.py":  # __init__.pyは除外
                continue

            # ファイルパスからCogの名前を生成（例: "cogs.hello"）
            cog = filepath.replace(os.sep, ".").replace(".py", "")
            try:
                await self.load_extension(cog)
                print(f"{cog}を読み込みました。")
            except Exception as e:
                print(f"{cog}の読み込みに失敗しました: {e}")
                traceback.print_exc()  # エラーの詳細を出力

        # 全てのコマンドをグローバルに同期
        await self.tree.sync(guild=None)

        guild_ids = [1103936224563036272] # すぐに同期したいサーバーのIDを入れる
        for guild_id in guild_ids:
            guild = self.get_guild(guild_id)
            if guild:
                try:
                    await self.tree.sync(guild=guild)
                except discord.errors.Forbidden:
                    print(f"サーバーID:{guild_id}に登録できませんでした。")
            else:
                print(f"サーバーID:{guild_id}が見つかりません。")



# MyBot クラスを使用して bot インスタンスを作成
bot = MyBot(command_prefix='!m', intents=intents, heartbeat_timeout=60, case_insensitive=True)

async def main():
    # Bot のセットアップやイベントループの処理
    try:
        await bot.start('')  # 'YOUR_TOKEN_HERE'を適切なトークンに置き換えてください
    finally:
        await bot.close()

if __name__ == '__main__':
    asyncio.run(main())
