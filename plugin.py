# -*- coding: utf-8 -*-
# {{{ LICENSE
###
# Copyright (c) 2006, Ilya Kuznetsov
# Copyright (c) 2008, Kevin Funk
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# }}}

### {{{ imports
import sys
import supybot.utils as utils
from supybot.commands import *
import supybot.conf as conf
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.ircmsgs as ircmsgs
import supybot.callbacks as callbacks
import supybot.world as world

import re

import urllib2
#from urllib import quote_plus
from xml.dom import minidom
import urllib
from time import time
from BeautifulSoup import BeautifulSoup

from LastFMDB import *
### }}}

class LastFM(callbacks.Plugin):
    # {{{ vars
    BASEURL = "http://ws.audioscrobbler.com/1.0/user"
    APIKEY = "7f11b8c4505415d7b9059339b47812d5" # FIXME: Get own key
    APIURL = "http://ws.audioscrobbler.com/2.0/?api_key=%s&" % APIKEY
    # }}}

    # {{{ system functions
    def __init__(self, irc):
        self.__parent = super(LastFM, self)
        self.__parent.__init__(irc)
        self.db = LastFMDB(dbfilename)
        world.flushers.append(self.db.flush)

    def die(self):
        if self.db.flush in world.flushers:
            world.flushers.remove(self.db.flush)
        self.db.close()
        self.__parent.die()
    # }}}

    # {{{ lastfm
    def lastfm(self, irc, msg, args, method, optionalId):
        """<method> [<id>]

        Lists LastFM info where <method> is in
        [friends, neighbours, profile, recenttracks, tags, topalbums,
        topartists, toptracks].
        Set your LastFM ID with the set method (default is your current nick)
        or specify <id> to switch for one call.
        """

        id = (optionalId or self.db.getId(msg.nick) or msg.nick)
        channel = msg.args[0]
        maxResults = self.registryValue("maxResults", channel)
        method = method.lower()

        try:
            f = urllib2.urlopen("%s/%s/%s.txt" % (self.BASEURL, id, method))
        except urllib2.HTTPError:
            irc.error("Unknown ID (%s) or unknown method (%s)"
                    % (msg.nick, method))
            return


        lines = f.read().split("\n")
        content = map(lambda s: s.split(",")[-1], lines)

        irc.reply("%s's %s: %s (with a total number of %i entries)"
                % (id, method, ", ".join(content[0:maxResults]),
                    len(content)))

    lastfm = wrap(lastfm, ["something", optional("something")])
    # }}}

    # {{{ np
    def np(self, irc, msg, args, optionalId):
        """[<id>]

        Announces the now playing track of the specified LastFM ID.
        Set your LastFM ID with the set method (default is your current nick)
        or specify <id> to switch for one call.
        """

        id = (self.db.getId(optionalId) or optionalId or self.db.getId(msg.nick) or msg.nick)
        if msg.nick.startswith("stoic") and not self.db.getId(msg.nick):
            id = "pentax_"
        channel = msg.args[0]
        showColours = self.registryValue("showColours", channel)
        trackInfo = self.registryValue("showTrackInfo", channel)
        showTags = self.registryValue("showTags", channel)

        try:
            f = urllib2.urlopen("%s&method=user.getrecenttracks&user=%s"
                    % (self.APIURL, id))
        except urllib2.HTTPError,e:
            irc.error("Unknown ID (%s)! Also, \"%s\"" % (id,e))
            return

        try:
            xml = minidom.parse(f).getElementsByTagName("recenttracks")[0]
        except IndexError:
            irc.error("Something broke, or you ain't listened to any tracks lol.")
            return
        user = xml.getAttribute("user")
        try:
            t = xml.getElementsByTagName("track")[0] # most recent track
        except IndexError,e:
            irc.error("No tracks or something for %s lol or maybe it's \"%s\"" % (id,e))
            return
        isNowplaying = (t.getAttribute("nowplaying") == "true")
        artist = t.getElementsByTagName("artist")[0].firstChild.data
        track = t.getElementsByTagName("name")[0].firstChild.data
        try:
            album = " ["+t.getElementsByTagName("album")[0].firstChild.data+"]"
        except AttributeError:
            album = ""

        artist2 = urllib.quote_plus(artist.encode("utf8"))
        track2 = urllib.quote_plus(track.encode("utf8"))

        # Play count and shit
        try:
            herp = urllib2.urlopen("%s&method=track.getInfo&username=%s&artist=%s&track=%s"
                    % (self.APIURL, id, artist2, track2))
            playinfo = minidom.parse(herp).getElementsByTagName("track")[0]
            playcount = playinfo.getElementsByTagName("playcount")[0].firstChild.data
            listenercount = playinfo.getElementsByTagName("listeners")[0].firstChild.data
            userloved = playinfo.getElementsByTagName("userloved")[0].firstChild.data
        except (IndexError, urllib2.HTTPError):
            trackInfo = False

        try:
            userplaycount = playinfo.getElementsByTagName("userplaycount")[0].firstChild.data
        except IndexError:
            userplaycount = 0

        # tags
        tags = []
        #if album != "":
            #thetags = urllib2.urlopen("%s&method=album.getTopTags&artist=%s&album=%s&autocorrect=1"
                    #% ( self.APIURL,artist2,urllib.quote_plus(t.getElementsByTagName("album")[0].firstChild.data)))
        #else:
        if True:
            try:
                thetags = urllib2.urlopen("%s&method=artist.getTopTags&artist=%s" % (self.APIURL,artist2))
                toptags = minidom.parse(thetags).getElementsByTagName("toptags")[0]
            except IndexError: 
                toptags = []
        for item in range(3):
            try:
                tags.append(toptags.getElementsByTagName("tag")[item].getElementsByTagName("name")[0].firstChild.data)
            except IndexError:
                break
        if len(tags) == 0:
            isTagged = False
        else:
            isTagged = True

        if showColours:
            if isNowplaying:
                output = ('\x038%s\x03 is listening to "\x0310%s\x03" by \x0312%s\x0313%s\x03' % (user, track, artist, album)).encode("utf8")
            else:
                time = int(t.getElementsByTagName("date")[0].getAttribute("uts"))
                output = ('\x038%s\x03 listened to "\x0310%s\x03" by \x0312%s\x0313%s\x03 about \x0315%s\x03' % (user, track, artist, album, self._formatTimeago(time))).encode("utf8")
            if trackInfo == True:
                if userloved == "1":
                    output += (' \x035%s\x03. %s plays by \x038%s\x03, %s plays by %s listeners.' % (u'♥', userplaycount, user, playcount, listenercount)).encode("utf8")
                else:
                    output += ('. %s plays by \x038%s\x03, %s plays by %s listeners.' % (userplaycount, user, playcount, listenercount)).encode("utf8")
            if showTags == True:
                if isTagged == True:
                    output += " ("
                    for i,item in enumerate(tags):
                        output += ("\x0307%s\x03" % item).encode("utf8")
                        if i != (len(tags)-1):
                            output += ", "
                    output += ")"
                else:
                    output += (' (\x037%s\x03)' % ("no tags")).encode("utf8")
        else:
            if isNowplaying:
                output = ('%s is listening to "%s" by %s%s' % (user, track, artist, album)).encode("utf8")
            else:
                time = int(t.getElementsByTagName("date")[0].getAttribute("uts"))
                output = ('%s listened to "%s" by %s%s about %s' % (user, track, artist, album, self._formatTimeago(time))).encode("utf8")
            if trackInfo == True:
                if userloved == "1":
                    output += (' %s. %s plays by %s, %s plays by %s listeners.' % (u'♥', userplaycount, user, playcount, listenercount)).encode("utf8")
                else:
                    output += ('. %s plays by %s, %s plays by %s listeners.' % (userplaycount, user, playcount, listenercount)).encode("utf8")
            if showTags == True:
                if isTagged == True:
                    output += " ("
                    for i,item in enumerate(tags):
                        output += ("%s" % item).encode("utf8")
                        if i != (len(tags)-1):
                            output += ", "
                    output += ")"
                else:
                    output += (' (%s)' % ("no tags")).encode("utf8")

        irc.reply(output)

    np = wrap(np, [optional("something")])
    # }}}

    # {{{ set
    def set(self, irc, msg, args, newId):
        """<id>

        Sets the LastFM ID for the caller and saves it in a database.
        """

        self.db.set(msg.nick, newId)

        irc.reply("LastFM ID changed.")
        self.profile(irc, msg, args)

    set = wrap(set, ["something"])
    # }}}

    # {{{ profile
    def profile(self, irc, msg, args, optionalId):
        """[<id>]

        Prints the profile info for the specified LastFM ID.
        Set your LastFM ID with the set method (default is your current nick)
        or specify <id> to switch for one call.
        """

        id = (optionalId or self.db.getId(msg.nick) or msg.nick)

        try:
            f = urllib2.urlopen("%s/%s/profile.xml" % (self.BASEURL, id))
        except urllib2.HTTPError:
            irc.error("Unknown user (%s)" % id)
            return

        xml = minidom.parse(f).getElementsByTagName("profile")[0]
        keys = "realname registered age gender country playcount".split()
        profile = tuple([self._parse(xml, node) for node in keys])
        url = ('http://www.last.fm/user/%s' % id)

        output = (("%s (realname: %s) registered on %s; age: %s / %s; \
Country: %s; Tracks played: %s" % ((id,) + profile)).encode("utf8"))
        irc.reply("%s [ %s ]" % (output,url))

    profile = wrap(profile, [optional("something")])
    # }}}

    # {{{ compare
    def compare(self, irc, msg, args, id1, optionalId):
        """<id1> [<optionalId>]

        Compare <id1>'s taste with <optionalId>'s or your current LastFM ID's taste.
        """

        channel = msg.args[0]
        showColours = self.registryValue("showColours", channel)
        id2 = (self.db.getId(optionalId) or optionalId or self.db.getId(msg.nick) or msg.nick)
        id1 = (self.db.getId(id1) or id1)

        try:
            f = urllib2.urlopen("%s&method=tasteometer.compare&type1=user&type2=user&value1=%s&value2=%s" % (self.APIURL, id1, id2))
        except urllib2.HTTPError:
            irc.error("Unknown ID (%s or %s)" % (id1, id2))
            #self.info.log("%s&method=tasteometer.compare&type1=user&type2=user&value1=%s&value2=%s" % (self.APIURL, id1, id2))
            #sys.stderr.write("%s&method=tasteometer.compare&type1=user&type2=user&value1=%s&value2=%s" % (self.APIURL, id1, id2))
            return

        xml = minidom.parse(f).getElementsByTagName("comparison")[0]
        score = float(xml.getElementsByTagName("score")[0].firstChild.data)
        artists = xml.getElementsByTagName("artist")
        artist_names = [artist.getElementsByTagName("name")[0].firstChild.data
                       for artist in artists]
        output = ""
        if showColours:
            if score*100 == -100.0:
                output += ("We're recharging the batteries of the taste-o-meter! ごめん！")
            else:
                output += ('\x0308%s\x03 and \x0308%s\x03 have \x0304%.3f%%\x03 music compatibility!' % (id1, id2, score*100))
                if score != 0:
                    output += (' Artists they share include: \x0312%s\x03' % ("\x03, \x0312".join(artist_names))).encode("utf8")
        else:
            if score*100 == -100.0:
                output += ("We're recharging the batteries of the taste-o-meter! ごめん！")
            else:
                output += ('%s and %s have %.3f%% music compatibility!' % (id1, id2, score*100))
                if score != 0:
                    output += (' Artists they share include: %s' % (", ".join(artist_names))).encode("utf8")
        irc.reply(output)
    
    compare = wrap(compare, ["something", optional("something")])
    # }}}

    # {{{ artist
    def artist(self, irc, msg, args, query):
        """<query>

        Searches last.fm for artist <query>.
        """

        id = (self.db.getId(msg.nick) or msg.nick)
        channel = msg.args[0]
        showColours = self.registryValue("showColours", channel)
        artist = urllib.quote_plus(query)
        isTagged = True
        placeAndDates = True
        userPlayed = True

        try:
            f = urllib2.urlopen("%s&method=artist.getInfo&autocorrect=1&artist=%s&username=%s"
                    % (self.APIURL, artist, id))
        except urllib2.HTTPError:
            irc.error("Unknown artist %s or something lol" % artist)
            return
        
        xml = minidom.parse(f).getElementsByTagName("artist")[0]
        name = xml.getElementsByTagName("name")[0].firstChild.data
        url = xml.getElementsByTagName("url")[0].firstChild.data
        listenercount = xml.getElementsByTagName("stats")[0].getElementsByTagName("listeners")[0].firstChild.data
        playcount = xml.getElementsByTagName("stats")[0].getElementsByTagName("playcount")[0].firstChild.data
        bio = xml.getElementsByTagName("bio")[0]

        try:
            userplaycount = xml.getElementsByTagName("userplaycount")[0].firstChild.data
        except IndexError:
            userPlayed = False

        try:
            placeformed = bio.getElementsByTagName("placeformed")[0].firstChild.data
            formationlist = bio.getElementsByTagName("formationlist")[0].getElementsByTagName("formation")[0]
            yearfrom = bio.getElementsByTagName("yearformed")[0].firstChild.data
            try:
                yearto = formationlist.getElementsByTagName("yearto")[0].firstChild.data
            except IndexError:
                yearto = "Present"
            except AttributeError:
                yearto = "Present"
        except IndexError:
            placeAndDates = False
        
        tags = []
        toptags = xml.getElementsByTagName("tags")[0]
        for item in range(3):
            try:
                tags.append(toptags.getElementsByTagName("tag")[item].getElementsByTagName("name")[0].firstChild.data)
            except IndexError:
                break
        if len(tags) == 0:
            isTagged = False

        if showColours:
            output = ("\x0312%s\x03" % name)
            if placeAndDates:
                output += (" [\x0305%s\x03 - \x0305%s\x03, \x038%s\x03]" % (yearfrom, yearto, placeformed))
            if isTagged:
                output += " ("
                for i in range(len(tags)):
                    output += ("\x0307%s\x03" % tags[i])
                    if i != (len(tags)-1):
                        output += ", "
                output += ")"
            if not userPlayed:
                userplaycount = 0
            output += (' %s plays by \x038%s\x03, %s plays by %s listeners.' % (userplaycount, id, playcount, listenercount)).encode("utf8")
            output += (" %s" % url)
        else:
            output = ("%s" % name)
            if placeAndDates:
                output += (" [%s - %s, %s]" % (yearfrom, yearto, placeformed))
            if isTagged:
                output += " ("
                for i in range(len(tags)):
                    output += ("%s" % tags[i])
                    if i != (len(tags)-1):
                        output += ", "
                output += ")"
            if not userPlayed:
                userplaycount = 0
            output += (' %s plays by %s, %s plays by %s listeners.' % (userplaycount, id, playcount, listenercount)).encode("utf8")
            output += (" %s" % url)

        irc.reply(output)

    artist = wrap(artist, ['text'])
    # }}}

    #{{{ tag
    def tag(self, irc, msg, args, query):
        """<tag>
        Displays some info about <tag>
        """

        channel = msg.args[0]
        showColours = self.registryValue("showColours", channel)
        tag = urllib.quote_plus(query)
        summaryLength = 230
        numArtists = 5
        try:
            f = urllib2.urlopen("%s&method=tag.getInfo&tag=%s" % (self.APIURL, tag))
            j = urllib2.urlopen("%s&method=tag.getTopArtists&tag=%s&limit=%s" 
                    % (self.APIURL, tag, numArtists))
        except urllib2.HTTPError:
            irc.error("Unknown tag %s or something lol" % tag)
            return
        except urllib2.URLError:
            irc.error("Time out lol")
            return

        # tag info
        xml = minidom.parse(f).getElementsByTagName("tag")[0]
        try:
            name = xml.getElementsByTagName("name")[0].firstChild.data.encode("utf8")
            url = xml.getElementsByTagName("url")[0].firstChild.data.encode("utf8")
            taggings = xml.getElementsByTagName("taggings")[0].firstChild.data
        except IndexError:
            irc.error("Something broke!")
            return
        try:
            summary = xml.getElementsByTagName("summary")[0].firstChild.data
        except IndexError:
            summary = ""
            
        if summary != None and summary != "":
            summary = str(BeautifulSoup(summary, convertEntities=BeautifulSoup.HTML_ENTITIES))
            # I janked these lines from BTN's DeepThroat's lastfm plugin
            summary = re.sub("\<[^<]+\>", "", summary)
            summary = re.sub("\s+", " ", summary)
            summary = summary[:summaryLength] + "..." if (summary[:summaryLength] != summary) else summary
            summary += " "
            summary = unicode(summary, errors='ignore')

        # top artist info
        xml2 = minidom.parse(j).getElementsByTagName("topartists")[0]

        topArtists = []
        for i in range(numArtists):
            try:
                topArtists.append(xml2.getElementsByTagName("name")[i].firstChild.data)
            except IndexError:
                break
        if len(topArtists) == 0:
            topArtists.append("No top artists")

        # process output
        output = ""
        if showColours:
            output += (u"\x0308%s\x03 (\x0304%s\x03 taggings): %s" 
                    % (name.capitalize(), taggings, summary))
            if topArtists[0] != "No top artists":
                output += "Top Artists: "
            for i,item in enumerate(topArtists):
                output += ("\x0312%s\x03" % item)
                if i != (len(topArtists)-1):
                    output += ", "
            output += (" [ %s ]" % url)
        else:
            output += ("%s (%s taggings): %s" 
                    % (name.capitalize(), taggings, summary))
            if topArtists[0] != "No top artists":
                output += "Top Artists: "
            for i,item in enumerate(topArtists):
                output += ("%s" % item)
                if i != (len(topArtists)-1):
                    output += ", "
            output += (" [ %s ]" % url)
        irc.reply(output)

    tag = wrap(tag, ['text'])

    #}}}

    # {{{ plays
    def plays(self, irc, msg, args, query):
        """[-user <user>] <query>

        Displays <user> or self plays for artist <query>.
        """

        channel = msg.args[0]
        showColours = self.registryValue("showColours", channel)

        id = (self.db.getId(msg.nick) or msg.nick)

        specificUser = True
        theList = query.split(' ')
        try:
            userIndex = theList.index('-user')
        except ValueError:
            specificUser = False

        if specificUser:
            try:
                user = theList[userIndex+1]
            except IndexError:
                irc.error("you have to put user after -user, dummy")
                return
            id = (self.db.getId(user) or user)
            band = theList[:theList.index("-user")] + theList[theList.index("-user")+2:]
            query = ' '.join(band)
            

        artist = urllib.quote_plus(query)
        userPlayed = True

        try:
            f = urllib2.urlopen("%s&method=artist.getInfo&autocorrect=1&artist=%s&username=%s"
                    % (self.APIURL, artist, id))
        except urllib2.HTTPError:
            irc.error("Unknown artist %s or something lol" % artist)
            return
        
        xml = minidom.parse(f).getElementsByTagName("artist")[0]
        try:
            name = xml.getElementsByTagName("name")[0].firstChild.data
            listenercount = xml.getElementsByTagName("stats")[0].getElementsByTagName("listeners")[0].firstChild.data
            playcount = xml.getElementsByTagName("stats")[0].getElementsByTagName("playcount")[0].firstChild.data
        except IndexError:
            irc.error("Can't find artist %s! :O" % artist)
            return

        try:
            userplaycount = xml.getElementsByTagName("userplaycount")[0].firstChild.data
        except IndexError:
            userPlayed = False

        if showColours:
            output = ("\x0312%s\x03" % name)
            if not userPlayed:
                userplaycount = 0
            output += (': %s plays by \x038%s\x03, %s plays by %s listeners.' % (userplaycount, id, playcount, listenercount)).encode("utf8")
        else:
            output = ("%s" % name)
            if not userPlayed:
                userplaycount = 0
            output += (': %s plays by %s, %s plays by %s listeners.' % (userplaycount, id, playcount, listenercount)).encode("utf8")

        irc.reply(output)

    plays = wrap(plays, ['text'])
    # }}}

    # {{{ similar
    def similar(self, irc, msg, args, query):
        """<artist>

        Shows artists similar to <artist>
        """

        channel = msg.args[0]
        showColours = self.registryValue("showColours",channel)
        artist = urllib.quote_plus(query)
        limit = 5

        try:
            f = urllib2.urlopen("%s&method=artist.getSimilar&autocorrect=1&artist=%s&limit=%s"
                    % (self.APIURL, artist, limit))
        except urllib2.HTTPError:
            irc.error("Unknown artist %s or something lol" % artist)
            return
        
        xml = minidom.parse(f).getElementsByTagName("similarartists")[0]
        theArtist = xml.getAttribute("artist")
        name = []
        similarity = []
        for i in range(limit):
            try:
                name.append(xml.getElementsByTagName("artist")[i].getElementsByTagName("name")[0].firstChild.data)
                similarity.append(xml.getElementsByTagName("artist")[i].getElementsByTagName("match")[0].firstChild.data)
            except IndexError:
                break
        if showColours:
            output = ("Artists similar to \x0308%s\x03: " % theArtist)
            for i,item in enumerate(name):
                output += ("\x0312%s\x03 (\x0304%.1f%%\x03)" % (item, float(similarity[i])*100))
                if i != (len(name)-1):
                    output += ", "
        else:
            output = ("Artists similar to %s: " % theArtist)
            for i,item in enumerate(name):
                output += ("%s (%.1f%%)" % (item, float(similarity[i])*100))
                if i != (len(name)-1):
                    output += ", "
        irc.reply(output)

    similar = wrap(similar, ['text'])
    #}}}

    #{{{ top artists
    def topartists(self, irc, msg, args, period):
        """[-user <user>] [<period>]

        Show <user>'s or saved user's top artists from <period> (7d,1m,3m,6m,12m,o)"""
        channel = msg.args[0]
        showColours = self.registryValue("showColours",channel)
        numArtists = 10

        id = (self.db.getId(msg.nick) or msg.nick)

        specificUser = True
        if period:
            theList = period.split(' ')
            try:
                userIndex = theList.index('-user')
            except ValueError:
                specificUser = False

            if specificUser:
                try:
                    user = theList[userIndex+1]
                except IndexError:
                    return("Error: you have to put user after -user, dummy")
                id = (self.db.getId(user) or user)
                timePeriod = theList[:theList.index("-user")] + theList[theList.index("-user")+2:]
                period = ' '.join(timePeriod)

        #noId = True
        #timeperiod = ""

        # python needs switch statements
        # this whole code is also pretty gross, eh?
        # I'm terrible at python 8)
        if period == "7d":
            period = "7day"
            timeperiod = "seven days"
        elif period == "1m":
            period = "1month"
            timeperiod = "one month"
        elif period == "3m":
            period = "3month"
            timeperiod = "three months"
        elif period == "6m":
            period = "6month"
            timeperiod = "six months"
        elif period == "12m":
            period = "12month"
            timeperiod = "twelve months"
        elif period == "o":
            period = "overall"
            timeperiod = "overall"
        else:
            #id = period
            period = "overall"
            #noId = False
        #if noId:
            #id = (self.db.getId(userid) or userid or self.db.getId(msg.nick) or msg.nick)
        #else:
            ##id = (self.db.getId(id) or id)
            #id = (self.db.getId(id) or id or self.db.getId(msg.nick) or msg.nick)
            timeperiod = "overall"

        try:
            f = urllib2.urlopen("%s&method=user.getTopArtists&user=%s&period=%s&limit=%s" % (self.APIURL, id, period, numArtists))
        except urllib2.HTTPError:
            irc.error("Unknown ID %s or bad period %s" % (id, period))
            return
        xml = minidom.parse(f).getElementsByTagName("topartists")[0]
        artists = xml.getElementsByTagName("artist")

        topArtists = []
        playCount = []

        for i in range(numArtists):
            try:
                topArtists.append(artists[i].getElementsByTagName("name")[0].firstChild.data)
                playCount.append(artists[i].getElementsByTagName("playcount")[0].firstChild.data)
            except IndexError:
                break

        output = ''

        if showColours:
            if timeperiod != "overall":
                output += ("\x0308%s\x03's top artists from the last %s: " % (id, timeperiod))
            else:
                output += ("\x0308%s\x03's %s top artists: " % (id, timeperiod))
            for i,item in enumerate(topArtists):
                output += ("\x0312%s\x03 (\x0304%s\x03)" % (item, playCount[i]))
                if i != (len(topArtists)-1):
                    output += ", "
        else:
            if timeperiod != "overall":
                output += ("%s\'s top artists from the last %s: " % (id, timeperiod))
            else:
                output += ("%s\'s %s top artists: " % (id, timeperiod))
            for i,item in enumerate(topArtists):
                output += ("%s (%s)" % (item, playCount[i]))
                if i != (len(topArtists)-1):
                    output += ", "
        
        irc.reply(output)

    topartists = wrap(topartists, [optional('text')])

    #}}}

    #{{{ top albums
    def topalbums(self, irc, msg, args, period):
        """[-user <user>] [<period>]

        Show <user>'s or saved user's top albums from <period> (7d,1m,3m,6m,12m,o)"""
        channel = msg.args[0]
        showColours = self.registryValue("showColours",channel)
        numAlbums = 10

        id = (self.db.getId(msg.nick) or msg.nick)

        specificUser = True
        if period:
            theList = period.split(' ')
            try:
                userIndex = theList.index('-user')
            except ValueError:
                specificUser = False

            if specificUser:
                try:
                    user = theList[userIndex+1]
                except IndexError:
                    return("Error: you have to put user after -user, dummy")
                id = (self.db.getId(user) or user)
                timePeriod = theList[:theList.index("-user")] + theList[theList.index("-user")+2:]
                period = ' '.join(timePeriod)

        #noId = True
        #timeperiod = ""

        # python needs switch statements
        # this whole code is also pretty gross, eh?
        # I'm terrible at python 8)
        # I should probably put all this shit in a function instead of
        # copy/paste
        # but I am too lazy
        # oh well
        if period == "7d":
            period = "7day"
            timeperiod = "seven days"
        elif period == "1m":
            period = "1month"
            timeperiod = "one month"
        elif period == "3m":
            period = "3month"
            timeperiod = "three months"
        elif period == "6m":
            period = "6month"
            timeperiod = "six months"
        elif period == "12m":
            period = "12month"
            timeperiod = "twelve months"
        elif period == "o":
            period = "overall"
            timeperiod = "overall"
        else:
            #id = period
            period = "overall"
            #noId = False
        #if noId:
            #id = (self.db.getId(userid) or userid or self.db.getId(msg.nick) or msg.nick)
        #else:
            ##id = (self.db.getId(id) or id)
            #id = (self.db.getId(id) or id or self.db.getId(msg.nick) or msg.nick)
            timeperiod = "overall"

        try:
            f = urllib2.urlopen("%s&method=user.getTopAlbums&user=%s&period=%s&limit=%s" % (self.APIURL, id, period, numAlbums))
        except urllib2.HTTPError:
            irc.error("Unknown ID %s or bad period %s" % (id, period))
            return
        xml = minidom.parse(f).getElementsByTagName("topalbums")[0]
        albums = xml.getElementsByTagName("album")

        topAlbums = []
        playCount = []
        artists = []

        for i in range(numAlbums):
            try:
                topAlbums.append(albums[i].getElementsByTagName("name")[0].firstChild.data)
                playCount.append(albums[i].getElementsByTagName("playcount")[0].firstChild.data)
                artists.append(albums[i].getElementsByTagName("artist")[0].getElementsByTagName("name")[0].firstChild.data)
            except IndexError:
                break

        output = ''

        if showColours:
            if timeperiod != "overall":
                output += ("\x0308%s\x03's top albums from the last %s: " % (id, timeperiod))
            else:
                output += ("\x0308%s\x03's %s top albums: " % (id, timeperiod))
            for i,item in enumerate(topAlbums):
                output += ("\x0312%s\x03 - \x0303%s\x03 (\x0304%s\x03)" % (artists[i], item, playCount[i]))
                if i != (len(topAlbums)-1):
                    output += ", "
        else:
            if timeperiod != "overall":
                output += ("%s\'s top albums from the last %s: " % (id, timeperiod))
            else:
                output += ("%s\'s %s top albums: " % (id, timeperiod))
            for i,item in enumerate(topAlbums):
                output += ("%s - %s (%s)" % (artists[i], item, playCount[i]))
                if i != (len(topAlbums)-1):
                    output += ", "
        
        irc.reply(output)

    topalbums = wrap(topalbums, [optional('text')])

    #}}}

    #{{{ top tracks
    def toptracks(self, irc, msg, args, period):
        """[-user <user>] [<period>]

        Show <user>'s or saved user's top tracks from <period> (7d,1m,3m,6m,12m,o)"""
        channel = msg.args[0]
        showColours = self.registryValue("showColours",channel)
        numTracks = 10

        id = (self.db.getId(msg.nick) or msg.nick)

        specificUser = True
        if period:
            theList = period.split(' ')
            try:
                userIndex = theList.index('-user')
            except ValueError:
                specificUser = False

            if specificUser:
                try:
                    user = theList[userIndex+1]
                except IndexError:
                    return("Error: you have to put user after -user, dummy")
                id = (self.db.getId(user) or user)
                timePeriod = theList[:theList.index("-user")] + theList[theList.index("-user")+2:]
                period = ' '.join(timePeriod)

        #noId = True
        #timeperiod = ""

        # python needs switch statements
        # this whole code is also pretty gross, eh?
        # I'm terrible at python 8)
        # I should probably put all this shit in a function instead of
        # copy/paste
        # but I am too lazy
        # oh well
        if period == "7d":
            period = "7day"
            timeperiod = "seven days"
        elif period == "1m":
            period = "1month"
            timeperiod = "one month"
        elif period == "3m":
            period = "3month"
            timeperiod = "three months"
        elif period == "6m":
            period = "6month"
            timeperiod = "six months"
        elif period == "12m":
            period = "12month"
            timeperiod = "twelve months"
        elif period == "o":
            period = "overall"
            timeperiod = "overall"
        else:
            #id = period
            period = "overall"
            #noId = False
        #if noId:
            #id = (self.db.getId(userid) or userid or self.db.getId(msg.nick) or msg.nick)
        #else:
            ##id = (self.db.getId(id) or id)
            #id = (self.db.getId(id) or id or self.db.getId(msg.nick) or msg.nick)
            timeperiod = "overall"

        try:
            f = urllib2.urlopen("%s&method=user.getTopTracks&user=%s&period=%s&limit=%s" % (self.APIURL, id, period, numTracks))
        except urllib2.HTTPError:
            irc.error("Unknown ID %s or bad period %s" % (id, period))
            return
        xml = minidom.parse(f).getElementsByTagName("toptracks")[0]
        tracks = xml.getElementsByTagName("track")

        topTracks = []
        playCount = []
        artists = []

        for i in range(numTracks):
            try:
                topTracks.append(tracks[i].getElementsByTagName("name")[0].firstChild.data)
                playCount.append(tracks[i].getElementsByTagName("playcount")[0].firstChild.data)
                artists.append(tracks[i].getElementsByTagName("artist")[0].getElementsByTagName("name")[0].firstChild.data)
            except IndexError:
                break

        output = ''

        if showColours:
            if timeperiod != "overall":
                output += ("\x0308%s\x03's top tracks from the last %s: " % (id, timeperiod))
            else:
                output += ("\x0308%s\x03's %s top tracks: " % (id, timeperiod))
            for i,item in enumerate(topTracks):
                output += ("\x0312%s\x03 - \x0303%s\x03 (\x0304%s\x03)" % (artists[i], item, playCount[i]))
                if i != (len(topTracks)-1):
                    output += ", "
        else:
            if timeperiod != "overall":
                output += ("%s\'s top tracks from the last %s: " % (id, timeperiod))
            else:
                output += ("%s\'s %s top tracks: " % (id, timeperiod))
            for i,item in enumerate(topTracks):
                output += ("%s - %s (%s)" % (artists[i], item, playCount[i]))
                if i != (len(topTracks)-1):
                    output += ", "
        
        irc.reply(output)

    toptracks = wrap(toptracks, [optional('text')])

    #}}}

    #{{{ first/last played
    def played(self, msg, first, query):
        channel = msg.args[0]
        showColours = self.registryValue("showColours", channel)

        id = (self.db.getId(msg.nick) or msg.nick)

        specificUser = True
        theList = query.split(' ')
        try:
            userIndex = theList.index('-user')
        except ValueError:
            specificUser = False

        if specificUser:
            try:
                user = theList[userIndex+1]
            except IndexError:
                return("Error: you have to put user after -user, dummy")
            id = (self.db.getId(user) or user)
            band = theList[:theList.index("-user")] + theList[theList.index("-user")+2:]
            query = ' '.join(band)

        artist = urllib.quote_plus(query)
        
        try:
            f = urllib2.urlopen("%s&method=user.getArtistTracks&artist=%s&user=%s" % (self.APIURL, artist, id))
        except urllib2.HTTPError,e:
            return ("Unknown user %s or artist %s, or maybe %s!" % (id,artist,e))
        xml = minidom.parse(f).getElementsByTagName("artisttracks")[0]
        user = xml.getAttribute("user")
        theArtist = xml.getAttribute("artist")
        if first:
            pages = xml.getAttribute("totalPages")
            try:
                j = urllib2.urlopen("%s&method=user.getArtistTracks&artist=%s&user=%s&page=%s" % (self.APIURL, artist, id, pages))
            except urllib2.HTTPError,e:
                return ("%s broke shit, m8." % e)
            lastpage = minidom.parse(j).getElementsByTagName("artisttracks")[0]
            try:
                firstPlay = lastpage.getElementsByTagName("track")[-1]
            except IndexError:
                return ("%s hasn't listened to %s lol" % (id,theArtist))
            theDate = firstPlay.getElementsByTagName("date")[0].firstChild.data
            track = firstPlay.getElementsByTagName("name")[0].firstChild.data
            try:
                album = firstPlay.getElementsByTagName("album")[0].firstChild.data
            except (IndexError,AttributeError):
                album = ""
        else:
            try:
                lastPlay = xml.getElementsByTagName("track")[0]
            except IndexError:
                return ("%s hasn't listened to %s lol" % (id,theArtist))
            theDate = lastPlay.getElementsByTagName("date")[0].firstChild.data
            track = lastPlay.getElementsByTagName("name")[0].firstChild.data
            try:
                album = lastPlay.getElementsByTagName("album")[0].firstChild.data
            except (IndexError,AttributeError):
                album = ""

        if showColours:
            output = "\x0308%s\x03" % id
            if first:
                output += " first "
            else:
                output += " last "
            output += "listened to \x0312%s\x03 on \x02%s\x02 with the track \"\x0310%s\x03\"" % ( theArtist, theDate, track)
            if album != "":
                output += " from [\x0313%s\x03]" % album
        else:
            output = "%s" % id
            if first:
                output += " first "
            else:
                output += " last "
            output += "listened to %s on %s with the track \"%s\"" % (theArtist, theDate, track)
            if album != "":
                output += " from [%s]" % album

        #irc.reply(output)
        return output

    def firstplayed(self, irc, msg, args, query):
        """<artist>

        Shows when user first played <artist>"""
        irc.reply(self.played(msg,True,query))
    firstplayed = wrap(firstplayed, ["text"])
    def lastplayed(self, irc, msg, args, query):
        """<artist>

        Shows when user last played <artist>"""
        irc.reply(self.played(msg,False,query))
    lastplayed = wrap(lastplayed, ["text"])
    #}}}

    # {{{ others
    def _parse(self, data, node, exceptMsg="not specified"):
            try:
                return data.getElementsByTagName(node)[0].firstChild.data
            except IndexError:
                return exceptMsg

    def _formatTimeago(self, unixtime):
        t = int(time()-unixtime)
        if t/86400 > 0:
            return "%i days ago" % (t/86400)
        if t/3600 == 1:
            return "%i hour ago" % (t/3600)
        if t/3600 > 0:
            return "%i hours ago" % (t/3600)
        if t/60 > 0:
            return "%i minutes ago" % (t/60)
        if t > 0:
            return "%i seconds ago" % (t)
    # }}}

dbfilename = conf.supybot.directories.data.dirize("LastFM.db")

Class = LastFM


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
