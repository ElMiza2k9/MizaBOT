# MizaBOT  
* [Granblue Fantasy](http://game.granbluefantasy.jp) Discord Bot used by the /gbfg/ server.  
#### Requirements  
* Python 3.7.  
* [discord.py](https://github.com/Rapptz/discord.py) (formerly the rewrite branch).  
* [PyDrive](https://pythonhosted.org/PyDrive/) to access the google drive where the save file is stored.  
* [psutil](https://psutil.readthedocs.io/en/latest/) is only used to get CPU and memory usage.  
* `pip install -r requirements.txt` to install all the modules.  
### Usage  
* The bot is designed to be used on [Heroku](https://www.heroku.com).  
* Do a git push to your [Heroku](https://www.heroku.com) app but don't expect it to work right away.  
* You need to setup a few files (config.json, save.json, credentials.json and more...)  
### Examples  
* Check the [example](https://github.com/MizaGBF/MizaBOT/tree/master/example) folder for minimal config and save files.  
* `credentials.json` needs to be generated by yourself before using it on [Heroku](https://www.heroku.com).  
* Example files might be a bit outdated. I'll do my best to update them as much as possible.  
### Details  
Random explanations:  
* A custom loop is used instead of the regular bot loop, to handle possible exceptions or crashes, check `mainLoop()` in [bot.py](https://github.com/MizaGBF/MizaBOT/blob/master/bot.py) for details.  
* The `GracefulExit` is needed for a proper use on [Heroku](https://www.heroku.com). A `SIGTERM` signal is sent when a restart happens on the [Heroku](https://www.heroku.com) side (every 24 hours, when you push a change or in some other cases).  
* [asyncio](https://docs.python.org/3/library/asyncio.html) is used by [discord.py](https://github.com/Rapptz/discord.py), there is no multithreading involved in this bot as a result.  
* [Heroku](https://www.heroku.com) apps have no persistent storage, [PyDrive](https://pypi.org/project/PyDrive/) is used to read and write save files to my google drive.  
* `baguette.py` is a black box and won't ever be on this github, but the bot can run without.  
* The debug channel refers to a channel, in my test server, where the bot send debug and error messages while running. Useful when I can't check the logs.  
### Version 5.0 Details  
The 5.0 version is a major rewrite of the bot.  
Here's what changed:  
* The [Bot instance](https://github.com/MizaGBF/MizaBOT/blob/master/bot.py) is now an override of the Discord Bot class.  
* All the data is centralized on the Bot instance and accessible by the Cogs.  
* Cogs are separated from the main file, in the [cogs folder](https://github.com/MizaGBF/MizaBOT/tree/master/cogs) folder.  
* The data serialization has been fixed when loading/saving. Now, integers are integers and dates are dates.  
* Cogs can run their own task easily.  
* [aiohttp](https://github.com/aio-libs/aiohttp) is now used for HTTP requests, to stay coherent with the use of asyncio.  