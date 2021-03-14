import discord
from discord import Message
from discord.ext import commands
from discord.ext.commands import Context

from LichessBot import LichessBot


class Help(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.content.lower().strip() == self.client.config.universal_prefix:
            await self.help_menu(Context(message=message, guild=message.guild, prefix=self.client.prefix(message)))

    @commands.command(name="help", aliases=["commands"])
    async def help_menu(self, context: Context):
        """
        Help command, show support server and command usage.
        @param context: ~Context: The context of the command
        @return:
        """
        prefix = self.client.prfx(context)
        embed = discord.Embed(title=f"Help", colour=0x000000)
        embed.add_field(name=f":question: Support", value=f"For help, issues or suggestions, join the "
                                                          f"[bot support server](https://discord.gg/KdpvMD72CV).",
                        inline=False)
        embed.add_field(name=f":pencil: Command prefix (currently `{prefix}`)",
                        value=f"`{prefix}lichessprefix [new prefix]` → Change the command prefix "
                              f"(administrator only)", inline=False)
        embed.add_field(name=f":face_with_monocle: About",
                        value=f"`{prefix}about` →  Show information about this bot",
                        inline=False)
        embed.add_field(name=":link: (Dis)connect your Lichess account",
                        value=f"`{prefix}connect [lichess username]` → connect your Discord "
                              f"profile with your Lichess account.\n"
                              f"`{prefix}disconnect` → disconnect your Discord profile from a "
                              f"connected Lichess account",
                        inline=False)
        embed.add_field(name=f":chart_with_upwards_trend: Rating",
                        value=f"`{prefix}rating [username]` →  show all chess ratings. When "
                              f"connected with `{prefix}connect` you can use this command without "
                              f"giving a username.\n`{prefix}rating [username] [gamemode]` →  show "
                              f"rating for a particular gamemode", inline=False)
        embed.add_field(name=f":jigsaw: Puzzle",
                        value=f"`{prefix}puzzle` →  show a random lichess puzzle, or one near your "
                              f"puzzle rating if your Lichess account is connected using "
                              f"`{prefix}connect`\n`{prefix}puzzle [puzzle_id]` "
                              f"→  show a particular lichess puzzle\n`{prefix}puzzle "
                              f"[rating1]-[rating2]` →  show a random puzzle with a rating between rating1 and rating2",
                        inline=False)
        embed.add_field(name=":white_check_mark: Answering puzzles",
                        value=f"`{prefix}answer [move]` / `{prefix}a [move]` →  give your answer to the most recent "
                              f"puzzle. Use the standard algebraic notation like *Qxb7+* or UCI like *a1b2*. You can "
                              f"give your answer in spoiler tags like this: `{prefix}answer "
                              f"||move||`\n`{prefix}bestmove` →  get the best move to play in the "
                              f"previous puzzle, you can continue the puzzle from the next move.", inline=False)
        embed.add_field(name=":man_raising_hand: Profile",
                        value=f"`{prefix}profile [username]` →  show a lichess user profile. When "
                              f"connected with `{prefix}connect` you can use this command without "
                              f"giving a username.",
                        inline=False)

        await context.send(embed=embed)

    @commands.command(name="about")
    async def about(self, context: Context):
        """
        Command to show information about this bot.
        @param context: ~Context: The context of the command
        @return:
        """
        embed = discord.Embed(title=f"Lichess Discord bot", colour=0x000000,
                              url="https://github.com/tvdhout/Lichess-discord-bot")
        embed.set_footer(text="Made by Thijs#9356",
                         icon_url="https://cdn.discordapp.com/avatars/289163010835087360"
                                  "/f7874fb1b63d84359307b8736f559355.webp?size=128")
        embed.add_field(name="About me",
                        value=f"I am a bot that can show Lichess puzzles for you to solve right here in the channel. "
                              f"I can also obtain various lichess-related pieces of information for you. You can see "
                              f"how I work [on the GitHub page](https://github.com/tvdhout/Lichess-discord-bot). "
                              f"You can invite me to your own server using "
                              f"[this link](https://discord.com/api/oauth2/authorize?client_id=707287095911120968"
                              f"&permissions=116800&scope=bot). "
                              f"Check out what I can do using `{self.client.prfx(context)}commands`. "
                              f"Any issues or suggestions can be posted in the "
                              f"[bot support discord server](https://discord.gg/KdpvMD72CV).")

        await context.send(embed=embed)

    @commands.command(name="lichessprefix")
    @commands.guild_only()
    async def change_prefix(self, context: Context):
        if not context.author.guild_permissions.administrator:  # Command issuer is not an administrator
            embed = discord.Embed(title="No permission!", colour=0xff0000)
            embed.add_field(name=":-(", value="You need to be a server administrator to change the command prefix.")
            await context.send(embed=embed)
            return

        content = context.message.content.split()
        embed = discord.Embed(title="Bot command prefix", colour=0xFF69B4)
        if len(content) == 1 or len(content[1]) > 10:
            embed.add_field(name="lichessprefix command:",
                            value=f"Change the command prefix using this command with your new command prefix, "
                                  f"e.g. `{self.client.prfx(context)}lichessprefix $` to change the prefix to `$`.\n"
                                  f"Constraints: max 10 characters, no spaces. I will always respond to "
                                  f"`{self.client.config.universal_prefix}` in case forget your current prefix.")
            await context.send(embed=embed)
            return
        prefix = content[1]
        self.client.prefixes[str(context.guild.id)] = prefix

        embed.add_field(name="Prefix changed succesfully!",
                        value=f"My command prefix is now `{prefix}`. I will always respond to "
                              f"`{self.client.config.universal_prefix}` in case forget your current prefix.")
        await context.send(embed=embed)

        cursor = self.client.connection.cursor(buffered=True)
        query = "INSERT INTO prefixes (guildId, prefix) VALUES (%s, %s) " \
                "ON DUPLICATE KEY UPDATE prefix = VALUES(prefix)"
        query_data = (str(context.guild.id), prefix)
        cursor.execute(query, query_data)
        self.client.connection.commit()
        cursor.close()


def setup(client: LichessBot):
    client.add_cog(Help(client))
    client.logger.info("Sucessfully added cog: Help")
