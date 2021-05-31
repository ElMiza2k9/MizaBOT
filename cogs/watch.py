import discord
from discord.ext import commands
import asyncio
import concurrent.futures
from PIL import Image, ImageFont, ImageDraw
from datetime import datetime, timedelta
import time
from bs4 import BeautifulSoup
import threading

# ----------------------------------------------------------------------------------------------------------------
# Watch Cog
# ----------------------------------------------------------------------------------------------------------------
# Those commands aren't intended for humans
# ----------------------------------------------------------------------------------------------------------------

class Watch(commands.Cog):
    """Special commands."""
    def __init__(self, bot):
        self.bot = bot
        self.color = 0xa62216
        self.tcache = []
        self.tlock = threading.Lock()

    def startTasks(self):
        self.bot.runTask('watch', self.watch)

    async def watch(self): # watch GBF state
        self.bot.channel.setMultiple([['private_update', 'you_private'], ['public_update', 'you_general'], ['gbfg_update', 'gbfg_general']])
        while True:
            if not self.bot.running: return

            try: # maintenance check
                await asyncio.sleep(60) # loop sleep
                r = await self.bot.do(self._checkMaintenance)
                if r > 0:
                    if r == 2:
                        await self.bot.send('debug', embed=self.bot.util.embed(title="Maintenance check", description="Maintenance detected" , color=self.color))
                        await asyncio.sleep(100)
                    continue
            except asyncio.CancelledError:
                await self.bot.sendError('gbfwatch', 'cancelled')
                return
            except Exception as e:
                await self.bot.sendError('gbfwatch Maintenance', e)

            try: # account refresh
                res = await self.bot.do(self._refresh)
                for i in res:
                    await self.bot.send('debug', embed=self.bot.util.embed(title="Account refresh", description="Account #{} is down".format(i) , color=self.color))
            except asyncio.CancelledError:
                await self.bot.sendError('gbfwatch', 'cancelled')
                return
            except Exception as e:
                await self.bot.sendError('gbfwatch Account', e)

            try: # news checker
                news = await self.bot.do(self.checkNews)
                for n in news:
                    await self.bot.sendMulti(['debug', 'public_update', 'gbfg_update'], embed=self.bot.util.embed(author={'name':"Granblue Fantasy News", 'icon_url':"http://game-a.granbluefantasy.jp/assets_en/img/sp/touch_icon.png"}, description="[{}]({})".format(n[1], n[0]), image=n[2], color=self.color))
            except asyncio.CancelledError:
                await self.bot.sendError('gbfwatch', 'cancelled')
                return
            except Exception as e:
                await self.bot.sendError('gbfwatch News', e)

            # check if it's possible to continue
            try:
                if self.bot.data.save['gbfaccounts'][self.bot.data.save['gbfcurrent']][3] == 2:
                    raise Exception()
            except asyncio.CancelledError:
                await self.bot.sendError('gbfwatch', 'cancelled')
                return
            except:
                continue

            try: # 4koma checker
                title, last = await self.bot.do(self.check4koma)
                if last is not None:
                    await self.bot.sendMulti(['debug', 'public_update', 'gbfg_update'], embed=self.bot.util.embed(title=title, url="http://game-a1.granbluefantasy.jp/assets/img/sp/assets/comic/episode/episode_{}.jpg".format(last['id']), image="http://game-a1.granbluefantasy.jp/assets/img/sp/assets/comic/thumbnail/thum_{}.png".format(last['id'].zfill(5)), color=self.color))
            except asyncio.CancelledError:
                await self.bot.sendError('gbfwatch', 'cancelled')
                return
            except Exception as e:
                await self.bot.sendError('gbfwatch 4koma', e)

            try: # update check
                v = await self.bot.do(self.bot.gbf.version)
                s = self.bot.gbf.updateVersion(v)
                if s == 3:
                    react = await self.bot.sendMulti(['debug_update', 'private_update'], embed=self.bot.util.embed(author={'name':"Granblue Fantasy", 'icon_url':"http://game-a.granbluefantasy.jp/assets_en/img/sp/touch_icon.png"}, description="Game version updated to `{}` (`{}`)".format(v, self.bot.gbf.version2str(v)), color=self.color))
                    try:
                        for r in react: await self.bot.util.react(r, 'time')
                    except:
                        pass
                    msg = ""
                    thumb = ""
                    tk = await self.bot.do(self.ut)
                    if len(tk) > 0:
                        msg += "**Gacha update**\n{} new ticket\n".format(len(tk))
                        thumb = tk[0]
                        if len(tk) > 1:
                            msg += "Other Ticket(s):\n"
                            for i in range(1, len(tk)):
                                msg += "[{}]({})\n".format(tk[i].split('/')[-1], tk[i])
                        msg += "\n"
                    ch = self.bot.get_channel(self.bot.data.config['ids']['debug_update'])
                    cu = await self.cc(ch)
                    try:
                        for r in react: await self.bot.util.unreact(r, 'time')
                    except:
                        pass
                    if len(cu) > 0:
                        msg += "**Content update**\n"
                        for k in cu:
                            msg += "{} {}\n".format(cu[k], k)
                    if msg != "":
                        await self.bot.sendMulti(['debug_update', 'private_update'], embed=self.bot.util.embed(title="Latest Update", description=msg, thumbnail=thumb, color=self.color))
                        await self.bot.send('debug_update', embed=self.bot.util.embed(title="Reminder", description="Keep it private", color=self.color))
                elif s == 2:
                    await self.bot.send('debug_update', embed=self.bot.util.embed(author={'name':"Granblue Fantasy", 'icon_url':"http://game-a.granbluefantasy.jp/assets_en/img/sp/touch_icon.png"}, description="Game version set to `{}` (`{}`)".format(v, self.bot.gbf.version2str(v)) , color=self.color))
            except asyncio.CancelledError:
                await self.bot.sendError('gbfwatch', 'cancelled')
                return
            except Exception as e:
                await self.bot.sendError('gbfwatch Update', e)

    def _checkMaintenance(self):
        maintenance_time = self.bot.util.JST()
        if not self.bot.gbf.isAvailable():
            if self.bot.data.save['maintenance']['state'] == True:
                if self.bot.data.save['maintenance']['duration'] > 0:
                    m_end = self.bot.data.save['maintenance']['time'] + timedelta(seconds=3600*self.bot.data.save['maintenance']['duration'])
                    current_time = self.bot.util.JST()
                    if current_time >= m_end:
                        time.sleep(30)
                    else:
                        d = m_end - current_time
                        time.sleep(d.seconds+1)
            else:
                if self.bot.util.JST() - maintenance_time >= timedelta(seconds=500):
                    with self.bot.data.lock:
                        self.bot.data.save['maintenance']["state"] = True
                        self.bot.data.save['maintenance']["duration"] = 0
                        self.bot.data.pending = True
                    return 2
            return 1
        else:
            if self.bot.data.save['maintenance']['state'] == True and (self.bot.data.save['maintenance']['duration'] == 0 or (self.bot.util.JST() > self.bot.data.save['maintenance']['time'] + timedelta(seconds=3600*self.bot.data.save['maintenance']['duration']))):
                with self.bot.data.lock:
                    self.bot.data.save['maintenance'] = {"state" : False, "time" : None, "duration" : 0}
                    self.bot.data.pending = True
        return 0

    def _refresh(self):
        res = []
        if 'test' in self.bot.data.save['gbfdata']:
            current_time = self.bot.util.JST()
            for i in range(0, len(self.bot.data.save['gbfaccounts'])):
                acc = self.bot.data.save['gbfaccounts'][i]
                if acc[3] == 0 or (acc[3] == 1 and (acc[5] is None or current_time - acc[5] >= timedelta(seconds=7200))):
                    r = self.bot.gbf.request(self.bot.data.config['gbfwatch']['test'], account=i, decompress=True, load_json=True, check=True, force_down=True)
                    with self.bot.data.lock:
                        if r is None or str(r.get('user_id', None)) != str(acc[0]):
                            res.append(i)
                            self.bot.data.save['gbfaccounts'][i][3] = 2
                        elif r == "Maintenance":
                            break
                        else:
                            self.bot.data.save['gbfaccounts'][i][3] = 1
                            self.bot.data.save['gbfaccounts'][i][5] = current_time
                        self.bot.data.pending = True
        return res

    def checkNews(self):
        res = []
        ret = []
        data = self.bot.gbf.request("https://granbluefantasy.jp/news/index.php", no_base_headers=True)
        if data is not None:
            soup = BeautifulSoup(data, 'html.parser')
            at = soup.find_all("article", class_="scroll_show_box")
            try:
                for a in at:
                    inner = a.findChildren("div", class_="inner", recursive=False)[0]
                    section = inner.findChildren("section", class_="content", recursive=False)[0]
                    h1 = section.findChildren("h1", recursive=False)[0]
                    url = h1.findChildren("a", class_="change_news_trigger", recursive=False)[0]

                    try:
                        mb25 = section.findChildren("div", class_="mb25", recursive=False)[0]
                        href = mb25.findChildren("a", class_="change_news_trigger", recursive=False)[0]
                        img = href.findChildren("img", recursive=False)[0].attrs['src']
                        if not img.startswith('http'):
                            if img.startswith('/'): img = 'https://granbluefantasy.jp' + img
                            else: img = 'https://granbluefantasy.jp/' + img
                    except:
                        img = None

                    res.append([url.attrs['href'], url.text, img])

                if 'news_url' in self.bot.data.save['gbfdata']:
                    foundNew = False
                    for i in range(0, len(res)):
                        found = False
                        for j in range(0, len(self.bot.data.save['gbfdata']['news_url'])):
                            if res[i][0] == self.bot.data.save['gbfdata']['news_url'][j][0]:
                                found = True
                                break
                        if not found:
                            ret.append(res[i])
                            foundNew = True
                    if foundNew:
                        with self.bot.data.lock:
                            self.bot.data.save['gbfdata']['news_url'] = res
                            self.bot.data.pending = True
                else:
                    with self.bot.data.lock:
                        self.bot.data.save['gbfdata']['news_url'] = res
                        self.bot.data.pending = True

            except:
                pass
        return ret

    def check4koma(self):
        data = self.bot.gbf.request('http://game.granbluefantasy.jp/comic/list/1?PARAMS', account=self.bot.data.save['gbfcurrent'], decompress=True, load_json=True, check=True)
        if data is None: return None, None
        last = data['list'][0]
        if '4koma' in self.bot.data.save['gbfdata']:
            if last is not None and int(last['id']) > int(self.bot.data.save['gbfdata']['4koma']):
                with self.bot.data.lock:
                    self.bot.data.save['gbfdata']['4koma'] = last['id']
                    self.bot.data.pending = True
                title = last['title_en']
                if title == "": title = last['title']
                return title, last
        else:
            with self.bot.data.lock:
                self.bot.data.save['gbfdata']['4koma'] = last['id']
                self.bot.data.pending = True
        return None, None

    def ut(self, ctx = None):
        if 'ticket_id' not in self.bot.data.save['gbfdata']:
            with self.bot.data.lock:
                self.bot.data.save['gbfdata']['ticket_id'] = 0
                self.bot.data.pending = True
            silent = True
            id = 0
        else:
            silent = False
            id = self.bot.data.save['gbfdata']['ticket_id']
        news = []
        errc = 0
        while errc < 8:
            id += 1
            url = "http://game-a.granbluefantasy.jp/assets_en/img_low/sp/assets/item/ticket/1{}1.jpg".format(str(id).zfill(4))
            if self.bot.gbf.request(url, no_base_headers=True) is not None:
                with self.bot.data.lock:
                    self.bot.data.save['gbfdata']['ticket_id'] = id
                    self.bot.data.pending = True
                if not silent: news.append(url)
                errc = 0
            else:
                errc += 1
        return news

    def isOwner(): # for decorators
        async def predicate(ctx):
            return ctx.bot.isOwner(ctx)
        return commands.check(predicate)

    def isOwnerOrDebug(): # for decorators
        async def predicate(ctx):
            return (ctx.bot.isOwner(ctx) or ctx.bot.isChannel(ctx, 'debug_bot'))
        return commands.check(predicate)

    async def do(self, executor, func, *args):
        return await self.bot.loop.run_in_executor(executor, func, *args)

    def ce(self, ct, o, i, silent):
        try:
            found = {'type':0, 'ct':ct, 'count':0}
            cid = ct[1]
            id = self.bot.data.save['gbfdata']['c'][i] + 1
            errc = 0
            while errc < 10:
                data = self.dad(str(cid + id * 1000), silent)

                if data[0] == "":
                    errc += 1
                else:
                    with self.bot.data.lock:
                        self.bot.data.save['gbfdata']['c'][i] = id
                        self.bot.data.pending = True
                    found['count'] += 1
                    errc = 0

                    if not silent:
                        self.bot.doAsTask(self.dadp(o, data, "{} : {}".format(ct[0], str(cid + id * 1000)), str(cid + id * 1000)))
                id += 1
            return found
        except:
            return None

    def cw(self, k, i, o, silent):
        try:
            x = int(k)
            wl = self.bot.data.config['gbfwatch']['wl']
            ws = self.bot.data.config['gbfwatch']['ws']
            wt = self.bot.data.config['gbfwatch']['wt']
            found = {'type':1, 'r':{}}
            errc = 0
            if len(self.bot.data.save['gbfdata']['w'][k][i]) == 0 or self.bot.data.save['gbfdata']['w'][k][i][-1] < 10:
                stid = 0
                max = 10
            else:
                stid = self.bot.data.save['gbfdata']['w'][k][i][-1] - 10
                max = self.bot.data.save['gbfdata']['w'][k][i][-1]
            id = (103 + x) * 10000000 + i * 100000 + stid * 100
            while errc < 7 or stid <= max:
                if stid in self.bot.data.save['gbfdata']['w'][k][i]:
                    stid += 1
                    continue
                id = (103 + x) * 10000000 + i * 100000 + stid * 100
                wfound = False
                for wul in wl:
                    data = self.bot.gbf.request(wul.format(id), no_base_headers=True)
                    if data is not None:
                        wfound = True
                        break
                if not wfound:
                    errc += 1
                    stid += 1
                    continue

                errc = 0
                with self.bot.data.lock:
                    self.bot.data.save['gbfdata']['w'][k][i].append(stid)
                    self.bot.data.pending = True

                tt = ws[x+2].format(self.bot.emote.get(wt.get(str(i+1), "Error")))
                if tt not in found['r']:
                    found['r'][tt] = 1
                else:
                    found['r'][tt] += 1

                if not silent:
                    r = self.bot.doAsTask(self.atr(o, str(id), True))
                    if not r:
                        self.bot.doAsTask(o.send(embed=self.bot.util.embed(title=ws[x], description='{} ▫️ {}'.format(tt, id), thumbnail=wl[0].format(id), color=self.color)))

                stid += 1

            with self.bot.data.lock:
                self.bot.data.save['gbfdata']['w'][k][i].sort()
                if len(self.bot.data.save['gbfdata']['w'][k][i]) > 11: self.bot.data.save['gbfdata']['w'][k][i] = self.bot.data.save['gbfdata']['w'][k][i][-11:]
                self.bot.data.pending = True
            return found
        except:
            return None

    async def cc(self, o):
        found = {}

        if 'c' not in self.bot.data.save['gbfdata'] or 'w' not in self.bot.data.save['gbfdata']:
            return

        try:
            crt = self.bot.data.config['gbfwatch']['crt']
        except:
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as e:
            coros = []
            for i in range(0, len(self.bot.data.save['gbfdata']['c'])):
                coros.append(self.do(e, self.ce, crt[i], o, i, False))
            for k in self.bot.data.save['gbfdata']['w']:
                for i in range(0, len(self.bot.data.save['gbfdata']['w'][k])):
                    coros.append(self.do(e, self.cw, k, i, o, False))
            results = await asyncio.gather(*coros)
            for r in results:
                if r is None: continue
                elif r['type'] == 0:
                    if r['count'] > 0:
                        found[r['ct'][0]] = r['count']
                elif r['type'] == 1:
                    for tt in r['r']:
                        found[tt] = r['r'][tt]
        return found

    async def atr(self, target, id, turbo=False):
        try:
            atr = self.bot.data.config['gbfwatch']['atr']
            type = int(id[0])
            id = int(id)
            if type not in [1, 2]: raise Exception()
            if turbo and type == 1:
                data = await self.bot.do(self.bot.gbf.request, atr[0], account=self.bot.data.save['gbfcurrent'], decompress=True, load_json=True, check=True, payload={"special_token":None,"weapon_id":str(id)})
            else:
                data = (await self.bot.do(self.bot.gbf.request, atr[1], account=self.bot.data.save['gbfcurrent'], decompress=True, load_json=True, check=True, payload={"special_token":None,"item_id":id,"item_kind":type}))['data']

            rarity = "{}".format(self.bot.emote.get({"2":"R", "3":"SR", "4":"SSR"}.get(data['rarity'], '')))
            msg = '{} {} {} {} at \⭐\⭐\⭐\n'.format(self.bot.emote.get('hp'), data['max_hp'], self.bot.emote.get('atk'), data['max_attack'])
            if turbo: msg += '*{}*\n'.format(data['comment'])
            if type == 1:
                kind = "{}".format(self.bot.emote.get({'1': 'sword','2': 'dagger','3': 'spear','4': 'axe','5': 'staff','6': 'gun','7': 'melee','8': 'bow','9': 'harp','10': 'katana'}.get(data.get('kind', ''), '')))
                if 'special_skill' in data:
                    msg += "{} **{}**\n".format(self.bot.emote.get('skill1'), data['special_skill']['name'])
                    msg += "{}\n".format(data['special_skill']['comment'].replace('<span class=text-blue>', '').replace('</span>', ''))
                for i in range(1, 4):
                    key = 'skill{}'.format(i)
                    sk = data.get(key, [])
                    if sk is not None and len(sk) > 0:
                        msg += "{} **{}**".format(self.bot.emote.get('skill2'), sk['name'])
                        if 'masterable_level' in sk:
                            if ',' in sk['masterable_level']:
                                base = sk['masterable_level'].split(',')[0]
                                if base != '1': msg += " (unlocks at lvl {}, upgrades at lvl ".format(base)
                                else: msg += " (upgrades at lvl "
                                msg += ', '.join(sk['masterable_level'].split(',')[1:])
                                msg += ')'
                            elif sk['masterable_level'] != '1':
                                msg += " (unlocks at lvl {})".format(sk['masterable_level'])
                        msg += "\n{}\n".format(sk['comment'].replace('<span class=text-blue>', '').replace('</span>', ''))
                url = 'http://game-a.granbluefantasy.jp/assets_en/img_low/sp/assets/weapon/m/{}.jpg'.format(data['id'])
            elif type == 2:
                kind = '{}'.format(self.bot.emote.get('summon'))
                msg += "{} **{}**\n".format(self.bot.emote.get('skill1'), data['special_skill']['name'])
                msg += "{}\n".format(data['special_skill']['comment'])
                if 'recast_comment' in data['special_skill']:
                    msg += "{}\n".format(data['special_skill']['recast_comment'])
                msg += "{} **{}**\n".format(self.bot.emote.get('skill2'), data['skill1']['name'])
                msg += "{}\n".format(data['skill1']['comment'])
                if 'sub_skill' in data:
                    msg += "{} **Sub Aura**\n".format(self.bot.emote.get('skill2'))
                    msg += "{}\n".format(data['sub_skill']['comment'])
                url = 'http://game-a.granbluefantasy.jp/assets_en/img_low/sp/assets/summon/m/{}.jpg'.format(data['id'])
            await target.send(embed=self.bot.util.embed(title="{}{}{} {}".format(rarity, kind, data['name'], data.get('series_name', '')), description=msg, thumbnail=url, footer=data['id'], color=self.color))
            return True
        except:
            return False

    async def dadp(self, c, data, tt, x=None):
        fields = []
        if x is None: x = tt
        tmp = ""
        for k in data[2]:
            try:
                with open(k, 'rb') as infile:
                    df = discord.File(infile)
                    message = await self.bot.send('image', file=df)
                    df.close()
                tmp += "[{}]({})\n".format('_'.join(k.replace(x, '').split('_')[:-1]), message.attachments[0].url)
                self.bot.file.rm(k)
            except:
                pass
        if len(tmp) > 0:
            fields.append({'name':'Sprites', 'value':tmp})

        for k in data[1]:
            tmp = ""
            for t in data[1][k]:
                if data[1][k][t]:
                    tmp += t + ', '
            if len(tmp) > 0:
                fields.append({'name':k, 'value':tmp[:-2]})
        
        for f in fields:
            if len(f['value']) >= 1024:
                f['value'] = f['value'][:1019] + '...'
        try:
            with open(data[0], "rb") as f:
                df = discord.File(f)
                await c.send(embed=self.bot.util.embed(title=tt, fields=fields, color=self.color, thumbnail=data[3]), file=df)
                df.close()
            self.bot.file.rm(data[0])
        except:
            await c.send(embed=self.bot.util.embed(title=tt, description=data[0], fields=fields, color=self.color, thumbnail=data[3]))

    def pa(self, a, indent):
        s = ""
        if indent > 0:
            s = "|"
            for i in range(0, indent): s += "-"
            s += " "
        res = ""
        for c in a:
            if isinstance(c, list):
                res += self.pa(c, indent+1)
            else:
                res += s+c+'\r\n'
        if indent == 0: res += '\r\n'
        return res

    def genTS(self):
        ts = int(datetime.utcnow().timestamp())
        with self.tlock:
            while ts in self.tcache:
                ts += 1
            self.tcache.append(ts)
        return ts

    def dad(self, id, silent, mode = 0):
        if id[0] == '3': type = 0
        elif id[0] == '2': type = 1
        elif id[0] == '1': type = 2
        else: return ["", {}, {}, {}, ""]
        try:
            files = self.bot.data.config['gbfwatch']["files"]
            flags = {}
            for t in self.bot.data.config['gbfwatch']["flags"]:
                flags[t] = {}
                for k in self.bot.data.config['gbfwatch']["flags"][t]:
                    flags[t][k] = False
            it = self.bot.data.config['gbfwatch']["it"]
            thct = self.bot.data.config['gbfwatch']["thct"]
            thbd = self.bot.data.config['gbfwatch']["thbd"]
        except:
            return ["", {}, {}, {}, ""]

        thf = thbd[type].format(id)
        try:
            data = self.bot.gbf.request(thbd[type].format(id), no_base_headers=True)
            if data is None and type == 0:
                data = self.bot.gbf.request(thct.format(id).replace("/30", "/38"), no_base_headers=True)
                if data is not None:
                    thf = thct.format(id).replace("/30", "/38")
        except:
            pass

        ts = None
        paste = ""
        iul = []
        counter = 0
        font = ImageFont.truetype("assets/font.ttf", 16)
        for f in files[type]:
            if mode == 1: ff = f[0] + id + f[1] + '_s2'
            else: ff = f[0] + id + f[1]
            uu = self.bot.data.config['gbfwatch']["base"].format(ff)
            try:
                data = self.bot.gbf.request(uu, no_base_headers=True)
                if data is None: raise Exception("404")
                data = str(data)
                paste += '# {} ############################################\r\n'.format(ff)

                root = []
                ref = root
                stack = []
                dupelist = []
                match = 0
                rcs = []
                imc = 1
                wd = 0
                ht = 0
                current = data.find("{", 0) + 1

                while current < len(data):
                    c = data[current]
                    if c == ff[match]:
                        match += 1
                        if match == len(ff):
                            if data[current+1] == '_':
                                x = current+2
                                while x < len(data) and (data[x] == '_' or data[x].isalnum()):
                                    x += 1
                                n = data[current+2:x]
                                if len(n) == 1:
                                    if n == "b":
                                        rcs[-1][-1] = 1
                                        if imc < 2: imc = 2
                                    elif n == "c":
                                        rcs[-1][-1] = 2
                                        if imc < 3: imc = 3
                                elif n != "" and (len(ref) == 0 or(len(ref) > 0 and ref[-1] != n)):
                                    ref.append(n)
                                    if n not in dupelist:
                                        dupelist.append(n)
                                        sub = n.split('_')
                                        for sk in sub:
                                            for fk in flags:
                                                if sk in flags[fk]:
                                                    flags[fk][sk] = True
                                current = x - 1
                            match = 0
                    else:
                        match = 0
                        if c == '{':
                            ref.append([])
                            stack.append(ref)
                            ref = ref[-1]
                        elif c == '}':
                            try:
                                ref = stack[-1]
                                if len(ref[-1]) == 0:
                                    ref.pop()
                                stack.pop()
                            except:
                                pass
                        elif len(stack) == 1:
                            sstr = data[current:]
                            if sstr.startswith("Rectangle("):
                                lp = sstr.find(")")
                                try:
                                    rc = sstr[len("Rectangle("):lp].split(',')
                                    rc = [int(ir.replace('1e3', '1000')) for ir in rc]
                                    for p in rc:
                                        if p < 0: raise Exception()
                                    if sum(rc) == 0:
                                        raise Exception()
                                    rc[2] += rc[0]
                                    rc[3] += rc[1]
                                    if rc[2] > wd: wd = rc[2]
                                    if rc[3] > ht: ht = rc[3]
                                    rc.append(stack[-1][-2])
                                    rc.append(0)
                                    rcs.append(rc)
                                except:
                                    pass
                    current += 1
                paste += self.pa(root, 0)
                i = Image.new('RGB', (wd*imc+200,ht+200), "black")
                d = ImageDraw.Draw(i)
                txcs = []
                for rc in rcs:
                    try:
                        fill = None
                        for q in it:
                            if fill is not None: break
                            for sfql in q[-1]:
                                if sfql in rc[4].lower():
                                    fill = (q[0],q[1],q[2])
                                    break
                        rc[0] += rc[5]*wd
                        rc[2] += rc[5]*wd
                        d.rectangle(rc[:4],fill=fill,outline=(140,140,140))
                        txcs.append([rc[0], rc[1], rc[4]])
                    except:
                        pass
                rcs.clear()
                txsb = []
                for txc in txcs:
                    bss = txc[:-1]
                    tss = font.getsize(txc[2])
                    bbx = [bss[0], bss[1], bss[0]+tss[0], bss[1]+tss[1]]
                    for tbx in txsb:
                        if bbx[0] < tbx[2] and tbx[0] < bbx[2] and bbx[1] < tbx[3] and tbx[1] < bbx[3]:
                            diff = tbx[3] - bbx[1]
                            bbx[1] += diff
                            bbx[3] += diff
                    txsb.append(bbx)
                    try: d.text((bbx[0], bbx[1]),txc[2],font=font,fill=(255,255,255))
                    except: pass
                txsb.clear()
                txcs.clear()
                if ts is None: ts = self.genTS()
                fst = "{}_{}.png".format(ff, ts)
                i.save(fst, "PNG")
                i.close()
                iul.append(fst)
            except:
                try: i.close()
                except: pass
                if counter >= 3 and len(paste) == 0:
                    return ["", {}, {}, thf, ""]
            counter+=1

        if len(paste) > 0:
            if silent:
                return ["Not uploaded", flags, iul, thf, paste]
            else:
                if ts is None: ts = self.genTS()
                title = "{}_dump_{}.txt".format(id, ts)
                with open(title, "wb") as f:
                    f.write(paste.encode('utf-8'))
                return [title, flags, iul, thf, paste]
        else:
            return ["", {}, {}, thf, ""]

    @commands.command(no_pm=True, cooldown_after_parsing=True)
    @isOwnerOrDebug()
    @commands.cooldown(1, 10, commands.BucketType.default)
    async def item(self, ctx, id : int):
        """Retrieve an item description (Owner or Debug Server only)"""
        try:
            data = await self.bot.do(self.bot.gbf.request, 'http://game.granbluefantasy.jp/rest/quest/droplist/drop_item_detail?PARAMS', account=self.bot.data.save['gbfcurrent'], decompress=True, load_json=True, check=True, payload={"special_token":None,"item_id":id,"item_kind":10})
            await ctx.reply(embed=self.bot.util.embed(title=data['name'], description=data['comment'].replace('<br>', ' '), thumbnail="http://game-a.granbluefantasy.jp/assets_en/img/sp/assets/item/article/s/{}.jpg".format(id), footer=data['id'], color=self.color))
        except:
            await self.bot.util.react(ctx.message, '❎') # white negative mark

    @commands.command(no_pm=True, cooldown_after_parsing=True)
    @isOwnerOrDebug()
    @commands.cooldown(1, 8, commands.BucketType.default)
    async def loot(self, ctx, id : str):
        """Retrieve a weapon or summon description (Owner or Debug Server only)"""
        try:
            await self.atr(ctx, id)
        except:
            await self.bot.util.react(ctx.message, '❎') # white negative mark

    @commands.command(no_pm=True, cooldown_after_parsing=True)
    @isOwnerOrDebug()
    @commands.cooldown(1, 2, commands.BucketType.default)
    async def dd(self, ctx, id : str, mode : int = 0):
        """Retrieve details (Owner or Debug Server only)"""
        if not await self.bot.do(self.bot.gbf.isAvailable):
            await ctx.reply(embed=self.bot.util.embed(title="Unavailable", color=self.color))
            return
        await self.bot.util.react(ctx.message, 'time')
        data = await self.bot.do(self.dad, id, False, mode)
        if data[0] != "":
            await self.dadp(ctx.channel, data, id)
        await self.bot.util.unreact(ctx.message, 'time')
        await self.bot.util.react(ctx.message, '✅') # white check mark

    @commands.command(no_pm=True, cooldown_after_parsing=True)
    @isOwner()
    async def cn(self, ctx):
        """Check content (Owner only)"""
        if not await self.bot.do(self.bot.gbf.isAvailable):
            await ctx.reply(embed=self.bot.util.embed(title="Unavailable", color=self.color))
            return
        await self.bot.util.react(ctx.message, 'time')
        uc = await self.cc(ctx.channel)
        await self.bot.util.unreact(ctx.message, 'time')
        msg = ""
        if len(uc) > 0:
            msg += "**Content update**\n"
            for k in uc:
                msg += "{} {}\n".format(uc[k], k)
        if msg != "":
            await self.bot.send('debug', embed=self.bot.util.embed(title="Result", description=msg, color=self.color))
        await self.bot.util.react(ctx.message, '✅') # white check mark