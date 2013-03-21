supybot-lastfm
==============

A plugin for supybot that displays various information about a LastFM ID in IRC.

Usage
-----

Showing now playing, or most recently played information:
```
05:33:14 lembas-nyan │ ~np
05:33:17     samwise │ tacticalbread listened to "Untitled" by dälek about 2 hours ago. 1 plays by tacticalbread, 1043 plays by 492 listeners. (Hip-Hop, experimental, noise)
```

Showing profile information:
```
05:34:20 lembas-nyan │ ~profile
05:34:21     samwise │ tacticalbread (realname: Shad) registered on Oct 28, 2008; age: 23 / m; Country: United States; Tracks played: 68542
```

Showing recent tracks:
```
05:35:23 lembas-nyan │ ~lastfm recenttracks
05:35:24     samwise │ tacticalbread's recenttracks: dälek – Untitled, dälek – Atypical Stereotype, dälek – 2012 (The Pillage), dälek – Gutter Tactics, dälek – We Lost Sight (with a total number of 11 entries)
```

Searching artists:
```
05:36:58 lembas-nyan │ ~lastfm search M83
05:37:00     samwise │ M83 [ 2001 - Present, Antibes, France ] ( electronic, shoegaze, post-rock ) 2940 plays by tacticalbread, 50479098 plays by 1260956 listeners. http://www.last.fm/music/M83
```

Comparing two users:
```
05:38:09 lembas-nyan │ ~compare suzuki-nyan
05:38:10     samwise │ gurosebe and tacticalbread have 98.0% music compatibility! Artists they share include: Matryoshka, Cloudkicker, Nujabes, YUI, きゃりーぱみゅぱみゅ
```

Similar Artists:
```
05:18:06  lembas │ ~similar Spangle call Lilli line
05:18:07 samwise │ Artists similar to Spangle call Lilli line: NINI TOUNUMA (100.0%), audio safari (58.4%), クラムボン (56.6%), advantage Lucy (55.2%), 点と線 (54.5%)
```

Showing help:
```
05:35:48 lembas-nyan │ ~help lastfm
05:35:53     samwise │ (lastfm <method> [<id>]) -- Lists LastFM info where <method> is in [friends, neighbours, profile, recenttracks, tags, topalbums, topartists, toptracks]. Set your LastFM ID with the set method (default is your current nick) or specify <id> to switch for one call.
```

Showing commands:
```
05:40:44 lembas-nyan │ ~list lastfm
05:40:47     samwise │ compare, lastfm, np, profile, search, and set
```

Development
-----------

The files `__init__.py` and `plugin.py` provide some documentation.
