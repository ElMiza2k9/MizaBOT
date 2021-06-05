# MizaBOT  
* [Granblue Fantasy](http://game.granbluefantasy.jp) Discord Bot.  
* Command List available [Here](https://mizagbf.github.io/MizaBOT/index.html).  
### Requirements  
* Python 3.9.  
* [discord.py](https://github.com/Rapptz/discord.py) (formerly the rewrite branch).  
* [PyDrive2](https://github.com/iterative/PyDrive2) to access the google drive where the save file is stored.  
* [psutil](https://psutil.readthedocs.io/en/latest/).  
* [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/).  
* [Tweepy](https://github.com/tweepy/tweepy).  
* [Pillow](https://pillow.readthedocs.io/en/stable/).  
* [leather](https://pypi.org/project/leather/).  
* [CairoSVG](https://pypi.org/project/CairoSVG/).  
* `pip install -r requirements.txt` to install all the modules.  
### Version 8.0  
A few things changed in the 8.0 version:  
* The main `bot.py` file, along with some cogs, are now split in multiple [components](https://github.com/MizaGBF/MizaBOT/tree/master/components) to simplify future developments.  
* Better multithreading support, with the use of Lock and some tricks to speedup the bot overall.  
* Some improvements and bug fixes in the existing command list.  

This version is currently in Beta.
More changes and improvements will come once discord.py 2.0 get released.
### Setup  
The bot is designed to be used on [Heroku](https://www.heroku.com).  
Here are a few instructions to set it up in its current state:  
* On the [Heroku](https://www.heroku.com) side, you only need to create a new app. The [CLI](https://devcenter.heroku.com/articles/heroku-cli) might help if you intend to do a git push since your own computer.   
* The bot uses [Google Drive](https://www.google.com/drive/) to read and save its data. You'll need to get API keys from [Google](https://developers.google.com/drive) and fill the `settings.yaml` you can find in the [example folder](https://github.com/MizaGBF/MizaBOT/tree/master/example).  
* Finally, you also need your [Discord token](https://discordapp.com/developers/applications/).  
* On the [bot application page](https://discord.com/developers/applications), you want to enable the *PRESENCE INTENT* and *SERVER MEMBERS INTENT* settings for a better experience. [See here](https://discordpy.readthedocs.io/en/latest/intents.html#privileged-intents).  
* Other files in the [example folder](https://github.com/MizaGBF/MizaBOT/tree/master/example) are:  
* `config.json` must be edited with a notepad (follow the instructions inside) and placed with the bot code (your discord token must be inserted inside).  
* `save.json` can be used as it is and must be placed in the [Google Drive](https://www.google.com/drive/) folder used to save the bot data. The bot can't start without a valid save file, it will create one if needed.  
* (Optional) Twitter credentials can be used to enhance some features. Requires a developper account.  
Check the [wiki](https://github.com/MizaGBF/MizaBOT/wiki/Setup) for details.  
This [issue](https://github.com/MizaGBF/MizaBOT/issues/1) might help if you encounter a problem.  
Example files might be a bit outdated. I'll do my best to update them as much as possible.  
### Code Overview  
* All data (from the config and save files) are centralized in the Data component and accessible by the Bot, Cogs or other Components at any time.  
* The `pending` flag of the Data component is checked every 10 minutes in the `status()` task and save to the Google Drive if True.  
* A "Graceful Exit" is needed for a proper use on [Heroku](https://www.heroku.com). A `SIGTERM` signal is sent when a restart happens on the [Heroku](https://www.heroku.com) side (usually every 24 hours, when you push a change or in some other cases). If needed, the bot also saves when this happens.  
Check the `exit_gracefully()` function for details.  
* During the boot, all the .py files in the cogs folder are tested to find valid cogs.  
* The `debug` channel refers to a channel, in my test server, where the bot send debug and error messages while running. Useful when I can't check the logs on Heroku.  
### User Overview  
* The default command prefix is `$`. It can be changed using the `$setPrefix <your new prefix>` command.  
* `$help` lists all the commands usable in your current channel with your current permissions.
When asking for a Cog command list, it's sent to your private messages. Check your privacy settings if the bot can't send you a direct message.
![Privacy example](https://cdn.discordapp.com/attachments/614716155646705676/643427911063568426/read02.png)
* A bot sees an user with the manage messages permission as a server moderator, in the channel where the command is invoked. So, be careful with this.  
* If you don't want to put the bot in quarantine in a single channel, you can disable the most "annoying" commands using `$toggleFullBot` in the concerned channel. `$allowBotEverywhere` lets you reset everything, while `$seeBotPermission` shows you all the allowed channels.  
![Command example](https://cdn.discordapp.com/attachments/614716155646705676/643427915526045696/read03.png)
* `$toggleBroadcast` and `$seeBroadcast` works the same. If the bot owner needs to send a message to all servers, those channels will receive the message.  
* Servers need to be approved before the bot can be used in it. The owner must use the `$accept <server id>` or `$refuse <server id>` commands. `$ban_server <server id>` or `$ban_owner <owner id>` can be used to forbid someone to add the bot to a server. The owner's 'debug server' registered in `config.json` can bypass those restrictions.  
* The [Granblue Fantasy](http://game.granbluefantasy.jp) Schedule must be manually set using `$setschedule`. The syntax is the following: `$setschedule date of event 1;name of event 1; etc.... ; date of event N; name of event N`. The previous command can be retrieved using `$schedule raw`.  
Alternatively, if Twitter is enabled, it can be retrieved from [@granblue_en](https://twitter.com/Granblue_en) with the `$getschedule` command. An automatic attempt will also happen at the start of each month by the `clean` task.  
![Schedule example](https://cdn.discordapp.com/attachments/614716155646705676/643427910874693642/read01.png)
* For details on everything else, I recommend the `$help` command.  
