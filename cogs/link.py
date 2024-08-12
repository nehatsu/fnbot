import discord
from discord.ext import commands

class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.server_id = 1076842891705602138  # 監視したいサーバーID
        self.channel_id = 1237650977939652689  # 通知を送りたいチャンネルID

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        if invite.guild.id == self.server_id:
            channel = self.bot.get_channel(self.channel_id)
            await channel.send(f'{invite.inviter} が新しい招待リンクを作成しました。リンク: ||{invite.url}||')


async def setup(bot):
    await bot.add_cog(InviteTracker(bot))