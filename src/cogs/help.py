import discord
from discord.ext import commands
from discord.ext.commands import Context

from LichessBot import LichessBot


class Help(commands.Cog):
    def __init__(self, client: LichessBot):
        self.client = client

    @commands.command(name="help", aliases=["commands"])
    async def help_menu(self, context: Context):
        """
        Help command, show support server and command usage.
        @param context: ~Context: The context of the command
        @return:
        """
        embed = discord.Embed(title=f"Commands", colour=0x000000)
        embed.add_field(name=f":question: Support", value=f"For help, issues or suggestions, join the "
                                                          f"[bot support server](https://discord.gg/KdpvMD72CV).",
                        inline=False)
        embed.add_field(name=f":face_with_monocle: About",
                        value=f"`{self.client.config.prefix}about` →  Show information about this bot",
                        inline=False)
        embed.add_field(name=":link: (Dis)connect your Lichess account",
                        value=f"`{self.client.config.prefix}connect [lichess username]` → connect your Discord "
                              f"profile with your Lichess account.\n"
                              f"`{self.client.config.prefix}disconnect` → disconnect your Discord profile from a "
                              f"connected Lichess account",
                        inline=False)
        embed.add_field(name=f":chart_with_upwards_trend: Rating",
                        value=f"`{self.client.config.prefix}rating [username]` →  show all chess ratings. When "
                              f"connected with `{self.client.config.prefix}connect` you can use this command without "
                              f"giving a username.\n`{self.client.config.prefix}rating [username] [gamemode]` →  show "
                              f"rating for a particular gamemode", inline=False)
        embed.add_field(name=f":jigsaw: Puzzle",
                        value=f"`{self.client.config.prefix}puzzle` →  show a random lichess puzzle, or one near your "
                              f"puzzle rating if your Lichess account is connected using "
                              f"`{self.client.config.prefix}connect`\n`{self.client.config.prefix}puzzle [puzzle_id]` "
                              f"→  show a particular lichess puzzle\n`{self.client.config.prefix}puzzle "
                              f"[rating1]-[rating2]` →  show a random puzzle with a rating between rating1 and rating2",
                        inline=False)
        embed.add_field(name=":white_check_mark: Answering puzzles",
                        value=f"`{self.client.config.prefix}answer [move]` →  give your answer to the most recent "
                              f"puzzle. Use the standard algebraic notation like *Qxb7+* or UCI like *a1b2*. You can "
                              f"give your answer in spoiler tags like this: `{self.client.config.prefix}answer "
                              f"||move||`\n`{self.client.config.prefix}bestmove` →  get the best move to play in the "
                              f"previous puzzle, you can continue the puzzle from the next move.", inline=False)
        embed.add_field(name=":man_raising_hand: Profile",
                        value=f"`{self.client.config.prefix}profile [username]` →  show a lichess user profile. When "
                              f"connected with `{self.client.config.prefix}connect` you can use this command without "
                              f"giving a username.",
                        inline=False)

        await context.send(embed=embed)

    @commands.command(name="about")
    async def about(self, context):
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
                              f"[this link](https://discord.com/oauth2/authorize?client_id=707287095911120968"
                              f"&permissions=52224&scope=bot). "
                              f"Check out what I can do using `{self.client.config.prefix}commands`. "
                              f"Any issues or suggestions can be posted in the "
                              f"[bot support discord server](https://discord.gg/KdpvMD72CV).")

        await context.send(embed=embed)


def setup(client: LichessBot):
    client.add_cog(Help(client))
    client.logger.info("Sucessfully added cog: Help")
