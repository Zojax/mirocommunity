### -*- coding: utf-8 -*- ####################################################

#from django import HttpResponse
#from SOAPpy import SAOPServer

from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import RssFeed

#def server(request):
 #   def echo(s):
  #      return s+s
    
    #server=SOAPServer(("localhost",8080))



class CaspioFeed(Feed):

    feed_type = RssFeed

    title = "Caspio.com rss feed"
    link = "/caspio/"
    description = "Latest videos from Caspio.com"

    description_template = ""

    def items(self):
        return []

    def item_title(self, item):
        return "item title"

    def item_description(self, item):
        return "item description"