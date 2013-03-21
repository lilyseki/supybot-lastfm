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

import urllib2
#from urllib import quote_plus
from xml.dom import minidom
import urllib
from time import time

from LastFMDB import *
### }}}

class LastFM(callbacks.Plugin):
    # {{{ vars
    BASEURL = "http://ws.audioscrobbler.com/1.0/user"
    APIKEY = "" # FIXME: Get own key
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

        id = (optionalId or self.db.getId(msg.nick) or msg.nick)
        channel = msg.args[0]
        showColours = self.registryValue("showColours", channel)
        trackInfo = self.registryValue("showTrackInfo", channel)
        showTags = self.registryValue("showTags", channel)

        try:
            f = urllib2.urlopen("%s&method=user.getrecenttracks&user=%s"
                    % (self.APIURL, id))
        except urllib2.HTTPError:
            irc.error("Unknown ID (%s)" % id)
            return

        xml = minidom.parse(f).getElementsByTagName("recenttracks")[0]
        user = xml.getAttribute("user")
        try:
            t = xml.getElementsByTagName("track")[0] # most recent track
        except:
            irc.error("No tracks or something for %s lol" % id)
            return
        isNowplaying = (t.getAttribute("nowplaying") == "true")
        artist = t.getElementsByTagName("artist")[0].firstChild.data
        track = t.getElementsByTagName("name")[0].firstChild.data
        try:
            album = urllib.quote_plus(" ["+t.getElementsByTagName("album")[0].getElementsByTagName("title")[0].firstChild.data+"]")
        except:
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
        except:
            trackInfo = False

        try:
            userplaycount = playinfo.getElementsByTagName("userplaycount")[0].firstChild.data
        except:
            userplaycount = 0

        # tags
        tags = []
        thetags = urllib2.urlopen("%s&method=artist.getTopTags&artist=%s" % (self.APIURL,artist2))
        toptags = minidom.parse(thetags).getElementsByTagName("toptags")[0]
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
                    output += " ( "
                    for item in tags:
                        output += ("\x0307%s\x03 " % item).encode("utf8")
                    output += ")"
                    #output += (' (\x0307%s\x03, \x0307%s\x03, \x0307%s\x03)' % (tag1, tag2, tag3)).encode("utf8")
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
                    output += " ( "
                    for item in tags:
                        output += ("%s " % item).encode("utf8")
                    output += ")"
                    #output += (' (%s, %s, %s)' % (tag1, tag2, tag3)).encode("utf8")
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
            output += ('\x0308%s\x03 and \x0308%s\x03 have \x0304%.1f%%\x03 music compatibility!' % (id1, id2, score*100))
            if score != 0:
                output += (' Artists they share include: \x0312%s\x03' % ("\x03, \x0312".join(artist_names))).encode("utf8")
        else:
            output += ('%s and %s have %.1f%% music compatibility!' % (id1, id2, score*100))
            if score != 0:
                output += (' Artists they share include: %s' % (", ".join(artist_names))).encode("utf8")
        irc.reply(output)
    
    compare = wrap(compare, ["something", optional("something")])
    # }}}

    # {{{ search
    def search(self, irc, msg, args, query):
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
        except:
            userPlayed = False

        try:
            placeformed = bio.getElementsByTagName("placeformed")[0].firstChild.data
            formationlist = bio.getElementsByTagName("formationlist")[0].getElementsByTagName("formation")[0]
            yearfrom = bio.getElementsByTagName("yearformed")[0].firstChild.data
            try:
                yearto = formationlist.getElementsByTagName("yearto")[0].firstChild.data
            except:
                yearto = "Present"
        except:
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
                output += " ( "
                for item in tags:
                    output += ("\x0307%s\x03 " % item)
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
                output += " ( "
                for item in tags:
                    output += ("%s " % item)
                output += ")"
            if not userPlayed:
                userplaycount = 0
            output += (' %s plays by %s, %s plays by %s listeners.' % (userplaycount, id, playcount, listenercount)).encode("utf8")
            output += (" %s" % url)

        irc.reply(output)

    search = wrap(search, ['text'])
    # }}}

    # {{{ plays
    def plays(self, irc, msg, args, query):
        """<query>

        Displays user plays for artist <query>.
        """

        id = (self.db.getId(msg.nick) or msg.nick)
        channel = msg.args[0]
        showColours = self.registryValue("showColours", channel)
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
        except:
            irc.error("Can't find artist %s! :O" % artist)
            return

        try:
            userplaycount = xml.getElementsByTagName("userplaycount")[0].firstChild.data
        except:
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
            except ValueError:
                break
        if showColours:
            output = ("Artists similar to \x0308%s\x03: " % theArtist)
            for i in range(len(name)):
                output += ("\x0312%s\x03 (\x0304%.1f%%\x03)" % (name[i], float(similarity[i])*100))
                if i != (len(name)-1):
                    output += ", "
        else:
            output = ("Artists similar to %s: " % theArtist)
            for i in range(len(name)):
                output += ("%s (%.1f%%)" % (name[i], float(similarity[i])*100))
                if i != (len(name)-1):
                    output += ", "
        irc.reply(output)

    similar = wrap(similar, ['text'])
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
