### -*- coding: utf-8 -*- ####################################################

import re
import urllib2

from django.db import models
from django.db.models.signals import post_save

from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from localtv.models import *
from suds.client import Client

CASPIO_SOURCE_STATUS_UNAPPROVED = VIDEO_STATUS_UNAPPROVED
CASPIO_SOURCE_STATUS_ACTIVE = VIDEO_STATUS_ACTIVE
CASPIO_SOURCE_STATUS_REJECTED = VIDEO_STATUS_REJECTED
CASPIO_SOURCE_STATUS_PENDING_THUMBNAIL = VIDEO_STATUS_PENDING_THUMBNAIL



CASPIO_SOURCE_STATUSES=VIDEO_STATUSES


CASPIO_ACCOUNT_ID = getattr(settings, "CASPIO_ACCOUNT_ID", None)
CASPIO_PROFILE_ID = getattr(settings, "CASPIO_PROFILE_ID", None)
CASPIO_PASSWORD = getattr(settings, "CASPIO_PASSWORD", None)

WSDL_URL="https://b3.caspio.com/ws/api.asmx?wsdl"

CASPIO_COMMON_FIELDS_MAP = (
    ("title", "BusinessName"),
    ("description", None),
    ("link", "PageURL"),
    ("id", "PK_ID"),
    ("author", "BusinessAuthor"),
    ("enclosure_url", "VideoURL"),
    ("enclosure_length", None),
    ("enclosure_mime", None),
    ("pubdate", "Updated"),
)

def get_wsdl(wsdl_url=WSDL_URL):
    return Client(wsdl_url)

def fetch_caspio_data(table_name, last_id, mapping=CASPIO_COMMON_FIELDS_MAP):

    """
    * table_name - name of Caspio table;
    * last_id - last fetched PK_ID;
    * mapping - fields mapping;

    """

    wsdl = get_wsdl()
    query_result = wsdl.service.SelectData(CASPIO_ACCOUNT_ID, CASPIO_PROFILE_ID, CASPIO_PASSWORD,
                            table_name, False,
                            "*",#(self.id_field_name, self.url_field_name, self.last_updated, self.video_title_name)
                            "PK_ID>%s" % last_id, "PK_ID")
    itms = []
    for i in query_result.Row:
        itm = {}
        for k,v in mapping:
            itm[k] = getattr(i, v)[0] if v else v

        # Need to fill content-type and length
        # But can take additional time
#        if itm["enclosure_length"] is None and itm["enclosure_mime"] is None\
#        and itm["enclosure_url"] is not None:
#            try:
#                item_info = urllib2.urlopen(itm["enclosure_url"])
#                itm["enclosure_mime"] = item_info.headers.get("Content-Type", None)
#                itm["enclosure_length"] = item_info.headers.get("Content-Length", None)
#            except:
#                pass

        itms.append(itm)

    return itms




CASPIO_FEED_RE = re.compile(r'.+feeds/caspio/(?P<table_name>\w+)')

class CaspioData(models.Model):
    """
    Model required for storing feed info like ID of last retrieved object in

    appropriate Caspio table.

    Fields:
        * table_name - Caspio table name;

        * last_id - ID of last fetched object;

        * last_updated - Date and time of last table retrieving;

    """

    table_name = models.CharField(verbose_name=_(u"Caspio table"), max_length=100, unique=True)

    last_id = models.IntegerField(verbose_name=_(u"Last object ID"), default=0)

    last_updated = models.DateTimeField(verbose_name=_(u"Last Updated"), auto_now=True, auto_now_add=True)

    feed = models.OneToOneField(Feed, related_name="caspio_data")

    class Meta:
        verbose_name = _(u"Caspio Data item")
        verbose_name_plural = _(u"Caspit Data items")

    def __unicode__(self):

        return _(u"Last object ID from '%s' table is %s" % (self.table_name, self.last_id))


def track_feed(sender=None, instance=None, created=False, *args, **kwargs):
    """
    Let's create CaspioData entry when feed with appropriate url added
    """
    if created:
        caspio_match = CASPIO_FEED_RE.search(instance.feed_url)
        if caspio_match:
            cd, created = CaspioData.objects.get_or_create(table_name = caspio_match.group("table_name"),
                                                            feed = instance)

post_save.connect(track_feed, sender=Feed)

