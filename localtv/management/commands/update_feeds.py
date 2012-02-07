# This file is part of Miro Community.
# Copyright (C) 2010 Participatory Culture Foundation
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

import traceback
import datetime
import eventlet
from eventlet.green import urllib2
import feedparser

from django.core.management.base import NoArgsCommand
from localtv.management import site_too_old
from localtv import models

def feed_update_items(feed, etag, data):
    try:
        feed.update_items(parsed_feed=feedparser.parse(data))
    except:
        traceback.print_exc()
    else:
        if etag:
            feed.etag = etag
            feed.save()

def fetch_feed(feed):
    req = urllib2.Request(feed.feed_url)
    if feed.etag:
        req.add_header('If-None-Match', feed.etag)
    try:
        handle = urllib2.urlopen(req)
    except (urllib2.HTTPError, urllib2.URLError):
        return (None, None, None)
    return feed, handle.info().getheader('ETag'), handle.read()
    
class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, **options):
        if site_too_old():
            return

        # all feeds submitted more than an hour ago should be shown
        hour = datetime.timedelta(hours=1)
        models.Feed.objects.filter(
            when_submitted__lte=datetime.datetime.now()-hour,
            status=models.FEED_STATUS_UNAPPROVED).update(
            status=models.FEED_STATUS_ACTIVE)

        green_pile = eventlet.GreenPile()
        for feed in models.Feed.objects.filter(
            status=models.FEED_STATUS_ACTIVE):
            for url in feed._get_feed_urls():
                green_pile.spawn(fetch_feed, feed)
        for feed, etag, data in green_pile:
            if feed:
                feed_update_items(feed, etag, data)



