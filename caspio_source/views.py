### -*- coding: utf-8 -*- ####################################################

#from django import HttpResponse
#from SOAPpy import SAOPServer

from django.contrib.syndication.views import Feed
#from django.utils.feedgenerator import RssFeed

from caspio_source.models import fetch_caspio_data, CaspioData


class CaspioFeed(Feed):

#    feed_type = RssFeed
#    def __init__(self, slug, request):
#        super(CaspioFeed, self).__init__(slug, request)


    title = u"Caspio.com rss feed"
    link = "http://caspio.com/"
    description = u"Latest videos from Caspio.com"
    table_name = None


    def get_object(self, request, table_name):
        try:
            cd = CaspioData.objects.get(table_name=table_name)
        except:
            cd = None
        feed_data = fetch_caspio_data(table_name, last_id=cd.last_id if cd else 0)
        self.table_name = table_name

        return feed_data

    def title(self, obj):
        return u"Caspio.com rss feed for table '%s' " % self.table_name

    def description(self, obj):
        return u"Latest videos from Caspio.com rss feed for table '%s'" % self.table_name

    def items(self, obj):
        return obj

    def item_title(self, item):

        return item['title']

    def item_description(self, item):

        return item['description']

    def item_link(self, item):
        """
        Takes an item, as returned by items(), and returns the item's URL.
        """
        return item['link']

    def item_guid(self, item):
        """
        Takes an item, as return by items(), and returns the item's ID.
        """
        return item['id']

    def item_author_name(self, item):
        """
        Returns the item's author's name as a normal Python string.
        """
        return item['author']


    def item_enclosure_url(self, item):
        """
        Returns the item's enclosure URL.
        """
        return item['enclosure_url']

    def item_enclosure_mime_type(self, item):
        """
        Returns the item's enclosure MIME type.
        """
        return item['enclosure_mime'] or ""

    def item_enclosure_length(self, item):
        """
        Returns the item's enclosure length.
        """
        return item['enclosure_length'] or 0