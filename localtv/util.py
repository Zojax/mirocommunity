# Copyright 2009 - Participatory Culture Foundation
#
# This file is part of Miro Community.
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

import hashlib
import re
import string
import urllib

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.db.models import get_model
from django.http import HttpResponse
from django.utils.encoding import force_unicode

import tagging
import vidscraper

VIDEO_EXTENSIONS = [
    '.mov', '.wmv', '.mp4', '.m4v', '.ogg', '.ogv', '.anx',
    '.mpg', '.avi', '.flv', '.mpeg', '.divx', '.xvid', '.rmvb',
    '.mkv', '.m2v', '.ogm']

def is_video_filename(filename):
    """
    Pass a filename to this method and it will return a boolean
    saying if the filename represents a video file.
    """
    filename = filename.lower()
    for ext in VIDEO_EXTENSIONS:
        if filename.endswith(ext):
            return True
    return False

def is_video_type(type):
    application_video_mime_types = [
        "application/ogg",
        "application/x-annodex",
        "application/x-bittorrent",
        "application/x-shockwave-flash"
    ]
    return (type.startswith('video/') or type.startswith('audio/') or
            type in application_video_mime_types)

def get_first_video_enclosure(entry):
    """Find the first video enclosure in a feedparser entry.  Returns the
    enclosure, or None if no video enclosure is found.
    """
    enclosures = entry.get('media_content') or entry.get('enclosures')
    if not enclosures:
        return None
    best_enclosure = None
    for enclosure in enclosures:
        if is_video_type(enclosure.get('type', '')) or \
                is_video_filename(enclosure.get('url', '')):
            if enclosure.get('isdefault'):
                return enclosure
            elif best_enclosure is None:
                best_enclosure = enclosure
    return best_enclosure

def get_thumbnail_url(entry):
    """Get the URL for a thumbnail from a feedparser entry."""
    # Try the video enclosure
    def _get(d):
        if 'media_thumbnail' in d:
            return d.media_thumbnail[0]['url']
        if 'blip_thumbnail_src' in d and d.blip_thumbnail_src:
            return (u'http://a.images.blip.tv/%s' % (
                d['blip_thumbnail_src'])).encode('utf-8')
        if 'itunes_image' in d:
            return d.itunes_image['href']
        if 'image' in d:
            return d.image['href']
        raise KeyError
    video_enclosure = get_first_video_enclosure(entry)
    if video_enclosure is not None:
        try:
            return _get(video_enclosure)
        except KeyError:
            pass
    # Try to get any enclosure thumbnail
    for key in 'media_content', 'enclosures':
        if key in entry:
            for enclosure in entry[key]:
                try:
                    return _get(enclosure)
                except KeyError:
                    pass
    # Try to get the thumbnail for our entry
    try:
        return _get(entry)
    except KeyError:
        pass

    if entry.get('link', '').find(u'youtube.com') != -1:
        if 'content' in entry:
            content = entry.content[0]['value']
        elif 'summary' in entry:
            content = entry.summary
        else:
            return None
        match = re.search(r'<img alt="" src="([^"]+)" />',
                          content)
        if match:
            return match.group(1)

    return None

def get_or_create_tags(tag_list):
    tag_set = set()
    for tag_text in tag_list:
        if isinstance(tag_text, basestring):
            tag_text = tag_text[:50] # tags can only by 50 chars
        if settings.FORCE_LOWERCASE_TAGS:
            tag_text = tag_text.lower()
        tags = tagging.models.Tag.objects.filter(name=tag_text)
        if not tags:
            tag = tagging.models.Tag.objects.create(name=tag_text)
        elif tags.count() == 1:
            tag = tags[0]
        else:
            for tag in tags:
                if tag.name == tag:
                    # MySQL doesn't do case-sensitive equals on strings
                    break
        tag.name = force_unicode(tag.name)
        tag_set.add(tag)
    return tagging.utils.edit_string_for_tags(list(tag_set))


def get_scraped_data(url):
    cache_key = 'vidscraper_data-' + url
    if len(cache_key) >= 250:
        # too long, use the hash
        cache_key = 'vidscraper_data-hash-' + hashlib.sha1(url).hexdigest()
    scraped_data = cache.get(cache_key)

    if not scraped_data:
        # try and scrape the url
        try:
            scraped_data = vidscraper.auto_scrape(url)
        except vidscraper.errors.Error:
            scraped_data = None

        cache.add(cache_key, scraped_data)

    return scraped_data


def send_mail_admins(sitelocation, subject, message, fail_silently=True):
    """
    Send an e-mail message to the admins for the given site.
    """
    admin_list = sitelocation.admins.filter(
        is_superuser=False).exclude(email=None).exclude(
        email='').values_list('email', flat=True)
    superuser_list = User.objects.filter(is_superuser=True).exclude(
        email=None).exclude(email='').values_list('email', flat=True)
    recipient_list = set(admin_list) | set(superuser_list)
    EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL,
                 bcc=recipient_list).send(fail_silently=fail_silently)

def sort_header(sort, label, current):
    """
    Generate some metadata for a sortable header.

    @param sort: the sort which this header represents
    @param label: the human-readable label
    @param the current sort

    Returns a dictionary with a link and a CSS class to use for this header,
    based on the scurrent sort.
    """
    if current.endswith(sort):
        # this is the current sort
        css_class = 'sortup'
        if current[0] != '-':
            sort = '-%s' % sort
            css_class = 'sortdown'
    else:
        css_class = ''
    return {
        'sort': sort,
        'link': '?sort=%s' % sort,
        'label': label,
        'class': css_class
        }

class MockQueryset(object):
    """
    Wrap a list of objects in an object which pretends to be a QuerySet.
    """

    def __init__(self, objects):
        self.objects = objects
        self.ordered = True

    def _clone(self):
        return self

    def __len__(self):
        return len(self.objects)

    def __iter__(self):
        return iter(self.objects)

    def __getitem__(self, k):
        if isinstance(k, slice):
            return MockQueryset(self.objects[k])
        return self.objects[k]

def get_profile_model():
    app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
    return get_model(app_label, model_name)


SAFE_URL_CHARACTERS = string.ascii_letters + string.punctuation

def quote_unicode_url(url):
    return urllib.quote(url, safe=SAFE_URL_CHARACTERS)