def update_data(sender=None, instance=None, created=False, *args, **kwargs):
    """
    Updates CaspioData entry when new Video created
    """
    if created and instance.feed is not None:
        try:
            # Trying to get CaspioData instance.
            # If it doesn't exist - skip as current feed
            # doesn't fit our purposes
            cd = instance.feed.caspio_data
            cd.last_id = int(instance.guid)
            cd.save()

        except CaspioData.DoesNotExist:
            pass
        except (TypeError, ValueError):
            # Something went wrong
            # video guid should be integer
            pass

post_save.connect(update_data, sender=Video)

#SelectData(xs:string AccountID, xs:string Profile, xs:string Password, xs:string ObjectName,
#           xs:boolean IsView, xs:string FieldList, xs:string Criteria, xs:string OrderBy, )

 
#class CaspioSource(Source):
#    """
#    Feed to pull videos in from.
#
#    If the same feed is used on two different , they will require two
#    separate entries here.
#
#    Fields:
#      - table_name : name of the table to select from
#      - id_field_name : name of the required field
#      - url_field_name : url where video situated
#      - video_title_field: human readable name of the video
#      - site: which site this feed belongs to
#      - name: human readable name for this source
#      - webpage: webpage that this feed\'s content is associated with
#      - description: human readable description of this item
#      - last_updated: last time we ran self.update_items()
#      - when_submitted: when this feed was first registered on this site
#      - status: one of FEED_STATUSES, either unapproved, active, or rejected
#      - etag: used to see whether or not the feed has changed since our last
#        update.
#      - auto_approve: whether or not to set all videos in this feed to approved
#        during the import process
#      - user: a user that submitted this source, if any
#      - auto_categories: categories that are automatically applied to videos on
#        import
#      - auto_authors: authors that are automatically applied to videos on
#        import
#    """
#
#    name = models.CharField(max_length=250)
#    webpage = models.URLField(verify_exists=False, blank=True)
#    description = models.TextField()
#    last_updated = models.DateTimeField(blank=True, null=True)
#    when_submitted = models.DateTimeField(auto_now_add=True)
#    status = models.IntegerField(choices=CASPIO_SOURCE_STATUSES, default=CASPIO_SOURCE_STATUS_UNAPPROVED)
#    etag = models.CharField(max_length=250, blank=True)
#    avoid_frontpage = models.BooleanField(default=False)
#    calculated_source_type = models.CharField(max_length=255, blank=True, default='')
#    table_name= models.CharField(max_length=250)
#    id_field_name=models.IntegerField(blank=False,null=False)
#    url_field_name = models.URLField(verify_exists=False, blank=False)
#    video_title_field=models.CharField(max_length=250)
#
#    class Meta:
#        unique_together = (
#            ('table_name', 'site'))
#        get_latest_by = 'last_updated'
#
#    def __unicode__(self):
#        return self.name
#
#    @models.permalink
#    def get_absolute_url(self):
#        return ('localtv_list_feed', [self.pk])
#    '''id = models.AutoField(primary_key=True)'''
#
#    def update_items(self, verbose=False, parsed_feed=None,
#                     clear_rejected=False):
#        """
#        Fetch and import new videos from this feed.
#
#        If clear_rejected is True, rejected videos that are part of this
#        feed will be deleted and re-imported.
#        """
#        for i in self._update_items_generator(verbose, parsed_feed,
#                                              clear_rejected):
#            pass
#
#    def get_wsdl(self):
#        return WSDL.Proxy(WSDL_URL)
#
#
#    def _update_items_generator(self, verbose=False, clear_rejected=False, actually_save_thumbnails=True):
#        """
#        Fetch and import new videos from this field.  After each imported
#        video, we yield a dictionary:
#        {'index': the index of the video we've just imported,
#         'total': the total number of videos in the feed,
#         'video': the Video object we just imported
#        }
#        """
#
#
#        wsdl = self.get_wsdl()
#        for entry in wsdl.SelectData(ACCOUNT_ID,PROFILEID, PASSWORD, self.table_name ,False, (self.id_field_name, self.url_field_name, self.last_updated, self.video_title_name), 'id'):
#            yield self._handle_one_bulk_import_feed_entry(wsdl, entry, verbose=verbose, clear_rejected=clear_rejected, actually_save_thumbnails=actually_save_thumbnails)
#
#        self._mark_bulk_import_as_done(wsdl)
#
#    def default_video_status(self):
#        # Check that if we want to add an active
#        if self.auto_approve and localtv.tiers.Tier.get().can_add_more_videos():
#            initial_video_status = VIDEO_STATUS_ACTIVE
#        else:
#            initial_video_status = VIDEO_STATUS_UNAPPROVED
#        return initial_video_status
#
#    def _handle_one_bulk_import_feed_entry(self, wsdl, entry, verbose, clear_rejected,
#                                           actually_save_thumbnails=True):# seems that we can deal with it without wsdl
#        def skip(reason):
#            if verbose:
#                print "Skipping %s: %s" % (entry['title'], reason)
#            return {'total': len(wsdl.entries),
#                   'video': None,
#                   'skip': reason}
#
#        initial_video_status = self.default_video_status()
#
#        guid = entry.get('guid', '')
#        link = entry.get('link', '')
#        if guid and Video.objects.filter(
#            feed=self, guid=guid).exists():
#            return skip('duplicate guid')
#
#        if 'links' in entry:
#            for possible_link in entry.links:
#                if possible_link.get('rel') == 'via':
#                    # original URL
#                    link = possible_link['href']
#                    break
#
#        if link:
#            if clear_rejected:
#                for video in Video.objects.filter(
#                    status=VIDEO_STATUS_REJECTED,
#                    website_url=link):
#                    video.delete()
#            if Video.objects.filter(
#                website_url=link).exists():
#                return skip('duplicate link')
#
#        video_data = {
#            'name': self.video_title_name,
#            'guid': guid,
#            'site': self.site,
#            'description': '',
#            'file_url': '',
#            'file_url_length': None,
#            'file_url_mimetype': '',
#            'embed_code': '',
#            'flash_enclosure_url': '',
#            'when_submitted': datetime.datetime.now(),
#            'when_approved': (
#                self.auto_approve and datetime.datetime.now() or None),
#            'status': initial_video_status,
#            'when_published': None,
#            #'feed': self,
#            'website_url': link}
#
#        tags = []
#        authors = self.auto_authors.all()
#
#        if entry.get('updated_parsed', None):
#            video_data['when_published'] = datetime.datetime(
#                *entry.updated_parsed[:6])
#
#        thumbnail_url = util.get_thumbnail_url(entry) or ''
#        if thumbnail_url and not urlparse.urlparse(thumbnail_url)[0]:
#            thumbnail_url = urlparse.urljoin(parsed_feed.feed.link,
#                                             thumbnail_url)
#        video_data['thumbnail_url'] = thumbnail_url
#
#        video_enclosure = util.get_first_video_enclosure(entry)
#        if video_enclosure:
#            file_url = video_enclosure.get('url')
#            if file_url:
#                file_url = unescape(file_url)
#                if not urlparse.urlparse(file_url)[0]:
#                    file_url = urlparse.urljoin(parsed_feed.feed.link,
#                                                file_url)
#                video_data['file_url'] = file_url
#
#                try:
#                    file_url_length = int(
#                        video_enclosure.get('filesize') or
#                        video_enclosure.get('length'))
#                except (ValueError, TypeError):
#                    file_url_length = None
#                video_data['file_url_length'] = file_url_length
#
#                video_data['file_url_mimetype'] = video_enclosure.get(
#                    'type', '')
#
#        try:
#            scraped_data = vidscraper.auto_scrape(
#                link,
#                fields=['file_url', 'embed', 'flash_enclosure_url',
#                        'publish_date', 'thumbnail_url', 'link',
#                        'file_url_is_flaky', 'user', 'user_url',
#                        'tags', 'description'])
#            if scraped_data.get('link'):
#                if (Video.objects.filter(
#                        website_url=scraped_data['link']).count()):
#                    return skip('duplicate link (vidscraper)')
#                else:
#                    video_data['website_url'] = scraped_data['link']
#
#
#            if not video_data['file_url']:
#                if not scraped_data.get('file_url_is_flaky'):
#                    video_data['file_url'] = scraped_data.get(
#                        'file_url') or ''
#            video_data['embed_code'] = scraped_data.get('embed')
#            video_data['flash_enclosure_url'] = scraped_data.get(
#                'flash_enclosure_url', '')
#            video_data['when_published'] = scraped_data.get(
#                'publish_date')
#            video_data['description'] = scraped_data.get(
#                'description', '')
#            if scraped_data['thumbnail_url']:
#                video_data['thumbnail_url'] = scraped_data.get(
#                    'thumbnail_url')
#
#            tags = scraped_data.get('tags', [])
#
#            if not authors.count() and scraped_data.get('user'):
#                name = scraped_data.get('user')
#                if ' ' in name:
#                    first, last = name.split(' ', 1)
#                else:
#                    first, last = name, ''
#                author, created = User.objects.get_or_create(
#                    username=name[:30],
#                    defaults={'first_name': first[:30],
#                              'last_name': last[:30]})
#                if created:
#                    author.set_unusable_password()
#                    author.save()
#                    util.get_profile_model().objects.create(
#                        user=author,
#                        website=scraped_data.get('user_url'))
#                authors = [author]
#
#        except vidscraper.errors.Error, e:
#            if verbose:
#                print "Vidscraper error: %s" % e
#
#        if not (video_data['file_url'] or video_data['embed_code']):
#            return skip('invalid')
#
#        if not video_data['description']:
#            description = entry.get('summary', '')
#            for content in entry.get('content', []):
#                content_type = content.get('type', '')
#                if 'html' in content_type:
#                    description = content.value
#                    break
#            video_data['description'] = description
#
#        if video_data['description']:
#            soup = BeautifulSoup(video_data['description'])
#            for tag in soup.findAll(
#                'div', {'class': "miro-community-description"}):
#                video_data['description'] = tag.renderContents()
#                break
#            video_data['description'] = sanitize(video_data['description'],
#                                                 extra_filters=['img'])
#
#        if entry.get('media_player'):
#            player = entry['media_player']
#            if isinstance(player, basestring):
#                video_data['embed_code'] = unescape(player)
#            elif player.get('content'):
#                video_data['embed_code'] = unescape(player['content'])
#            elif 'url' in player and not video_data['embed_code']:
#                video_data['embed_code'] = '<embed src="%(url)s">' % player
#
#        video = Video.objects.create(**video_data)
#        if verbose:
#                print 'Made video %i: %s' % (video.pk, video.name)
#
#        if actually_save_thumbnails:
#            try:
#                video.save_thumbnail()
#            except CannotOpenImageUrl:
#                if verbose:
#                    print "Can't get the thumbnail for %s at %s" % (
#                        video.id, video.thumbnail_url)
#
#        if tags or entry.get('tags'):
#            if not tags:
#                # Sometimes, entry.tags is just a lousy old
#                # string. In that case, do our best to undo the
#                # delimiting. For now, all I have seen is
#                # space-separated values, so that's what I'm going
#                # to go with.
#                if type(entry.tags) in types.StringTypes:
#                    tags = set(tag.strip() for tag in entry.tags.split())
#
#                else:
#                    # Usually, entry.tags is a list of dicts. If so, flatten them out into
#                    tags = set(
#                        tag['term'] for tag in entry['tags']
#                        if tag.get('term'))
#
#            if tags:
#                video.tags = util.get_or_create_tags(tags)
#
#        video.categories = self.auto_categories.all()
#        video.authors = authors
#        video.save()
#
#        return {'index': index,
#               'total': len(parsed_feed.entries),
#               'video': video}
#
#    def _mark_bulk_import_as_done(self, parsed_feed):
#        self.etag = parsed_feed.get('etag') or ''
#        self.last_updated = datetime.datetime.now()
#        self.save()
#
#    def source_type(self):
#        return self.calculated_source_type
#
#    def _calculate_source_type(self):
#        return _feed__calculate_source_type(self)
#
#    def video_service(self):
#        return feed__video_service(self)
#
#def feed__video_service(feed):
#    # This implements the video_service method. It's outside the Feed class
#    # so we can use it safely from South.
#    for service, regexp in VIDEO_SERVICE_REGEXES:
#        if re.search(regexp, feed.feed_url, re.I):
#            return service
#
#def _feed__calculate_source_type(feed):
#    # This implements the _calculate_source_type method. It's outside the Feed
#    # class so we can use it safely from South.
#    video_service = feed__video_service(feed)
#    if video_service is None:
#        return u'Feed'
#    else:
#        return u'User: %s' % video_service
#
#def pre_save_set_calculated_source_type(instance, **kwargs):
#    # Always save the calculated_source_type
#    instance.calculated_source_type = _feed__calculate_source_type(instance)
#    # Plus, if the name changed, we have to recalculate all the Videos that depend on us.
#    try:
#        v = Feed.objects.get(id=instance.id)
#    except Feed.DoesNotExist:
#        return instance
#    if v.name != instance.name:
#        # recalculate all the sad little videos' calculated_source_type
#        for vid in instance.video_set.all():
#            vid.save()
#    return instance
#models.signals.pre_save.connect(pre_save_set_calculated_source_type,
#                                sender=Feed)
