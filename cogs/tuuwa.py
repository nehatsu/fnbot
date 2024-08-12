import discord
from discord.ext import commands
from discord.ui import Button, View
from collections import defaultdict
from datetime import datetime
import json
import os
import matplotlib
matplotlib.use('Agg')  # これを追加
import matplotlib.pyplot as plt
import japanize_matplotlib  # これを追加
from discord import app_commands

class CallRecord(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        guild_id = member.guild.id
        guild_data_file = f'call_data_{guild_id}.json'

        # 通話に参加
        if before.channel is None and after.channel is not None:
            self.voice_states[member.id] = datetime.now()

        # 通話から退出
        elif before.channel is not None and after.channel is None:
            if member.id in self.voice_states:
                duration = datetime.now() - self.voice_states.pop(member.id)
                self._update_call_duration(guild_id, member.id, duration.total_seconds())

        # 通話チャンネル変更
        elif before.channel is not None and after.channel is not None:
            if member.id in self.voice_states:
                duration = datetime.now() - self.voice_states[member.id]
                self._update_call_duration(guild_id, member.id, duration.total_seconds())
                self.voice_states[member.id] = datetime.now()

    def _update_call_duration(self, guild_id, user_id, duration):
        guild_data_file = f'call_data_{guild_id}.json'

        # JSONファイルが存在しない場合は空の辞書を作成
        if not os.path.exists(guild_data_file):
            call_durations = {}
        else:
            with open(guild_data_file, 'r') as f:
                call_durations = json.load(f)

        if str(user_id) not in call_durations:
            call_durations[str(user_id)] = 0

        call_durations[str(user_id)] += int(duration)

        with open(guild_data_file, 'w') as f:
            json.dump(call_durations, f)

    @commands.hybrid_command(name="rtwa", description="通話時間のデータを昇順のランク形式で表示します。")
    async def calltime(self, ctx):
        guild_id = ctx.guild.id
        guild_data_file = f'call_data_{guild_id}.json'

        if not os.path.exists(guild_data_file):
            await ctx.send("通話記録がありません。")
            return

        with open(guild_data_file, 'r') as f:
            call_durations = json.load(f)

        sorted_data = sorted(call_durations.items(), key=lambda x: x[1], reverse=True)  # 降順に修正

        embed = discord.Embed(title="通話時間ランキング", color=discord.Color.blue())
        for user_id, duration in sorted_data[:10]:  # 上位10人だけを表示
            user = self.bot.get_user(int(user_id))
            if user is None or user.bot:  # userがNoneの場合もスキップ
                continue
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            if hours > 0:
                embed.add_field(name=user.display_name, value=f"{hours}時間 {minutes}分", inline=False)  # user.nameからuser.display_nameに変更
            else:
                embed.add_field(name=user.display_name, value=f"{minutes}分", inline=False)  # user.nameからuser.display_nameに変更

        await ctx.send(embed=embed,view=ButtonView(self.bot))
        
    @commands.hybrid_command(name="ktwa", description="指定したユーザーの通話時間を確認することができます。")
    @discord.app_commands.describe(member="ユーザーを指定しましょう。")
    async def user(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author
        
        guild_id = ctx.guild.id
        guild_data_file = f'call_data_{guild_id}.json'

        if not os.path.exists(guild_data_file):
            await ctx.send(f"{member.display_name}の通話記録はありません。")
            return

        with open(guild_data_file, 'r') as f:
            call_durations = json.load(f)

        user_id = str(member.id)
        if user_id not in call_durations:
            await ctx.send(f"{member.display_name}の通話記録はありません。")
            return

        duration = call_durations[user_id]
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        if hours > 0:
            await ctx.send(f"{member.display_name}の通話時間: {hours}時間 {minutes}分")
        else:
            await ctx.send(f"{member.display_name}の通話時間: {minutes}分")

async def setup(bot):
    await bot.add_cog(CallRecord(bot))

class ButtonView(discord.ui.View):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @discord.ui.button(label="グラフを表示する。", style=discord.ButtonStyle.green)
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            guild_id = interaction.guild.id
            guild_data_file = f'call_data_{guild_id}.json'

            if not os.path.exists(guild_data_file):
                await interaction.response.send_message("通話記録がありません。")
                return

            with open(guild_data_file, 'r') as f:
                call_durations = json.load(f)

            sorted_data = sorted(call_durations.items(), key=lambda x: x[1], reverse=True)[:10]  # 上位10人だけを取得

            user_names = []
            durations = []
            for user_id, duration in sorted_data:
                user = self.bot.get_user(int(user_id))
                if user is None or user.bot:
                    continue
                user_names.append(user.display_name)
                durations.append(duration // 3600)  # 秒から時間に変換

            plt.figure(figsize=(10, 6))
            bars = plt.bar(user_names, durations, color='skyblue')
            plt.xlabel('ユーザー名')
            plt.ylabel('通\n話\n時\n間', labelpad=15, size=15, rotation=360)  # 横文字から縦文字に変更
            plt.title('ユーザーの通話時間上位10位')
            plt.xticks(rotation=45)
            plt.tight_layout()

    # データラベルを追加
            for bar, duration in zip(bars, durations):
                plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f'{duration}時間', ha='center', va='bottom')

            file_name = 'top_10_calltime.png'
            plt.savefig(file_name)
            plt.close()
            try:

                with open(file_name, 'rb') as file:
                    picture = discord.File(file)
                    await interaction.response.send_message(file=picture)
            
                os.remove(file_name)

            except Exception as e:
                await interaction.response.send_message(f"エラーが発生しました: {e}")    


