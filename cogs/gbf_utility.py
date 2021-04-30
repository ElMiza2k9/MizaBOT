﻿import discord
from discord.ext import commands
import asyncio
import aiohttp
from datetime import datetime, timedelta
import random
import math
import re
import sqlite3
import os
from bs4 import BeautifulSoup
from xml.sax import saxutils as su
from urllib import parse
from operator import itemgetter

class GBF_Utility(commands.Cog):
    """GBF related commands."""
    def __init__(self, bot):
        self.bot = bot
        self.color = 0x46fc46

    def isYou(): # for decorators
        async def predicate(ctx):
            return ctx.bot.isServer(ctx, 'you_server')
        return commands.check(predicate)

    def isOwner(): # for decorators
        async def predicate(ctx):
            return ctx.bot.isOwner(ctx)
        return commands.check(predicate)

    def honorFormat(self, h): # convert honor number to a shorter string version
        if h is None: return "n/a"
        elif h >= 1000000000: return "{:.1f}B".format(h/1000000000)
        elif h >= 1000000: return "{:.1f}M".format(h/1000000)
        elif h >= 1000: return "{:.1f}K".format(h/1000)
        return h

    def getMaintenanceStatus(self): # check the gbf maintenance status, empty string returned = no maintenance
        current_time = self.bot.getJST()
        msg = ""
        if self.bot.maintenance['state'] == True:
            if current_time < self.bot.maintenance['time']:
                d = self.bot.maintenance['time'] - current_time
                if self.bot.maintenance['duration'] == 0:
                    msg = "{} Maintenance starts in **{}**".format(self.bot.getEmote('cog'), self.bot.getTimedeltaStr(d, 2))
                else:
                    msg = "{} Maintenance starts in **{}**, for **{} hour(s)**".format(self.bot.getEmote('cog'), self.bot.getTimedeltaStr(d, 2), self.bot.maintenance['duration'])
            else:
                d = current_time - self.bot.maintenance['time']
                if self.bot.maintenance['duration'] <= 0:
                    msg = "{} Emergency maintenance on going".format(self.bot.getEmote('cog'))
                elif (d.seconds // 3600) >= self.bot.maintenance['duration']:
                    self.bot.maintenance = {"state" : False, "time" : None, "duration" : 0}
                    self.bot.savePending = True
                else:
                    e = self.bot.maintenance['time'] + timedelta(seconds=3600*self.bot.maintenance['duration'])
                    d = e - current_time
                    msg = "{} Maintenance ends in **{}**".format(self.bot.getEmote('cog'), self.bot.getTimedeltaStr(d, 2))
        return msg

    # function to fix the case (for $wiki)
    def fixCase(self, term): # term is a string
        fixed = ""
        up = False
        if term.lower() == "and": # if it's just 'and', we don't don't fix anything and return a lowercase 'and'
            return "and"
        elif term.lower() == "of":
            return "of"
        elif term.lower() == "(sr)":
            return "(SR)"
        elif term.lower() == "(ssr)":
            return "(SSR)"
        elif term.lower() == "(r)":
            return "(R)"
        for i in range(0, len(term)): # for each character
            if term[i].isalpha(): # if letter
                if term[i].isupper(): # is uppercase
                    if not up: # we haven't encountered an uppercase letter
                        up = True
                        fixed += term[i] # save
                    else: # we have
                        fixed += term[i].lower() # make it lowercase and save
                elif term[i].islower(): # is lowercase
                    if not up: # we haven't encountered an uppercase letter
                        fixed += term[i].upper() # make it uppercase and save
                        up = True
                    else: # we have
                        fixed += term[i] # save
                else: # other characters
                    fixed += term[i] # we just save
            elif term[i] == "/" or term[i] == ":" or term[i] == "#" or term[i] == "-": # we reset the uppercase detection if we encounter those
                up = False
                fixed += term[i]
            else: # everything else,
                fixed += term[i] # we save
        return fixed # return the result

    def stripWikiStr(self, elem):
        txt = elem.text.replace('foeBoost', 'foe. Boost') # special cases
        checks = [['span', 'tooltiptext'], ['sup', 'reference'], ['span', 'skill-upgrade-text']]
        for target in checks:
            f = elem.findChildren(target[0], class_=target[1])
            for e in f:
                txt = txt.replace(e.text, "")
        return txt.replace('Slight', '_sligHt_').replace('C.A.', 'CA').replace('.', '. ').replace('!', '! ').replace('?', '? ').replace(':', ': ').replace('. )', '.)').replace("Damage cap", "Cap").replace("Damage", "DMG").replace("damage", "DMG").replace(" and ", " and").replace(" and", " and ").replace("  ", " ").replace("fire", str(self.bot.getEmote('fire'))).replace("water", str(self.bot.getEmote('water'))).replace("earth", str(self.bot.getEmote('earth'))).replace("wind", str(self.bot.getEmote('wind'))).replace("dark", str(self.bot.getEmote('dark'))).replace("light", str(self.bot.getEmote('light'))).replace("Fire", str(self.bot.getEmote('fire'))).replace("Water", str(self.bot.getEmote('water'))).replace("Earth", str(self.bot.getEmote('earth'))).replace("Wind", str(self.bot.getEmote('wind'))).replace("Dark", str(self.bot.getEmote('dark'))).replace("Light", str(self.bot.getEmote('light'))).replace('_sligHt_', 'Slight')

    async def requestWiki(self, ctx, url, search_mode = False): # url MUST be for gbf.wiki
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if r.status != 200:
                    raise Exception("HTTP Error 404: Not Found")
                else:
                    cnt = await r.content.read()
                    try: cnt = cnt.decode('utf-8')
                    except: cnt = cnt.decode('iso-8859-1')
                    soup = BeautifulSoup(cnt, 'html.parser') # parse the html
                    try: title = soup.find_all("h1", id="firstHeading", class_="firstHeading")[0].text # page title
                    except: title = ""
                    if search_mode and not title.startswith('Search results'): # handling rare cases of the search function redirecting the user directly to a page
                        search_mode = False
                        url = "https://gbf.wiki/{}".format(title.replace(' ', '_')) # update the url so it looks pretty (with the proper page name)

                    if search_mode: # use the wiki search function
                        try:
                            res = soup.find_all("ul", class_="mw-search-results")[0].findChildren("li", class_="mw-search-result", recursive=False) # recuperate the search results
                        except:
                            raise Exception("HTTP Error 404: Not Found") # no results
                        matches = []
                        for r in res: # for each, get the title
                            matches.append(r.findChildren("div", class_="mw-search-result-heading", recursive=False)[0].findChildren("a", recursive=False)[0].attrs['title'])
                            if len(matches) >= 5: break # max 5
                        if len(matches) == 0: # no results check
                            raise Exception("No results")
                        elif len(matches) == 1: # single result, request it directly
                            await self.requestWiki(ctx, "https://gbf.wiki/{}".format(matches[0]))
                            return
                        desc = ""
                        for m in matches: # build the message with the results
                            desc += "[{}](https://gbf.wiki/{})\n".format(m, m.replace(" ", "_"))
                        desc = "First five results\n{}".format(desc)
                        final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="Not Found, click here to refine", description=desc, url=url, color=self.color))
                    else: # direct access to the page (assume a match)
                        data = {}
                        # what we are interested in
                        type_check = {"/Category:Fire_Characters":0, "/Category:Water_Characters":1, "/Category:Earth_Characters":2, "/Category:Wind_Characters":3, "/Category:Dark_Characters":4, "/Category:Light_Characters":5, "/Category:Special_Characters":6, "/Category:Fire_Summons":10, "/Category:Water_Summons":11, "/Category:Earth_Summons":12, "/Category:Wind_Summons":13, "/Category:Dark_Summons":14, "/Category:Light_Summons":15, "/Category:Special_Summons":16, "/Category:Sabre_Weapons":20, "/Category:Dagger_Weapons":21, "/Category:Spear_Weapons":22, "/Category:Axe_Weapons":23, "/Category:Staff_Weapons":24, "/Category:Gun_Weapons":25, "/Category:Melee_Weapons":26, "/Category:Bow_Weapons":27, "/Category:Harp_Weapons":28, "/Category:Katana_Weapons":29}
                        for k, n in type_check.items(): # check if the page matches
                            r = soup.find_all("a", {'href' : k})
                            if len(r) > 0:
                                data['object'] = n // 10 # 0 = chara, 1 = summon, 2 = weapon
                                if data['object'] < 2: data['element'] = {0:'fire', 1:'water', 2:'earth', 3:'wind', 4:'dark', 5:'light', 6:'misc'}.get(n%10, "") # retrieve the element here for chara and summon
                                else: data['type'] = k[len('/Category:'):k.find('_Weapons')].lower().replace('sabre', 'sword') # retrieve the wpn type here
                                break
                        # retrieve thumbnail if any
                        try:
                            i = soup.find_all("script", type="application/ld+json")[0].string
                            s = i.find("\"image\" : \"")
                            if s != -1:
                                s += len("\"image\" : \"")
                                e = i.find("\"", s)
                                data['image'] = i[s:e]
                        except:
                            pass

                        # retrieve ID
                        tables = soup.find_all("table", class_='wikitable') # iterate all wikitable
                        for t in tables:
                            try:
                                body = t.findChildren("tbody" , recursive=False)[0].findChildren("tr" , recursive=False) # check for tr tag
                                for tr in body:
                                    if str(tr).find("ID") != -1:
                                        try:
                                            if tr.findChildren("th")[0].text.strip() == "ID" and 'id' not in data:
                                                data['id'] = tr.findChildren("td")[0].text
                                        except: pass
                            except:
                                pass

                        # retrieve description
                        try: data['description'] = soup.find_all("meta", {'name' : 'description'})[0].attrs['content']
                        except: pass

                        # get rarity, title and name
                        try: 
                            header = soup.find_all("div", class_='char-header')[0] # get it
                            try: # first we get the rarity
                                data['rarity'] = str(header.findChildren("div" , class_='char-rarity', recursive=False)[0])
                                if data['rarity'].find("Rarity SSR") != -1: data['rarity'] = "SSR"
                                elif data['rarity'].find("Rarity SR") != -1: data['rarity'] = "SR"
                                elif data['rarity'].find("Rarity R") != -1: data['rarity'] = "R"
                                else: data['rarity'] = ""
                            except:
                                pass
                            for child in header.findChildren("div" , recursive=False): # then the name and title if any
                                if 'class' not in child.attrs:
                                    for divs in child.findChildren("div" , recursive=False):
                                        if 'class' in divs.attrs:
                                            if 'char-name' in divs.attrs['class']: data['name'] = divs.text
                                            elif 'char-title' in divs.attrs['class']:
                                                try:
                                                    tx = divs.findChildren("span", recursive=False)[0].text
                                                    data['title'] = tx[1:tx.find("]")]
                                                except:
                                                    tx = divs.text
                                                    data['title'] = tx[1:tx.find("]")]
                        except:
                            pass

                        x = data.get('object', None)
                        if x is None: # if no match
                            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title=title, description=data.get('description', None), image=data.get('image', None), url=url, footer=data.get('id', None), color=self.color))
                        elif x == 0: # charater
                            if 'title' in data: title = title + ", " + data['title']
                            if 'rarity' in data: title = "{} {}".format(self.bot.getEmote(data['rarity']), title)
                            try:
                                # check all character versions
                                versions = soup.find_all("div", class_="character__versions")[0].findChildren("table", recursive=False)[0].findChildren("tbody", recursive=False)[0].findChildren("tr", recursive=False)[2].findChildren("td", recursive=False)
                                elems = []
                                for v in versions:
                                    s = v.findChildren("a", recursive=False)[0].text
                                    if s != title: elems.append(s)
                                if len(elems) == 0: raise Exception()
                                desc = "This character has other versions\n"
                                for e in elems:
                                    desc += "[{}](https://gbf.wiki/{})\n".format(e, e.replace(" ", "_"))
                                final_msg = await ctx.reply(embed=self.bot.buildEmbed(title=title, description=desc, image=data.get('image', None), url=url, footer=data.get('id', None), color=self.color))
                            except: # if none, just send the link
                                final_msg = await ctx.reply(embed=self.bot.buildEmbed(title=title, description=data.get('description', None), image=data.get('image', None), url=url, footer=data.get('id', None), color=self.color))
                        else: # summon and weapon
                            # iterate all wikitable again
                            for t in tables:
                                body = t.findChildren("tbody" , recursive=False)[0].findChildren("tr" , recursive=False) # check for tr tag
                                if str(body).find("Copyable?") != -1: continue # for chara skills if I add it one day
                                expecting_hp = False
                                expecting_wpn_skill = False
                                expecting_sum_call = False
                                aura = 0
                                for tr in body: # iterate on tags
                                    content = str(tr)
                                    if expecting_sum_call:
                                        if content.find("This is the call for") != -1 or content.find("This is the basic call for") != -1:
                                            try: data['call'][1] = self.stripWikiStr(tr.findChildren("td")[0])
                                            except: pass
                                        else:
                                            expecting_sum_call = False
                                    elif expecting_wpn_skill:
                                        if 'class' in tr.attrs and tr.attrs['class'][0].startswith('skill'):
                                            if tr.attrs['class'][-1] == "post" or (tr.attrs['class'][0] == "skill" and len(tr.attrs['class']) == 1):
                                                try: 
                                                    n = tr.findChildren("td", class_="skill-name", recursive=False)[0].text.replace("\n", "")
                                                    d = tr.findChildren("td", class_="skill-desc", recursive=False)[0]
                                                    if 'skill' not in data: data['skill'] = []
                                                    data['skill'].append([n, self.stripWikiStr(d)])
                                                except: pass
                                        else:
                                            expecting_wpn_skill = False
                                    elif expecting_hp:
                                        if content.find('Level ') != -1:
                                            childs = tr.findChildren(recursive=False)
                                            try: data['lvl'] = childs[0].text[len('Level '):]
                                            except: pass
                                            try: data['hp'] = childs[1].text
                                            except: pass
                                            try: data['atk'] = childs[2].text
                                            except: pass
                                        else:
                                            expecting_hp = False
                                    elif content.find('class="hp-text"') != -1 and content.find('class="atk-text"') != -1:
                                        try:
                                            expecting_hp = True
                                            elem_table = {"/Weapon_Lists/SSR/Fire":"fire", "/Weapon_Lists/SSR/Water":"water", "/Weapon_Lists/SSR/Earth":"earth", "/Weapon_Lists/SSR/Wind":"wind", "/Weapon_Lists/SSR/Dark":"dark", "/Weapon_Lists/SSR/Light":"light"}
                                            for s, e in elem_table.items():
                                                if content.find(s) != -1:
                                                    data['element'] = e
                                                    break
                                        except: pass
                                    elif content.find('"Skill charge attack.png"') != -1:
                                        try:
                                            n = tr.findChildren("td", class_="skill-name", recursive=False)[0].text
                                            d = tr.findChildren("td", recursive=False)[-1]
                                            data['ca'] = [n, self.stripWikiStr(d)]
                                        except: pass
                                    elif content.find('"/Weapon_Skills"') != -1:
                                        expecting_wpn_skill = True
                                    elif content.find('<a href="/Sword_Master" title="Sword Master">Sword Master</a>') != -1 or content.find('Status_Energized') != -1:
                                        try:
                                            tds = tr.findChildren("td", recursive=False)
                                            n = tds[0].text
                                            d = tds[1]
                                            if 'sm' not in data: data['sm'] = []
                                            data['sm'].append([n, self.stripWikiStr(d)])
                                        except: pass
                                    elif content.find('"/Summons#Calls"') != -1:
                                        try:
                                            data['call'] = [tr.findChildren("th")[0].text[len("Call - "):], '']
                                            expecting_sum_call = True
                                        except: pass
                                    elif content.find("Main Summon") != -1:
                                        aura = 1
                                    elif content.find("Sub Summon") != -1:
                                        aura = 2
                                    elif content.find("This is the basic aura") != -1:
                                        try:
                                            if aura == 0: aura = 1
                                            n = tr.findChildren("span", class_="tooltip")[0].text.split("This is the basic aura")[0]
                                            d = tr.findChildren("td")[0]
                                            if aura == 1: data['aura'] = self.stripWikiStr(d)
                                            elif aura == 2: data['subaura'] = self.stripWikiStr(d)
                                        except: pass
                                    elif content.find("This is the aura") != -1:
                                        try:
                                            n = tr.findChildren("span", class_="tooltip")[0].text.split("This is the aura")[0]
                                            d = tr.findChildren("td")[0]
                                            if aura == 1: data['aura'] = self.stripWikiStr(d)
                                            elif aura == 2: data['subaura'] = self.stripWikiStr(d)
                                        except: pass
                            # final message
                            title = ""
                            title += "{}".format(self.bot.getEmote(data.get('element', '')))
                            title += "{}".format(self.bot.getEmote(data.get('rarity', '')))
                            title += "{}".format(self.bot.getEmote(data.get('type', '')))
                            title += "{}".format(data.get('name', ''))
                            if 'title' in data: title += ", {}".format(data['title'])

                            desc = ""
                            if 'lvl' in data: desc += "**Lvl {}** ".format(data['lvl'])
                            if 'hp' in data: desc += "{} {} ".format(self.bot.getEmote('hp'), data['hp'])
                            if 'atk' in data: desc += "{} {}".format(self.bot.getEmote('atk'), data['atk'])
                            if desc != "": desc += "\n"
                            if 'ca' in data: desc += "{} **{}**▫️{}\n".format(self.bot.getEmote('skill1'), data['ca'][0], data['ca'][1])
                            if 'skill' in data:
                                for s in data['skill']:
                                    desc += "{} **{}**▫️{}\n".format(self.bot.getEmote('skill2'), s[0], s[1])
                            if 'sm' in data:
                                if desc != "": desc += "\n"
                                for s in data['sm']:
                                    if s[0] == "Attack" or s[0] == "Defend": continue
                                    desc += "**{}**▫️{}\n".format(s[0], s[1])
                            if 'call' in data: desc += "{} **{}**▫️{}\n".format(self.bot.getEmote('skill1'), data['call'][0], data['call'][1])
                            if 'aura' in data: desc += "{} **Aura**▫️{}\n".format(self.bot.getEmote('skill2'), data['aura'])
                            if 'subaura' in data: desc += "{} **Sub Aura**▫️{}\n".format(self.bot.getEmote('skill2'), data['subaura'])

                            footer = data.get('id', None)

                            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title=title, description=desc, thumbnail=data.get('image', None), url=url, footer=data.get('id', None), color=self.color))
        await self.bot.cleanMessage(ctx, final_msg, 80)


    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['gbfwiki'])
    @commands.cooldown(3, 4, commands.BucketType.guild)
    async def wiki(self, ctx, *, terms : str = ""):
        """Search the GBF wiki"""
        final_msg = None
        if terms == "":
            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="Tell me what to search on the wiki", footer="wiki [search terms]", color=self.color))
        else:
            # build the url (the wiki is case sensitive)
            arr = []
            for s in terms.split(" "):
                arr.append(self.fixCase(s))
            sch = "_".join(arr)
            url = "https://gbf.wiki/{}".format(sch)
            try:
                await self.requestWiki(ctx, url) # try to request
            except Exception as e:
                url = "https://gbf.wiki/index.php?title=Special:Search&search={}".format(parse.quote_plus(terms))
                if str(e) != "HTTP Error 404: Not Found": # unknown error, we stop here
                    await self.bot.sendError("wiki", str(e))
                    final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="Unexpected error, click here to search", url=url, footer=str(e), color=self.color))
                else: # failed, we try the search function
                    try:
                        await self.requestWiki(ctx, url, True) # try
                    except Exception as f:
                        if str(f) == "No results":
                            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="No matches found", color=self.color)) # no results
                        else:
                            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="Not Found, click here to refine", url=url, color=self.color)) # no results
        await self.bot.cleanMessage(ctx, final_msg, 45)

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['tweet'])
    @commands.cooldown(1, 2, commands.BucketType.default)
    async def twitter(self, ctx, term : str = ""):
        """Post a twitter account (Tweepy enhanced)
        If none is found and twitter is enabled, try to get the corresponding user.
        options: granblue_en, en, noel, channel, tv wawi, raidpic, pic, kmr, fkhr,
        kakage, hag, jk, hecate, hecate_mk2, gbfverification, gw, gamewith, anime,
        gbf, granblue"""
        registered = {
            'granblue_en' : ["granblue_en", "Welcome EOP"],
            'en' : ["granblue_en", "Welcome EOP"],
            'noel' : ["noel_gbf", "Japanese Granblue news"],
            'tv' : ["noel_gbf", "Japanese Granblue news"],
            'channel' : ["noel_gbf", "Japanese Granblue news"],
            'wawi' : ["wawigbf", "Subscribe: https://twitter.com/Wawi3313"],
            'raidpic' : ["twihelp_pic", "To grab Granblue raid artworks"],
            'pic' : ["twihelp_pic", "To grab Granblue raid artworks"],
            'kmr' : ["kimurayuito", "Give praise, for he has no equal"],
            'fkhr' : ["hiyopi", "The second in charge"],
            'kakage' : ["kakage0904", "Young JK inside"],
            'hag' : ["kakage0904", "Young JK inside"],
            'jk' : ["kakage0904", "Young JK inside"],
            'hecate' : ["hecate_mk2", "For nerds :nerd:"],
            'hecate_mk2' : ["hecate_mk2", "For nerds :nerd:"],
            'gbfverification' : ["hecate_mk2", "For nerds :nerd:"],
            'gw' : ["granblue_gw", ":nine: / :keycap_ten:"],
            'gamewith' : ["granblue_gw", ":nine: / :keycap_ten:"],
            'anime' : ["anime_gbf", ":u5408:"],
            'gbf' : ["granbluefantasy", "Official account"],
            'granblue' : ["granbluefantasy", "Official account"]
        }

        target = registered.get(term.lower(), None)
        pic = None
        user = None
        accepted = (target is not None)

        if target is None:
            user = self.bot.getTwitterUser(term.lower())
        else:
            user = self.bot.getTwitterUser(target[0])
        if user is not None:
            pic = user.profile_image_url.replace("normal", "bigger")
        else:
            pic = None

        if accepted:
            if user is None:
                await ctx.reply(embed=self.bot.buildEmbed(title=target[0], url="https://twitter.com/{}".format(target[0]), description=target[1], thumbnail=pic, color=self.color))
            else:
                await ctx.reply(embed=self.bot.buildEmbed(title=user.name, url="https://twitter.com/{}".format(target[0]), description=target[1], thumbnail=pic, color=self.color))
        elif user is None:
            await ctx.reply(embed=self.bot.buildEmbed(title="Error", description="`{}` not found".format(term), color=self.color))
        elif ctx.channel.is_nsfw():
            await ctx.reply(embed=self.bot.buildEmbed(title=user.name, url="https://twitter.com/{}".format(user.screen_name), thumbnail=pic, color=self.color))
        else:
            await ctx.reply(embed=self.bot.buildEmbed(title="NSFW protection", description="Check at your own risk\n[{}](https://twitter.com/{})".format(user.name, user.screen_name), color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True)
    async def reddit(self, ctx):
        """Post a link to /r/Granblue_en
        You wouldn't dare, do you?"""
        await ctx.reply(embed=self.bot.buildEmbed(title="/r/Granblue_en/", url="https://www.reddit.com/r/Granblue_en/", thumbnail="https://cdn.discordapp.com/attachments/354370895575515138/581522602325966864/lTgz7Yx_6n8VZemjf54viYVZgFhW2GlB6dlpj1ZwKbo.png", description="Disgusting :nauseated_face:", color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['leech'])
    async def leechlist(self, ctx):
        """Post a link to /gbfg/ leechlist collection"""
        await ctx.reply(embed=self.bot.buildEmbed(title="/gbfg/ Leechlist", description=self.bot.strings["leechlist()"], thumbnail="https://cdn.discordapp.com/attachments/354370895575515138/582191446182985734/unknown.png", color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['time', 'st', 'reset', 'gbf'])
    @commands.cooldown(2, 2, commands.BucketType.guild)
    async def granblue(self, ctx):
        """Post various Granblue Fantasy informations"""
        current_time = self.bot.getJST()
        description = "{:} Current Time is **{:02d}:{:02d} JST**".format(self.bot.getEmote('clock'), current_time.hour, current_time.minute)

        if self.bot.gbfversion is not None:
            description += "\n{} Version is `{}` (`{}`)".format(self.bot.getEmote('cog'), self.bot.gbfversion, self.bot.versionToDateStr(self.bot.gbfversion))

        reset = current_time.replace(hour=5, minute=0, second=0, microsecond=0)
        if current_time.hour >= reset.hour:
            reset += timedelta(days=1)
        d = reset - current_time
        description += "\n{} Reset in **{}**".format(self.bot.getEmote('mark'), self.bot.getTimedeltaStr(d))

        id = str(ctx.message.author.guild.id)
        if id in self.bot.st:
            st1 = current_time.replace(hour=self.bot.st[id][0], minute=0, second=0, microsecond=0)
            st2 = st1.replace(hour=self.bot.st[id][1])

            if current_time.hour >= st1.hour:
                st1 += timedelta(days=1)
            if current_time.hour >= st2.hour:
                st2 += timedelta(days=1)

            d = st1 - current_time
            if d.seconds >= 82800: description += "\n{} Strike times in {} **On going** ".format(self.bot.getEmote('st'), self.bot.getEmote('1'))
            else: description += "\n{} Strike times in {} **{}** ".format(self.bot.getEmote('st'), self.bot.getEmote('1'), self.bot.getTimedeltaStr(d))
            d = st2 - current_time
            if d.seconds >= 82800: description += "{} **On going**".format(self.bot.getEmote('2'))
            else: description += "{} **{}**".format(self.bot.getEmote('2'), self.bot.getTimedeltaStr(d))

        try:
            buf = self.getMaintenanceStatus()
            if len(buf) > 0: description += "\n" + buf
        except Exception as e:
            await self.bot.sendError("getMaintenanceStatus", str(e))

        try:
            cog = self.bot.get_cog('GBF_Access')
            if cog is not None:
                buf = await cog.getCurrentGacha()
                if len(buf) > 0:
                    description += "\n{} Current gacha ends in **{}**".format(self.bot.getEmote('SSR'), self.bot.getTimedeltaStr(buf[0], 2))
                    if buf[0] != buf[1]:
                        description += " (Spark period ends in **{}**)".format(self.bot.getTimedeltaStr(buf[1], 2))
        except Exception as e:
            await self.bot.sendError("getgachatime", str(e))

        try:
            if current_time < self.bot.stream['time']:
                description += "\n{} Stream starts in **{}**".format(self.bot.getEmote('crystal'), self.bot.getTimedeltaStr(self.bot.stream['time'] - current_time, 2))
        except:
            pass

        try:
            buf = self.bot.get_cog('GuildWar').getGWState()
            if len(buf) > 0: description += "\n" + buf
        except Exception as e:
            await self.bot.sendError("getgwstate", str(e))

        try:
            buf = self.bot.get_cog('DreadBarrage').getBarrageState()
            if len(buf) > 0: description += "\n" + buf
        except Exception as e:
            await self.bot.sendError("getBarrageState", str(e))

        try:
            buf = self.bot.get_cog('GuildWar').getNextBuff(ctx)
            if len(buf) > 0: description += "\n" + buf
        except Exception as e:
            await self.bot.sendError("getnextbuff", str(e))

        await ctx.send(embed=self.bot.buildEmbed(author={'name':"Granblue Fantasy", 'icon_url':"http://game-a.granbluefantasy.jp/assets_en/img/sp/touch_icon.png"}, description=description, color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['maint'])
    @commands.cooldown(2, 2, commands.BucketType.guild)
    async def maintenance(self, ctx):
        """Post GBF maintenance status"""
        try:
            description = self.getMaintenanceStatus()
            if len(description) > 0:
                await ctx.send(embed=self.bot.buildEmbed(author={'name':"Granblue Fantasy", 'icon_url':"http://game-a.granbluefantasy.jp/assets_en/img/sp/touch_icon.png"}, description=description, color=self.color))
            else:
                await ctx.send(embed=self.bot.buildEmbed(title="Granblue Fantasy", description="No maintenance in my memory", color=self.color))
        except Exception as e:
            await self.bot.sendError("getMaintenanceStatus", str(e))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['drive'])
    @isYou()
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def gdrive(self, ctx):
        """Post the (You) google drive
        (You) server only"""
        try:
            image = self.bot.get_guild(self.bot.ids['you_server']).icon_url
        except:
            image = ""
        await ctx.reply(embed=self.bot.buildEmbed(title="(You) Public Google Drive", description=self.bot.strings["gdrive()"], thumbnail=image, color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['arcarum', 'arca', 'oracle', 'evoker', 'astra', 'sandbox', 'veritas', 'newworld', 'luster'])
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def arcanum(self, ctx):
        """Post a link to my autistic Arcanum Sheet"""
        await ctx.reply(embed=self.bot.buildEmbed(title="Arcanum Tracking Sheet", description=self.bot.strings["arcanum()"], thumbnail="http://game-a.granbluefantasy.jp/assets_en/img_low/sp/assets/item/article/s/250{:02d}.jpg".format(random.randint(1, 74)), color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['eternals', 'transcendence', 'transc'])
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def eternal(self, ctx):
        """Post a link to my autistic Eternal Sheet"""
        await ctx.reply(embed=self.bot.buildEmbed(title="Eternal Transcendance Tracking Sheet", description=self.bot.strings["eternal()"], thumbnail="http://game-a.granbluefantasy.jp/assets_en/img/sp/assets/npc/s/30400{}.jpg".format(random.choice(['30000_04', '31000_04', '32000_03', '33000_03', '34000_03', '35000_03', '36000_03', '37000_03', '38000_03', '39000_03'])), color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['sparktracker'])
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def rollTracker(self, ctx):
        """Post a link to my autistic roll tracking Sheet"""
        await ctx.reply(embed=self.bot.buildEmbed(title="{} GBF Roll Tracker".format(self.bot.getEmote('crystal')), description=self.bot.strings["rolltracker()"], color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['gwskin', 'blueskin'])
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def stayBlue(self, ctx):
        """Post a link to my autistic blue eternal outfit grinding Sheet"""
        await ctx.reply(embed=self.bot.buildEmbed(title="5* Eternal Skin Farming Sheet", description=self.bot.strings["stayblue()"], color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['soldier'])
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def bullet(self, ctx):
        """Post a link to my bullet grind Sheet"""
        await ctx.reply(embed=self.bot.buildEmbed(title="Bullet Grind Sheet", description=self.bot.strings["bullet()"], color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['gbfgcrew', 'gbfgpastebin'])
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def pastebin(self, ctx):
        """Post a link to the /gbfg/ crew pastebin"""
        await ctx.reply(embed=self.bot.buildEmbed(title="/gbfg/ Guild Pastebin", description=self.bot.strings["pastebin()"], thumbnail="https://cdn.discordapp.com/attachments/354370895575515138/582191446182985734/unknown.png", color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['tracker'])
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def dps(self, ctx):
        """Post the custom Combat tracker"""
        await ctx.reply(embed=self.bot.buildEmbed(title="GBF Combat Tracker", description=self.bot.strings["dps()"], color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['raidfinder', 'python_raidfinder'])
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def pyfinder(self, ctx):
        """Post the (You) python raidfinder"""
        await ctx.reply(embed=self.bot.buildEmbed(title="(You) Python Raidfinder", description=self.bot.strings["pyfinder()"], color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True)
    @commands.cooldown(1, 20, commands.BucketType.guild)
    async def mizatube(self, ctx):
        """Post the owner youtube channel"""
        if 'mizatube()' in self.bot.strings:
            await ctx.reply(embed=self.bot.buildEmbed(title="Mizatube:tm:", description="[Link]({})".format(self.bot.strings['mizatube()']), footer="Subscribe ;)", color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['ubhl', 'ubahahl'])
    @commands.cooldown(1, 15, commands.BucketType.guild)
    async def ubaha(self, ctx):
        """Post the Ultimate Bahamut HL Triggers"""
        await ctx.reply(embed=self.bot.buildEmbed(title="Empyreal Ascension (Impossible)", url="https://gbf.wiki/Ultimate_Bahamut_(Raid)#impossible", description="**95%**{} Daedalus Wing (uplift)\n**85%**{} Deadly Flare (dispel)\n**80%**♦️ charge diamonds\n**75%**{} Virtuous Verse (swap)\n**70%**{} The Rage (local debuffs)\n**70-50%**♦️ charge diamonds in OD\n**55%**{} Deadly Flare (stone)\n**50 & 40**%{} Sirius (4x30% plain)\n**45 & 35**%▫️ Sirius\n**28%**♦️ charge diamonds\n**22%**{} Ultima Blast (dispel)\n**15%**{} Skyfall Ultimus\n**10% & 1%**▫️ Cosmic Collision\n**5%**{} Deadly Flare".format(self.bot.getEmote('wind'), self.bot.getEmote('fire'), self.bot.getEmote('earth'), self.bot.getEmote('light'), self.bot.getEmote('fire'), self.bot.getEmote('misc'), self.bot.getEmote('water'), self.bot.getEmote('dark'), self.bot.getEmote('dark')), footer="Stay blue", color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['darkrapture', 'rapture', 'faa', 'luci', 'lucihl', 'luciliushl'])
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def lucilius(self, ctx):
        """Post the Lucilius HL Triggers"""
        await ctx.reply(embed=self.bot.buildEmbed(title="Dark Rapture (Hard)", url="https://gbf.wiki/Lucilius_(Raid)#Impossible_.28Hard.29", fields = [{'name': "{} Black Wings".format(self.bot.getEmote('1')), 'value':'**N **{} Phosphosrus (single)\n**OD**{} Iblis (multi, debuffs)\n**OD, both**▫️ Paradise Lost (party)\n**Join**{} Paradise Lost (30K)\n**70%**▫️ Sephiroth (debuff wipe)\n**50%**{} Seven Trumpets (**12 Labors**)\n**1-6**{} increase damage [10M]\n**7**{} use superior element [2M plain]\n**8**{} nullify phalanx [OverChain]\n**9**{} heal [30 hits]\n**10**{} random debuff [10 debuffs]\n**11**{} dispel 2 buffs [trigger PL]\n**12**{} deal plain damage [all labors]'.format(self.bot.getEmote('lucilius'), self.bot.getEmote('lucilius'), self.bot.getEmote('misc'), self.bot.getEmote('labor'), self.bot.getEmote('labor'), self.bot.getEmote('labor'), self.bot.getEmote('labor'), self.bot.getEmote('labor'), self.bot.getEmote('labor'), self.bot.getEmote('labor'), self.bot.getEmote('labor'), self.bot.getEmote('labor'))}, {'name': "{} Lucilius".format(self.bot.getEmote('2')), 'value':'**95%**{} Phosphosrus (single)\n**85%**{} Axion (multi)\n**70%**♦️ charge diamonds\n**60%**{} Axion (**party**)\n**55%**♦️ charge diamonds\n**25%**{} Gopherwood Ark (racial check)\n**20 & 15%**{} Axion Apocalypse (multi)\n**10 & 3%**{} Paradise Lost (999k)\n\n*Click the title for more details*'.format(self.bot.getEmote('lucilius'), self.bot.getEmote('lucilius'), self.bot.getEmote('lucilius'), self.bot.getEmote('lucilius'), self.bot.getEmote('lucilius'), self.bot.getEmote('lucilius'))}], inline=True, footer="Your fate is over", color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['beelzebub', 'bubz'])
    @commands.cooldown(1, 15, commands.BucketType.guild)
    async def bubs(self, ctx):
        """Post the Beelzebub HL Triggers"""
        await ctx.reply(embed=self.bot.buildEmbed(title="Long Live the King", url="https://gbf.wiki/Beelzebub_(Raid)", description="**100% & OD**▫️ Chaoscaliber (party, stun) [30 hits]\n**N **▫️ Unisonic (multi, counter) [10M]\n**75, 60% & OD**▫️ Karma (summonless) [FC]\n**N **▫️ Black Flies (multi, slashed) [10M]\n**50%**{} Langelaan Field (4T, reflect 2K, doesn't attack) [5M+20M/death]\n**OD**▫️ Chaoscaliber (party x2, stun) [FC]\n**N **▫️ Just Execution (24 hits, -1T to buff/hit) [FC]\n**30 & 15%**▫️ Black Spear (party, defenless) [FC]\n**25 & 10%**▫️ Chaos Legion (party, 10k guarded) [FC]\n**King's Religion**{} Total turns reached 30xPlayer Count".format(self.bot.getEmote('misc'), self.bot.getEmote('misc')), footer="Qilin Fantasy", color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=["christmas", "anniversary", "anniv", "summer"])
    @commands.cooldown(3, 30, commands.BucketType.guild)
    async def stream(self, ctx, op : str = ""):
        """Post the stream text"""
        if len(self.bot.stream['content']) == 0:
            await ctx.send(embed=self.bot.buildEmbed(title="No event or stream available", color=self.color))
        elif op == "raw":
            msg = ""
            for c in self.bot.stream['content']:
                msg += c + '\n'
            await ctx.send('`' + msg + '`')
        else:
            title = self.bot.stream['content'][0]
            msg = ""
            current_time = self.bot.getJST()
            if self.bot.stream['time'] is not None:
                if current_time < self.bot.stream['time']:
                    d = self.bot.stream['time'] - current_time
                    cd = "{}".format(self.bot.getTimedeltaStr(d, 2))
                else:
                    cd = "On going!!"
            else:
                cd = ""
            for i in range(1, len(self.bot.stream['content'])):
                if cd != "" and self.bot.stream['content'][i].find('{}') != -1:
                    msg += self.bot.stream['content'][i].format(cd) + "\n"
                else:
                    msg += self.bot.stream['content'][i] + "\n"
            
            if cd != "" and title.find('{}') != -1:
                title = title.format(cd) + "\n"

            await ctx.send(embed=self.bot.buildEmbed(title=title, description=msg, color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=["event"])
    @commands.cooldown(3, 30, commands.BucketType.guild)
    async def schedule(self, ctx, raw : str = ""):
        """Post the GBF schedule"""
        if len(self.bot.schedule) == 0:
            await ctx.send(embed=self.bot.buildEmbed(title="No schedule available", color=self.color))
        else:
            l = len(self.bot.schedule)
            if raw != 'raw': l = l - (l%2) # need an even amount, skipping the last one if odd
            i = 0
            msg = ""
            c = self.bot.getJST()
            nx = None
            md = c.month * 100 + c.day
            while i < l:
                if raw == 'raw':
                    if i != 0: msg += ";"
                    else: msg += "`"
                    msg += self.bot.schedule[i]
                    i += 1
                else:
                    try: # checking if the event is on going (to bold it)
                        dates = self.bot.schedule[i].replace(' ', '').split('-')
                        ev_md = []
                        for di in range(0, len(dates)):
                            ev_md.append(int(dates[di].split('/')[0]) * 100 + int(dates[di].split('/')[1]))
                        if len(dates) == 2:
                            if ev_md[0] >= 1200 and ev_md[1] <= 100: ev_md[0] -= 1200
                            on_going = (md >= ev_md[0] and md <= ev_md[1])
                        else:
                            on_going = (md >= ev_md[0])
                    except:
                        on_going = False
                    # check if it's the next event in line
                    if not on_going:
                        try:
                            dates = self.bot.schedule[i].replace(' ', '').split('-')
                            evd = dates[0].split('/')
                            evt = c.replace(month=int(evd[0]), day=int(evd[1]), hour=18, minute=0, second=0, microsecond=0)
                            if evt > c and (nx is None or evt < nx):
                                nx = evt
                        except:
                            pass
                    if on_going: msg += "**"
                    if l > 12: # enable or not emotes (I have 6 numbered emotes, so 6 field max aka 12 elements in my array)
                        msg += "{} ▫️ {}".format(self.bot.schedule[i], self.bot.schedule[i+1])
                        i += 2
                    else:
                        msg += "{} {} ▫️ {}".format(self.bot.getEmote(str((i//2)+1)), self.bot.schedule[i], self.bot.schedule[i+1])
                        i += 2
                    if on_going: msg += "**"
                    msg += "\n"
            if raw == 'raw': msg += "`"
            else:
                if nx is not None and c < nx:
                    msg += "{} Next event approximately in **{}**\n".format(self.bot.getEmote('mark'), self.bot.getTimedeltaStr(nx - c, 2))
                try:
                    buf = self.getMaintenanceStatus()
                    if len(buf) > 0: msg += buf + '\n'
                except Exception as e:
                    await self.bot.sendError("getMaintenanceStatus", str(e))
                try:
                    current_time = self.bot.getJST()
                    if current_time < self.bot.stream['time']:
                        msg += "{} Stream starts in **{}**".format(self.bot.getEmote('crystal'), self.bot.getTimedeltaStr(self.bot.stream['time'] - current_time, 2))
                except:
                    pass
            await ctx.send(embed=self.bot.buildEmbed(title="🗓 Event Schedule {} {:%Y/%m/%d %H:%M} JST".format(self.bot.getEmote('clock'), self.bot.getJST()), url="https://twitter.com/granblue_en", color=self.color, description=msg))

    def strToInt(self, s): # convert string such as 1.2B to 1200000000
        try:
            return int(s)
        except:
            n = float(s[:-1]) # float to support for example 1.2B
            m = s[-1].lower()
            l = {'k':1000, 'm':1000000, 'b':1000000000}
            return int(n * l[m])

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['tokens'])
    @commands.cooldown(2, 10, commands.BucketType.guild)
    async def token(self, ctx, tok : str):
        """Calculate how many GW box you get from X tokens"""
        try:
            tok = self.strToInt(tok)
            if tok < 1 or tok > 9999999999: raise Exception()
            b = 0
            t = tok
            if tok >= 1600:
                tok -= 1600
                b += 1
            while b < 4 and tok >= 2400:
                tok -= 2400
                b += 1
            while b < 46 and tok >= 2000:
                tok -= 2000
                b += 1
            while b < 81 and tok >= 10000:
                tok -= 10000
                b += 1
            while tok >= 15000:
                tok -= 15000
                b += 1
            ex = math.ceil(t / 56.0)
            explus = math.ceil(t / 66.0)
            n90 = math.ceil(t / 83.0)
            n95 = math.ceil(t / 111.0)
            n100 = math.ceil(t / 168.0)
            n150 = math.ceil(t / 257.0)
            wanpan = math.ceil(t / 48.0)
            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="{} Token Calculator ▫️ {}".format(self.bot.getEmote('gw'), t), description="**{:,}** box(s) and **{:,}** leftover tokens\n**{:,}** EX (**{:,}** pots)\n**{:,}** EX+ (**{:,}** pots)\n**{:,}** NM90 (**{:,}** pots, **{:,}** meats)\n**{:,}** NM95 (**{:,}** pots, **{:,}** meats)\n**{:,}** NM100 (**{:,}** pots, **{:,}** meats)\n**{:,}** NM150 (**{:,}** pots, **{:,}** meats)\n**{:,}** NM100 join (**{:}** BP)".format(b, tok, ex, math.ceil(ex*30/75), explus, math.ceil(explus*30/75), n90, math.ceil(n90*30/75), n90*5, n95, math.ceil(n95*40/75), n95*10, n100, math.ceil(n100*50/75), n100*20, n150, math.ceil(n150*50/75), n150*20, wanpan, wanpan*3), color=self.color))
        except:
            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="Error", description="Invalid token number", color=self.color))
        await self.bot.cleanMessage(ctx, final_msg, 60)

    @commands.command(no_pm=True, cooldown_after_parsing=True)
    @commands.cooldown(2, 10, commands.BucketType.guild)
    async def box(self, ctx, box : int):
        """Calculate how many GW tokens you need"""
        try:
            if box < 1 or box > 999: raise Exception()
            t = 0
            b = box
            if box >= 1: t += 1600
            if box >= 2: t += 2400
            if box >= 3: t += 2400
            if box >= 4: t += 2400
            if box > 80:
                t += (box - 80) * 15000
                box = 80
            if box > 45:
                t += (box - 45) * 10000
                box = 45
            if box > 4:
                t += (box - 4) * 2000
            ex = math.ceil(t / 56.0)
            explus = math.ceil(t / 66.0)
            n90 = math.ceil(t / 83.0)
            n95 = math.ceil(t / 111.0)
            n100 = math.ceil(t / 168.0)
            n150 = math.ceil(t / 257.0)
            wanpan = math.ceil(t / 48.0)
            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="{} Token Calculator ▫️ {}".format(self.bot.getEmote('gw'), b), description="**{:,}** tokens needed\n\n**{:,}** EX (**{:,}** pots)\n**{:,}** EX+ (**{:,}** pots)\n**{:,}** NM90 (**{:,}** pots, **{:,}** meats)\n**{:,}** NM95 (**{:,}** pots, **{:,}** meats)\n**{:,}** NM100 (**{:,}** pots, **{:,}** meats)\n**{:,}** NM150 (**{:,}** pots, **{:,}** meats)\n**{:,}** NM100 join (**{:}** BP)".format(t, ex, math.ceil(ex*30/75), explus, math.ceil(explus*30/75), n90, math.ceil(n90*30/75), n90*5, n95, math.ceil(n95*40/75), n95*10, n100, math.ceil(n100*50/75), n100*20, n150, math.ceil(n150*50/75), n150*20, wanpan, wanpan*3), color=self.color))
        except:
            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="Error", description="Invalid box number", color=self.color))
        await self.bot.cleanMessage(ctx, final_msg, 60)

    @commands.command(no_pm=True, cooldown_after_parsing=True)
    @commands.cooldown(2, 10, commands.BucketType.guild)
    async def meat(self, ctx, meat : str):
        """Calculate how many GW honors you get"""
        try:
            meat = self.strToInt(meat)
            if meat < 5 or meat > 100000: raise Exception()
            nm90 = meat // 5
            nm95 = meat // 10
            nm100 = meat // 20
            nm150 = meat // 20
            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="{} Meat Calculator ▫️ {}".format(self.bot.getEmote('gw'), meat), description="**{:,}** NM90 or **{:}** honors\n**{:,}** NM95 or **{:}** honors\n**{:}** NM100 or **{:}** honors\n**{:,}** NM150 or **{:}** honors\n".format(nm90, self.honorFormat(nm90*260000), nm95, self.honorFormat(nm95*910000), nm100, self.honorFormat(nm100*2650000), nm150, self.honorFormat(nm150*4100000)), color=self.color))
        except:
            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="Error", description="Invalid meat number", color=self.color))
        await self.bot.cleanMessage(ctx, final_msg, 60)

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['honors'])
    @commands.cooldown(2, 10, commands.BucketType.guild)
    async def honor(self, ctx, target : str):
        """Calculate how many NM95 and 150 you need for your targeted honor"""
        try:
            target = self.strToInt(target)
            if target < 10000: raise Exception()
            honor = [0, 0, 0]
            ex = 0
            meat_per_ex_average = 4
            meat = 0
            total_meat = 0
            nm = [0, 0]
            day_target = [target * 0.2, target * 0.3] # sum = 0.5
            meat_use = [10, 20]
            honor_per_nm = [910000, 4100000]

            for i in [1, 0]:
                daily = 0
                while daily < day_target[i]:
                    if meat < meat_use[i]:
                        meat += meat_per_ex_average
                        total_meat += meat_per_ex_average
                        ex += 1
                        daily += 80800
                        honor[0] += 80800
                    else:
                        meat -= meat_use[i]
                        nm[i] += 1
                        daily += honor_per_nm[i]
                        honor[i+1] += honor_per_nm[i]

            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="{} Honor Planning ▫️ {} honors".format(self.bot.getEmote('gw'), self.honorFormat(target)), description="Preliminaries & Interlude ▫️ **{:,}** meats (around **{:,}** EX+ and **{:}** honors)\nDay 1 and 2 total ▫️ **{:,}** NM95 (**{:}** honors)\nDay 3 and 4 total ▫️ **{:,}** NM150 (**{:}** honors)".format(math.ceil(total_meat*2), ex*2, self.honorFormat(honor[0]*2), nm[0]*2, self.honorFormat(honor[1]*2), nm[1]*2, self.honorFormat(honor[2]*2)), footer="Assuming {} meats / EX+ on average".format(meat_per_ex_average), color=self.color))
        except:
            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="Error", description="Invalid honor number", color=self.color))
        await self.bot.cleanMessage(ctx, final_msg, 60)

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['friday'])
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def premium(self, ctx):
        """Post the time to the next Premium Friday"""
        c = self.bot.getJST()
        d = c
        last = None
        searching = True
        thumbnail = "https://cdn.discordapp.com/attachments/354370895575515138/584025273079562240/unknown.png"
        while searching:
            if d.weekday() == 4:
                last = d
            d = d + timedelta(seconds=86400)
            if last is not None and d.month != last.month:
                if c == last:
                    beg = last.replace(hour=15, minute=00, second=00)
                    end = c.replace(hour=23, minute=59, second=59) + timedelta(days=2, seconds=1)
                    if c >= beg and c < end:
                        end = end - c
                        await ctx.send(embed=self.bot.buildEmbed(title="{} Premium Friday".format(self.bot.getEmote('clock')), description="Premium Friday ends in **{}**".format(self.bot.getTimedeltaStr(end, 2)), url="http://game.granbluefantasy.jp", thumbnail=thumbnail, color=self.color))
                        return
                    elif c >= end:
                        pass
                    elif c < beg:
                        last = beg
                        searching = False
                else:
                    searching = False
        last = last.replace(hour=15, minute=00, second=00) - c
        await ctx.send(embed=self.bot.buildEmbed(title="{} Premium Friday".format(self.bot.getEmote('clock')), description="Premium Friday starts in **{}**".format(self.bot.getTimedeltaStr(last, 2)),  url="http://game.granbluefantasy.jp", thumbnail=thumbnail, color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['koregura', 'koregra'])
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def korekara(self, ctx):
        """Post the time to the next monthly dev post"""
        c = self.bot.getJST()
        try:
            if c < self.bot.stream['time']:
                target = self.bot.stream['time']
            else:
                raise Exception()
        except:
            if c.day == 1:
                if c.hour >= 12:
                    if c.month == 12: target = datetime(year=c.year+1, month=1, day=1, hour=12, minute=0, second=0, microsecond=0)
                    else: target = datetime(year=c.year, month=c.month+1, day=1, hour=12, minute=0, second=0, microsecond=0)
                else:
                    target = datetime(year=c.year, month=c.month, day=1, hour=12, minute=0, second=0, microsecond=0)
            else:
                if c.month == 12: target = datetime(year=c.year+1, month=1, day=1, hour=12, minute=0, second=0, microsecond=0)
                else: target = datetime(year=c.year, month=c.month+1, day=1, hour=12, minute=0, second=0, microsecond=0)
        delta = target - c
        await ctx.send(embed=self.bot.buildEmbed(title="{} Kore Kara".format(self.bot.getEmote('clock')), description="Release approximately in **{}**".format(self.bot.getTimedeltaStr(delta, 2)),  url="https://granbluefantasy.jp/news/index.php", thumbnail="http://game-a.granbluefantasy.jp/assets_en/img/sp/touch_icon.png", color=self.color))

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['crits', 'critical', 'criticals'])
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def crit(self, ctx, *, weapons : str = ""):
        """Calculate critical rate"""
        values = {'small10':2, 'small15':3, 'small20':4, 'medium10':5, 'medium15':6.5, 'medium20':7.5, 'big10':8, 'big15':10, 'big20':11, 'bigII15':12, 'wamdus':20, 'hercules':11.5, 'sephira':25}
        ts = {'small':'small15', 'med':'medium15', 'medium':'medium15', 'big':'big15', 'big2':'bigII15', 's10':'small10', 's15':'small15', 's20':'small20', 'm10':'medium10', 'm15':'medium15', 'm20':'medium20', 'med10':'medium10', 'med15':'medium15', 'med20':'medium20', 'b10':'big10', 's15':'big15', 's20':'big20', 'bII10':'bigII10', 'bII15':'bigII15', 'b210':'bigII10', 'b215':'bigII15', 'big210':'bigII10', 'big215':'bigII15', 'ameno':'medium20', 'gaebulg':'medium20', 'bulg':'medium20', 'bulge':'medium20', 'gae':'medium20', 'mjollnir':'small20', 'herc':'hercules', 'ecke':'medium15', 'eckesachs':'medium15', 'sachs':'medium15', 'blut':'small15', 'blutgang':'small15', 'indra':'medium15', 'ivory':'bigII15', 'ivoryark':'bigII15', 'ark':'bigII15', 'auberon':'medium15', 'aub':'medium15', 'taisai':'big15', 'pholia':'big15', 'galilei':'medium15', 'europa':'medium15', 'benedia':'medium15', 'thunderbolt':'big15', 'shibow':'big15', 'fawn':'big15', 'rein':'bigII15', 'babel':'bigII15', 'mandeb':'bigII15', 'bab-el-mandeb':'bigII15', 'arca':'sephira', 'arcarum':'sephira'}
        flats = ['wamdus', 'sephira']
        try:
            if weapons == "": raise Exception("Empty Parameter")
            mods = weapons.lower().split(' ')
            s1 = ""
            s2 = ""
            base = 0
            flat = 0
            for m in mods:
                if ts.get(m, m) in flats:
                    flat += values[ts.get(m, m)]
                    s2 += "{}+".format(values[ts.get(m, m)])
                else:
                    base += values[ts.get(m, m)]
                    s1 += "{}+".format(values[ts.get(m, m)])
            if s1 != "": s1 = "Boosted " + s1[:-1]
            if s2 != "":
                if s1 != "": s1 += ", "
                s1 = s1 + "Flat " + s2[:-1]
            msg =  "**Aura ▫️ Critical ▫️▫️ Aura ▫️ Critical**\n"
            msg += "140% ▫️ {:.1f}% ▫️▫️ 290% ▫️ {:.1f}%\n".format(min(base*2.4 + flat, 100), min(base*3.9 + flat, 100))
            msg += "150% ▫️ {:.1f}% ▫️▫️ 300% ▫️ {:.1f}%\n".format(min(base*2.5 + flat, 100), min(base*4 + flat, 100))
            msg += "160% ▫️ {:.1f}% ▫️▫️ 310% ▫️ {:.1f}%\n".format(min(base*2.6 + flat, 100), min(base*4.1 + flat, 100))
            msg += "170% ▫️ {:.1f}% ▫️▫️ 320% ▫️ {:.1f}%\n".format(min(base*2.7 + flat, 100), min(base*4.2 + flat, 100))
            msg += "280% ▫️ {:.1f}%\n".format(min(base*3.8 + flat, 100))
            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="Critical Calculator", description=msg.replace('.0%', '%').replace('100%', '**100%**'), footer=s1, color=self.color))
        except Exception as e:
            if str(e) == "Empty Parameter":
                modstr = ""
                for m in values:
                    modstr += "`{}`, ".format(m)
                for m in ts:
                    modstr += "`{}`, ".format(m)
                final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="Critical Calculator", description="**Posible modifiers:**\n" + modstr[:-2] + "\n\nModifiers must be separated by spaces" , color=self.color))
            else:
                final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="Critical Calculator", description="Error", footer=str(e), color=self.color))
        await self.bot.cleanMessage(ctx, final_msg, 40)

    def getSkillUpValue(self, type, sl): # calculate what's needed to raise a weapon skill level from a given skill level. return a list containing two dicts: first one contains the summary, second contains the details
        use = {}
        total = {}
        if type == 0:
            if sl >= 5: use['{}'.format(self.bot.getEmote('SR'))] = sl
            else: use['{}'.format(self.bot.getEmote('R'))] = sl*4
            total = use
        elif type == 1:
            if sl >= 15:
                use['{} **SL3**'.format(self.bot.getEmote('SSR'))] = sl // 3
                total['{}'.format(self.bot.getEmote('SSR'))] = use['{} **SL3**'.format(self.bot.getEmote('SSR'))]
                total['{}'.format(self.bot.getEmote('SR'))] = total['{}'.format(self.bot.getEmote('SSR'))] * 6
                if sl % 3 == 2:
                    use['{} **SL2**'.format(self.bot.getEmote('SSR'))] = 1
                    total['{}'.format(self.bot.getEmote('SSR'))] += 1
                    total['{}'.format(self.bot.getEmote('SR'))] += 2
                elif sl % 3 == 1:
                    use['{}'.format(self.bot.getEmote('SSR'))] = 1
                    total['{}'.format(self.bot.getEmote('SSR'))] += 1
            elif sl >= 12:
                use['{} **SL3**'.format(self.bot.getEmote('SSR'))] = 1
                total['{}'.format(self.bot.getEmote('SSR'))] = 1
                total['{}'.format(self.bot.getEmote('SR'))] = 6
            elif sl == 11:
                use['{} **SL2**'.format(self.bot.getEmote('SSR'))] = 1
                use['{}'.format(self.bot.getEmote('SR'))] = 2
                total['{}'.format(self.bot.getEmote('SSR'))] = 1
                total['{}'.format(self.bot.getEmote('SR'))] = 4
            elif sl >= 6:
                use['{} **SL2**'.format(self.bot.getEmote('SSR'))] = 1
                total['{}'.format(self.bot.getEmote('SSR'))] = 1
                total['{}'.format(self.bot.getEmote('SR'))] = 2
            elif sl == 5:
                use['{}'.format(self.bot.getEmote('SSR'))] = 1
                total = use
            else:
                use['{}'.format(self.bot.getEmote('SR'))] = sl * 2
                total = use
        elif type == 2:
            if sl == 19:
                use['{} **SL3**'.format(self.bot.getEmote('SSR'))] = 10
                use['{} **SL2**'.format(self.bot.getEmote('SSR'))] = 1
                total['{}'.format(self.bot.getEmote('SSR'))] = 11
                total['{}'.format(self.bot.getEmote('SR'))] = 62
            elif sl == 18:
                use['{} **SL3**'.format(self.bot.getEmote('SSR'))] = 10
                total['{}'.format(self.bot.getEmote('SSR'))] = 10
                total['{}'.format(self.bot.getEmote('SR'))] = 60
            elif sl == 17:
                use['{} **SL3**'.format(self.bot.getEmote('SSR'))] = 9
                use['{} **SL2**'.format(self.bot.getEmote('SSR'))] = 1
                total['{}'.format(self.bot.getEmote('SSR'))] = 10
                total['{}'.format(self.bot.getEmote('SR'))] = 54
            elif sl == 16:
                use['{} **SL3**'.format(self.bot.getEmote('SSR'))] = 9
                total['{}'.format(self.bot.getEmote('SSR'))] = 9
                total['{}'.format(self.bot.getEmote('SR'))] = 54
            elif sl == 15:
                use['{} **SL3**'.format(self.bot.getEmote('SSR'))] = 8
                use['{} **SL2**'.format(self.bot.getEmote('SSR'))] = 1
                total['{}'.format(self.bot.getEmote('SSR'))] = 9
                total['{}'.format(self.bot.getEmote('SR'))] = 48
            else:
                sl3 = sl // 3
                total['{}'.format(self.bot.getEmote('SSR'))] = 0
                if sl3 > 0:
                    use['{} **SL3**'.format(self.bot.getEmote('SSR'))] = sl3
                    total['{}'.format(self.bot.getEmote('SSR'))] += sl3
                    total['{}'.format(self.bot.getEmote('SR'))] = sl3 * 6
                if sl % 3 == 2:
                    use['{} **SL2**'.format(self.bot.getEmote('SSR'))] = 1
                    total['{}'.format(self.bot.getEmote('SSR'))] += 2
                    total['{}'.format(self.bot.getEmote('SR'))] = 2 + total.get('{}'.format(self.bot.getEmote('SR')), 0)
                elif sl % 3 == 1:
                    use['{}'.format(self.bot.getEmote('SSR'))] = 1
                    total['{}'.format(self.bot.getEmote('SSR'))] += 1
        return [use, total]

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['sl', 'skillup'])
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def skillLevel(self, ctx, type : str, current : int, next : int = -1):
        """Calculate what you need for skill up
        type: sr, ssr, magna, omega, astral, ex, xeno, bahamut, baha, ultima, serap, seraphic, draconic, draco, opus
        current: your weapon current skill level
        next: your targeted skill level"""
        types = {'sr':0, 'ssr':1, 'magna':1, 'omega':1, 'astral':1, 'ex':1, 'xeno':1, 'bahamut':2, 'baha':2, 'ultima':2, 'seraph':2, 'seraphic':2, 'draconic':2, 'draco':2, 'opus':2}
        type = type.lower()
        value = types.get(type, -1)
        if value == -1:
            value = 1
            type = 'ssr ({} was invalid)'.format(type)
        if next < current: next = current + 1
        if current < 1:
            await ctx.reply(embed=self.bot.buildEmbed(title="Skill Level Calculator", description="Current level can't be lesser than 1", url="https://gbf.wiki/Raising_Weapon_Skills", color=self.color))
            return
        if current >= 20 or (current >= 15 and value == 0):
            await ctx.reply(embed=self.bot.buildEmbed(title="Skill Level Calculator", description="Current level is too high", url="https://gbf.wiki/Raising_Weapon_Skills", color=self.color))
            return
        while next > 20 or (next > 15 and value == 0):
            next -= 1
        total = {}
        count = 0
        divide = next - current + 1
        if divide < 6: divide = 6
        else: divide = divide // 2
        fields = []
        while current < next: 
            if count % divide == 0: fields.append({'name':'Page {}'.format(self.bot.getEmote('{}'.format(len(fields)+1))), 'value':''})
            count += 1
            res = self.getSkillUpValue(value, current)
            current += 1
            fields[-1]['value'] += "To **SL{}**▫️".format(current)
            first = True
            for k in res[0]:
                if first: first = False
                else: fields[-1]['value'] += ", "
                fields[-1]['value'] += "{} {}".format(res[0][k], k)
            fields[-1]['value'] += "\n"
            # add total
            for k in res[1]:
                total[k] = total.get(k, 0) + res[1][k]
        msg = "**Total**▫️"
        first = True
        for k in total:
            if first: first = False
            else: msg += ", "
            msg += "{} {}".format(total[k], k)
        final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="Skill Level Calculator", description=msg, url="https://gbf.wiki/Raising_Weapon_Skills", fields=fields, inline=True, footer="type: {}".format(type), color=self.color))
        await self.bot.cleanMessage(ctx, final_msg, 60)

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=["doom", "doompost", "magnafest", "magnafes", "campaign", "brick", "bar", "sunlight", "stone", "suptix", "surprise", "evolite", "fugdidmagnafeststart", "alivegame", "alive"])
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def deadgame(self, ctx):
        """Give the time elapsed of various GBF related releases"""
        msg = ""
        wiki_checks = ["Category:Campaign", "Surprise_Special_Draw_Set", "Damascus_Ingot", "Gold_Brick", "Sunlight_Stone", "Sephira_Evolite"]
        regexs = ["<td>(\\d+ days)<\\/td>\\s*<td><span class=\"image_link\"><a href=\"/Four_Symbols_Stone\"", "<td>(\\d+ days)<\\/td>\\s*<td>Time since last", "<td>(-\\d+ days)<\\/td>\\s*<td>Time since last", "<td>(\\d+ days)<\\/td>\\s*<td>Time since last", "<td>(\\d+ days)<\\/td>\\s*<td style=\"text-align: left;\">Time since last", "<td>(\\d+ days)<\\/td>\\s*<td style=\"text-align: center;\">\\?\\?\\?<\\/td>\\s*<td style=\"text-align: left;\">Time since last", "<td>(\\d+ days)<\\/td>\\s*<td style=\"text-align: center;\">\\?\\?\\?<\\/td>\\s*<td style=\"text-align: left;\">Time since last ", "<td style=\"text-align: center;\">\\?\\?\\?<\\/td>\\s*<td>(\\d+ days)<\\/td>\\s*"]
        for w in wiki_checks:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://gbf.wiki/{}".format(w)) as r:
                    if r.status == 200:
                        t = await r.text()
                        for r in regexs:
                            m = re.search(r, t)
                            if m:
                                msg += "**{}** since the last {}\n".format(m.group(1), w.replace("_", " ").replace("Category:", ""))
                                break

        # grand (for memes, might remove later)
        c = self.bot.getJST()
        grands = {
            "Water": c.replace(year=2018, month=10, day=17, hour=19, minute=0, second=0, microsecond=0),
            "Wind": c.replace(year=2021, month=4, day=30, hour=19, minute=0, second=0, microsecond=0)
        }
        for e in grands:
            msg += "**{} days** since the last {} Grand\n".format(self.bot.getTimedeltaStr(c - grands[e], 3).split('d')[0], e)

        if msg != "":
            final_msg = await ctx.send(embed=self.bot.buildEmbed(author={'name':"Granblue Fantasy", 'icon_url':"http://game-a.granbluefantasy.jp/assets_en/img/sp/touch_icon.png"}, description=msg, color=self.color))
        else:
            final_msg = await ctx.send(embed=self.bot.buildEmbed(title="Error", description="Unavailable", color=self.color))
        await self.bot.cleanMessage(ctx, final_msg, 30)

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['setcrystal', 'setspark'])
    @commands.cooldown(30, 30, commands.BucketType.guild)
    async def setRoll(self, ctx, crystal : int, single : int = 0, ten : int = 0):
        """Set your roll count"""
        id = str(ctx.message.author.id)
        try:
            if crystal < 0 or single < 0 or ten < 0:
                raise Exception('Negative numbers')
            if crystal > 500000 or single > 1000 or ten > 100:
                raise Exception('Big numbers')
            if crystal + single + ten == 0: 
                if id in self.bot.spark[0]:
                    self.bot.spark[0].pop(id)
            else:
                self.bot.spark[0][id] = [crystal, single, ten, datetime.utcnow()]
            self.bot.savePending = True
            try:
                await self.bot.callCommand(ctx, 'seeRoll')
            except Exception as e:
                final_msg = await ctx.reply(embed=self.bot.buildEmbed(author={'name':title, 'icon_url':member.avatar_url}, description="**{} {} {} {} {} {}**".format(self.bot.getEmote("crystal"), crystal, self.bot.getEmote("singledraw"), single, self.bot.getEmote("tendraw"), ten), color=self.color))
                await self.bot.sendError('setRoll', str(e), 'B')
        except Exception as e:
            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="Error", description="Give me your number of crystals, single tickets and ten roll tickets, please", color=self.color, footer="setRoll <crystal> [single] [ten]"))
        try:
            await self.bot.cleanMessage(ctx, final_msg, 30)
        except:
            pass

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=['seecrystal', 'seespark'])
    @commands.cooldown(30, 30, commands.BucketType.guild)
    async def seeRoll(self, ctx, member : discord.Member = None):
        """Post your roll count"""
        if member is None: member = ctx.author
        id = str(member.id)
        try:
            # get the roll count
            if id in self.bot.spark[0]:
                s = self.bot.spark[0][id]
                if s[0] < 0 or s[1] < 0 or s[2] < 0:
                    raise Exception('Negative numbers')
                r = (s[0] / 300) + s[1] + s[2] * 10
                fr = math.floor(r)
                if len(s) > 3: timestamp = s[3]
                else: timestamp = None
            else:
                r = 0
                fr = 0
                s = None
                timestamp = None

            # calculate estimation
            # note: those numbers are from my own experimentation
            month_min = [80, 80, 200, 80, 80, 80, 80, 250, 90, 80, 80, 160]
            month_max = [60, 60, 120, 60, 60, 60, 60, 140, 60, 60, 60, 110]
            month_day = [31.0, 28.25, 31.0, 30.0, 31.0, 30.0, 31.0, 31.0, 30.0, 31.0, 30.0, 31.0]

            # get current day
            if timestamp is None: now = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            else: now = timestamp.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            t_min = now
            t_max = now
            r_min = r % 300
            r_max = r_min
            expected = [month_max[now.month-1], month_min[now.month-1]]
            while r_min < 300 or r_max < 300: # increase the date until we reach the 300 target for both estimation
                if r_min < 300:
                    m = (t_min.month-1) % 12
                    r_min += month_min[m] / month_day[m]
                    t_min += timedelta(days=1)
                if r_max < 300:
                    m = (t_max.month-1) % 12
                    r_max += month_max[m] / month_day[m]
                    t_max += timedelta(days=1)

            # roll count text
            title = "{} has {} roll".format(member.display_name, fr)
            if fr != 1: title += "s"
            # sending
            if s is None:
                final_msg = await ctx.reply(embed=self.bot.buildEmbed(author={'name':title, 'icon_url':member.avatar_url}, description="Update your rolls with the `setRoll` command", footer="Next spark between {} and {} from 0 rolls".format(t_min.strftime("%y/%m/%d"), t_max.strftime("%y/%m/%d")), color=self.color))
            else:
                final_msg = await ctx.reply(embed=self.bot.buildEmbed(author={'name':title, 'icon_url':member.avatar_url}, description="**{} {} {} {} {} {}**\n*Expecting {} to {} rolls in {}*".format(self.bot.getEmote("crystal"), s[0], self.bot.getEmote("singledraw"), s[1], self.bot.getEmote("tendraw"), s[2], expected[0], expected[1], now.strftime("%B")), footer="Next spark between {} and {}".format(t_min.strftime("%y/%m/%d"), t_max.strftime("%y/%m/%d")), timestamp=timestamp, color=self.color))
        except Exception as e:
            final_msg = await ctx.reply(embed=self.bot.buildEmbed(title="Error", description="I warned my owner", color=self.color, footer=str(e)))
            await self.bot.sendError('seeRoll', str(e))
        await self.bot.cleanMessage(ctx, final_msg, 30)

    @commands.command(no_pm=True, cooldown_after_parsing=True, aliases=["sparkranking", "hoarders"])
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def rollRanking(self, ctx):
        """Show the ranking of everyone saving for a spark in the server
        You must use $setRoll to set/update your roll count"""
        try:
            ranking = {}
            guild = ctx.message.author.guild
            for m in guild.members:
                id = str(m.id)
                if id in self.bot.spark[0]:
                    if id in self.bot.spark[1]:
                        continue
                    s = self.bot.spark[0][id]
                    if s[0] < 0 or s[1] < 0 or s[2] < 0:
                        continue
                    r = (s[0] / 300) + s[1] + s[2] * 10
                    if r > 1500:
                        continue
                    ranking[id] = r
            if len(ranking) == 0:
                final_msg = await ctx.send(embed=self.bot.buildEmbed(title="The ranking of this server is empty"))
                return
            ar = -1
            i = 0
            emotes = {0:self.bot.getEmote('SSR'), 1:self.bot.getEmote('SR'), 2:self.bot.getEmote('R')}
            msg = ""
            top = 15
            for key, value in sorted(ranking.items(), key = itemgetter(1), reverse = True):
                if i < top:
                    fr = math.floor(value)
                    msg += "**#{:<2}{} {}** with {} roll".format(i+1, emotes.pop(i, "▫️"), guild.get_member(int(key)).display_name, fr)
                    if fr != 1: msg += "s"
                    msg += "\n"
                if key == str(ctx.message.author.id):
                    ar = i
                    if i >= top: break
                i += 1
                if i >= 100:
                    break
            if ar >= top: footer = "You are ranked #{}".format(ar+1)
            elif ar == -1: footer = "You aren't ranked ▫️ You need at least one roll to be ranked"
            else: footer = ""
            final_msg = await ctx.send(embed=self.bot.buildEmbed(title="{} Spark ranking of {}".format(self.bot.getEmote('crown'), guild.name), color=self.color, description=msg, footer=footer, thumbnail=guild.icon_url))
        except Exception as e:
            final_msg = await ctx.send(embed=self.bot.buildEmbed(title="Sorry, something went wrong :bow:", footer=str(e)))
            await self.bot.sendError("rollRanking", str(e))
        await self.bot.cleanMessage(ctx, final_msg, 30)