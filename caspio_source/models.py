from django.db import models

from localtv.models import *

CASPIO_SOURCE_STATUS_UNAPPROVED = VIDEO_STATUS_UNAPPROVED
CASPIO_SOURCE_STATUS_ACTIVE = VIDEO_STATUS_ACTIVE
CASPIO_SOURCE_STATUS_REJECTED = VIDEO_STATUS_REJECTED
CASPIO_SOURCE_STATUS_PENDING_THUMBNAIL = VIDEO_STATUS_PENDING_THUMBNAIL

CASPIO_SOURCE_STATUSES=VIDEO_STATUSES
 
class CaspioSource(Source):
    """
    Feed to pull videos in from.

    If the same feed is used on two different , they will require two
    separate entries here.

    Fields: 
      - table_name : name of the table to select from
      - id_field_name : name of the required field
      - url_field_name : url where video situated
      - video_title_field_name: human readable name of the video 
      - site: which site this feed belongs to
      - name: human readable name for this source
      - webpage: webpage that this feed\'s content is associated with
      - description: human readable description of this item
      - last_updated: last time we ran self.update_items()
      - when_submitted: when this feed was first registered on this site
      - status: one of FEED_STATUSES, either unapproved, active, or rejected
      - etag: used to see whether or not the feed has changed since our last
        update.
      - auto_approve: whether or not to set all videos in this feed to approved
        during the import process
      - user: a user that submitted this source, if any
      - auto_categories: categories that are automatically applied to videos on
        import
      - auto_authors: authors that are automatically applied to videos on
        import
    """

    name = models.CharField(max_length=250)
    webpage = models.URLField(verify_exists=False, blank=True)
    description = models.TextField()
    last_updated = models.DateTimeField(blank=True, null=True)
    when_submitted = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(choices=CASPIO_SOURCE_STATUSES, default=CASPIO_SOURCE_STATUS_UNAPPROVED)
    etag = models.CharField(max_length=250, blank=True)
    avoid_frontpage = models.BooleanField(default=False)
    calculated_source_type = models.CharField(max_length=255, blank=True, default='')
    table_name= models.CharField(max_length=250)

    class Meta:
        unique_together = (
            ('table_name', 'site'))
        get_latest_by = 'last_updated'

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('localtv_list_feed', [self.pk])
    '''id = models.AutoField(primary_key=True)'''

    def update_items(self, verbose=False, parsed_feed=None,
                     clear_rejected=False):
        """
        Fetch and import new videos from this feed.

        If clear_rejected is True, rejected videos that are part of this
        feed will be deleted and re-imported.
        """
        for i in self._update_items_generator(verbose, parsed_feed,
                                              clear_rejected):
            pass

    def _get_feed_urls(self):
        '''You might think that self.feed_url is the feed we will fetch
        during self.update_items(). That would be true, but...

        YouTube provides two different URLs for video feed. They are supposed
        to be equivalent, but sometimes videos show up in one but do not show
        up in the other. So when doing update_items() on a YouTube feed, we
        ask the backend to crawl both feed URLs.

        It's pretty terrible, but that's life.'''
        # Here is the YouTube-specific hack...
        if (self.feed_url.startswith('http://gdata.youtube.com/') and
            'v=2' in self.feed_url and
            'orderby=published' in self.feed_url):
            return [self.feed_url, self.feed_url.replace('orderby=published', '')]
        return [self.feed_url]

    def _update_items_generator(self, verbose=False, parsed_feed=None,
                                clear_rejected=False, actually_save_thumbnails=True):
        """
        Fetch and import new videos from this field.  After each imported
        video, we yield a dictionary:
        {'index': the index of the video we've just imported,
         'total': the total number of videos in the feed,
         'video': the Video object we just imported
        }
        """
        if parsed_feed is None:
            for feed_url in self._get_feed_urls():
                individual_parsed_feeds = []
                data = util.http_get(feed_url)
                individual_parsed_feeds.append(feedparser.parse(data))
            parsed_feed = vidscraper.bulk_import.util.join_feeds(
                individual_parsed_feeds)

        for index, entry in enumerate(parsed_feed['entries'][::-1]):
            yield self._handle_one_bulk_import_feed_entry(index, parsed_feed, entry, verbose=verbose, clear_rejected=clear_rejected, actually_save_thumbnails=actually_save_thumbnails)

        self._mark_bulk_import_as_done(parsed_feed)

    def default_video_status(self):
        # Check that if we want to add an active
        if self.auto_approve and localtv.tiers.Tier.get().can_add_more_videos():
            initial_video_status = VIDEO_STATUS_ACTIVE
        else:
            initial_video_status = VIDEO_STATUS_UNAPPROVED
        return initial_video_status

    def _handle_one_bulk_import_feed_entry(self, index, parsed_feed, entry, verbose, clear_rejected,
                                           actually_save_thumbnails=True):
        def skip(reason):
            if verbose:
                print "Skipping %s: %s" % (entry['title'], reason)
            return {'index': index,
                   'total': len(parsed_feed.entries),
                   'video': None,
                   'skip': reason}

        initial_video_status = self.default_video_status()

        guid = entry.get('guid', '')
        link = entry.get('link', '')
        if guid and Video.objects.filter(
            feed=self, guid=guid).exists():
            return skip('duplicate guid')

        if 'links' in entry:
            for possible_link in entry.links:
                if possible_link.get('rel') == 'via':
                    # original URL
                    link = possible_link['href']
                    break

        if link:
            if clear_rejected:
                for video in Video.objects.filter(
                    status=VIDEO_STATUS_REJECTED,
                    website_url=link):
                    video.delete()
            if Video.objects.filter(
                website_url=link).exists():
                return skip('duplicate link')

        video_data = {
            'name': unescape(entry['title']),
            'guid': guid,
            'site': self.site,
            'description': '',
            'file_url': '',
            'file_url_length': None,
            'file_url_mimetype': '',
            'embed_code': '',
            'flash_enclosure_url': '',
            'when_submitted': datetime.datetime.now(),
            'when_approved': (
                self.auto_approve and datetime.datetime.now() or None),
            'status': initial_video_status,
            'when_published': None,
            'feed': self,
            'website_url': link}

        tags = []
        authors = self.auto_authors.all()

        if entry.get('updated_parsed', None):
            video_data['when_published'] = datetime.datetime(
                *entry.updated_parsed[:6])

        thumbnail_url = util.get_thumbnail_url(entry) or ''
        if thumbnail_url and not urlparse.urlparse(thumbnail_url)[0]:
            thumbnail_url = urlparse.urljoin(parsed_feed.feed.link,
                                             thumbnail_url)
        video_data['thumbnail_url'] = thumbnail_url

        video_enclosure = util.get_first_video_enclosure(entry)
        if video_enclosure:
            file_url = video_enclosure.get('url')
            if file_url:
                file_url = unescape(file_url)
                if not urlparse.urlparse(file_url)[0]:
                    file_url = urlparse.urljoin(parsed_feed.feed.link,
                                                file_url)
                video_data['file_url'] = file_url

                try:
                    file_url_length = int(
                        video_enclosure.get('filesize') or
                        video_enclosure.get('length'))
                except (ValueError, TypeError):
                    file_url_length = None
                video_data['file_url_length'] = file_url_length

                video_data['file_url_mimetype'] = video_enclosure.get(
                    'type', '')

        try:
            scraped_data = vidscraper.auto_scrape(
                link,
                fields=['file_url', 'embed', 'flash_enclosure_url',
                        'publish_date', 'thumbnail_url', 'link',
                        'file_url_is_flaky', 'user', 'user_url',
                        'tags', 'description'])
            if scraped_data.get('link'):
                if (Video.objects.filter(
                        website_url=scraped_data['link']).count()):
                    return skip('duplicate link (vidscraper)')
                else:
                    video_data['website_url'] = scraped_data['link']


            if not video_data['file_url']:
                if not scraped_data.get('file_url_is_flaky'):
                    video_data['file_url'] = scraped_data.get(
                        'file_url') or ''
            video_data['embed_code'] = scraped_data.get('embed')
            video_data['flash_enclosure_url'] = scraped_data.get(
                'flash_enclosure_url', '')
            video_data['when_published'] = scraped_data.get(
                'publish_date')
            video_data['description'] = scraped_data.get(
                'description', '')
            if scraped_data['thumbnail_url']:
                video_data['thumbnail_url'] = scraped_data.get(
                    'thumbnail_url')

            tags = scraped_data.get('tags', [])

            if not authors.count() and scraped_data.get('user'):
                name = scraped_data.get('user')
                if ' ' in name:
                    first, last = name.split(' ', 1)
                else:
                    first, last = name, ''
                author, created = User.objects.get_or_create(
                    username=name[:30],
                    defaults={'first_name': first[:30],
                              'last_name': last[:30]})
                if created:
                    author.set_unusable_password()
                    author.save()
                    util.get_profile_model().objects.create(
                        user=author,
                        website=scraped_data.get('user_url'))
                authors = [author]

        except vidscraper.errors.Error, e:
            if verbose:
                print "Vidscraper error: %s" % e

        if not (video_data['file_url'] or video_data['embed_code']):
            return skip('invalid')

        if not video_data['description']:
            description = entry.get('summary', '')
            for content in entry.get('content', []):
                content_type = content.get('type', '')
                if 'html' in content_type:
                    description = content.value
                    break
            video_data['description'] = description

        if video_data['description']:
            soup = BeautifulSoup(video_data['description'])
            for tag in soup.findAll(
                'div', {'class': "miro-community-description"}):
                video_data['description'] = tag.renderContents()
                break
            video_data['description'] = sanitize(video_data['description'],
                                                 extra_filters=['img'])

        if entry.get('media_player'):
            player = entry['media_player']
            if isinstance(player, basestring):
                video_data['embed_code'] = unescape(player)
            elif player.get('content'):
                video_data['embed_code'] = unescape(player['content'])
            elif 'url' in player and not video_data['embed_code']:
                video_data['embed_code'] = '<embed src="%(url)s">' % player

        video = Video.objects.create(**video_data)
        if verbose:
                print 'Made video %i: %s' % (video.pk, video.name)

        if actually_save_thumbnails:
            try:
                video.save_thumbnail()
            except CannotOpenImageUrl:
                if verbose:
                    print "Can't get the thumbnail for %s at %s" % (
                        video.id, video.thumbnail_url)

        if tags or entry.get('tags'):
            if not tags:
                # Sometimes, entry.tags is just a lousy old
                # string. In that case, do our best to undo the
                # delimiting. For now, all I have seen is
                # space-separated values, so that's what I'm going
                # to go with.
                if type(entry.tags) in types.StringTypes:
                    tags = set(tag.strip() for tag in entry.tags.split())

                else:
                    # Usually, entry.tags is a list of dicts. If so, flatten them out into
                    tags = set(
                        tag['term'] for tag in entry['tags']
                        if tag.get('term'))

            if tags:
                video.tags = util.get_or_create_tags(tags)

        video.categories = self.auto_categories.all()
        video.authors = authors
        video.save()

        return {'index': index,
               'total': len(parsed_feed.entries),
               'video': video}

    def _mark_bulk_import_as_done(self, parsed_feed):
        self.etag = parsed_feed.get('etag') or ''
        self.last_updated = datetime.datetime.now()
        self.save()

    def source_type(self):
        return self.calculated_source_type

    def _calculate_source_type(self):
        return _feed__calculate_source_type(self)

    def video_service(self):
        return feed__video_service(self)

def feed__video_service(feed):
    # This implements the video_service method. It's outside the Feed class
    # so we can use it safely from South.
    for service, regexp in VIDEO_SERVICE_REGEXES:
        if re.search(regexp, feed.feed_url, re.I):
            return service

def _feed__calculate_source_type(feed):
    # This implements the _calculate_source_type method. It's outside the Feed
    # class so we can use it safely from South.
    video_service = feed__video_service(feed)
    if video_service is None:
        return u'Feed'
    else:
        return u'User: %s' % video_service

def pre_save_set_calculated_source_type(instance, **kwargs):
    # Always save the calculated_source_type
    instance.calculated_source_type = _feed__calculate_source_type(instance)
    # Plus, if the name changed, we have to recalculate all the Videos that depend on us.
    try:
        v = Feed.objects.get(id=instance.id)
    except Feed.DoesNotExist:
        return instance
    if v.name != instance.name:
        # recalculate all the sad little videos' calculated_source_type
        for vid in instance.video_set.all():
            vid.save()
    return instance
models.signals.pre_save.connect(pre_save_set_calculated_source_type,
                                sender=Feed)
