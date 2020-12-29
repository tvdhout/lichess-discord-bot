# Lichess discord bot

[![Bot status widget](https://top.gg/api/widget/status/707287095911120968.svg)](https://top.gg/bot/707287095911120968)

[Click here to invite the bot to your server!](https://discord.com/api/oauth2/authorize?client_id=707287095911120968&permissions=52224&scope=bot)

## DESCRIPTION
This bot integrates with the lichess.org chess website. The bot can be used to retrieve ELO rankings for users, query chess puzzles (random / specific / random within a rating range) and more in the making! Any further ideas can be requested as an issue on the GitHub page.

## PREFIX
\-

## COMMANDS 
* `-help` or `-commands` --> show list of commands
* `-about` --> show information about the bot
* `-rating [username | user url]` --> retrieve all ratings and average rating for a user
* `-rating [username | user url] [gamemode]` --> retrieve the ratings for a user for a specific gamemode
* `-puzzle` --> show a random chess puzzle
* `-puzzle [id]` --> show a specific chess puzzle
* `-puzzle [rating1]-[rating2]` --> show a random chess puzzle with a difficulty rating in a range
* `-answer [move]` --> give an answer to the most recent puzzle shown in the channel
* `-bestmove` --> ask for the answer for the most recent puzzle shown in the channel. If there are more steps to the puzzle, the user can continue from the next step
* `-profile [username]` --> to get public profile information

## Help / Contact / Issues / Requests / Collaboration
Questions, issues and requests can be posted as an issue in this repository, or posted in the [discord support server](https://discord.gg/xCpCRsp)

## Screenshots
![Puzzle command screenshot](/media/puzzle_example.png)

![Answer command screenshot](/media/bestmove_example.png)

![Rating command screenshot](/media/rating_example.png)

![Profile command screenshot](/media/profile_example.png)

![Help command screenshot](/media/help_example.png)

