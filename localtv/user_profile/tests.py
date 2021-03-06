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

"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import Client
from django.core.files.base import File
from django.core.urlresolvers import reverse

from notification import models as notification

from localtv.tests import BaseTestCase
from localtv.user_profile import forms
from localtv import util

Profile = util.get_profile_model()

class ProfileFormTestCase(TestCase):

    fixtures = ['site', 'users']

    def setUp(self):
        self.user = User.objects.get(username='user')
        self.profile = Profile.objects.create(
            user=self.user,
            description='Description',
            location='Location',
            website='http://www.pculture.org/')

    def test_save(self):
        """
        Filling the ProfileForm with data should cause the Profile to be
        updated.
        """
        data = {
            'username': 'newusername',
            'name': 'First Last',
            'email': 'test@foo.bar.com',
            'description': 'New Description',
            'location': 'Where I am',
            'website': 'http://www.google.com/'
            }
        form = forms.ProfileForm(data, instance=self.user)
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEquals(instance.username, 'newusername')
        self.assertEquals(instance.first_name, 'First')
        self.assertEquals(instance.last_name, 'Last')
        self.assertEquals(instance.email, 'test@foo.bar.com')
        self.assertEquals(instance.get_profile().description,
                          'New Description')
        self.assertEquals(instance.get_profile().location, 'Where I am')
        self.assertEquals(instance.get_profile().website,
                          'http://www.google.com/')

    def test_save_no_changes(self):
        """
        A blank form should have all the data to simply resave and not cause
        any changes.
        """
        blank_form = forms.ProfileForm(instance=self.user)
        initial = blank_form.initial.copy()
        for name, field in blank_form.fields.items():
            if field.initial:
                initial[name] = field.initial
        form = forms.ProfileForm(initial, instance=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        instance = form.save()
        self.assertEquals(instance.username, self.user.username)
        self.assertEquals(instance.first_name, self.user.first_name)
        self.assertEquals(instance.last_name, self.user.last_name)
        self.assertEquals(instance.email, self.user.email)
        self.assertEquals(instance.get_profile().description,
                          self.profile.description)
        self.assertEquals(instance.get_profile().location,
                          self.profile.location)
        self.assertEquals(instance.get_profile().website,
                          self.profile.website)


class ProfileViewTestCase(BaseTestCase):

    fixtures = ['site', 'users']
    url = reverse('localtv_user_profile')

    def setUp(self):
        BaseTestCase.setUp(self)
        self.user = User.objects.get(username='user')
        self.profile = Profile.objects.create(
            user=self.user,
            description='Description',
            location='Location',
            website='http://www.pculture.org/')

    def test_GET(self):
        """
        A GET request to the user profile view should render the
        'localtv/user_profile/edit.html' template and include a form for
        editing the profile.
        """
        c = Client()
        c.login(username='user', password='password')
        response = c.get(self.url)
        self.assertStatusCodeEquals(response, 200)
        self.assertEquals(response.template[0].name,
                          'localtv/user_profile/edit.html')
        self.assertTrue('form' in response.context[0])

    def test_POST_failure(self):
        """
        A POST request to the user profile view with an invalid form should
        cause the page to be rerendered and include the form errors.
        """
        c = Client()
        c.login(username='user', password='password')
        response = c.post(self.url, {})
        self.assertStatusCodeEquals(response, 200)
        self.assertTrue(response.context['form'].is_bound)
        self.assertFalse(response.context['form'].is_valid())

    def test_POST_success(self):
        """
        Filling the ProfileForm with data should cause the Profile to be
        updated.
        """
        data = {
            'username': 'newusername',
            'name': 'First Last',
            'email': 'test@foo.bar.com',
            'description': 'New Description',
            'location': 'Where I am',
            'website': 'http://www.google.com'
            }
        c = Client()
        c.login(username='user', password='password')
        response = c.post(self.url, data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        user = User.objects.get(pk=self.user.pk)
        self.assertEquals(user.username, 'newusername')
        self.assertEquals(user.first_name, 'First')
        self.assertEquals(user.last_name, 'Last')
        self.assertEquals(user.email, 'test@foo.bar.com')
        self.assertEquals(user.get_profile().description,
                          'New Description')
        self.assertEquals(user.get_profile().location, 'Where I am')
        self.assertEquals(user.get_profile().website,
                          'http://www.google.com/')

    def test_POST_delete_logo(self):
        """
        If the 'delete_logo' POST argument is present, the logo should be
        deleted.
        """
        self.profile.logo = File(
            file(self._data_file('logo.png')))
        self.profile.save()
        self.assertTrue(self.profile.logo)

        data = {
            'username': self.user.username,
            'name': self.user.get_full_name(),
            'email': self.user.email,
            'delete_logo': 'yes'
            }

        c = Client()
        c.login(username='user', password='password')
        response = c.post(self.url, data)
        self.assertStatusCodeEquals(response, 302)
        self.assertEquals(response['Location'],
                          'http://%s%s' % (
                self.site_location.site.domain,
                self.url))

        user = User.objects.get(pk=self.user.pk)
        profile = user.get_profile()
        self.assertFalse(profile.logo)

class NotificationsFormTestCase(TestCase):

    fixtures = ['site', 'users']

    def test_user_settings(self):
        """
        A regular user should only see the 'video_approved' and 'video_comment'
        notifications.  The initial data for the form should have those
        settings enabled, since they're on by default.
        """
        user = User.objects.get(username='user')
        form = forms.NotificationsForm(instance=user)
        self.assertEquals(len(form.fields['notifications'].choices), 2)
        self.assertEquals(form.initial, {
                'notifications': ['video_approved', 'video_comment']
                })

    def test_save_user_settings(self):
        """
        Saving the form should save the user's settings.
        """
        user = User.objects.get(username='user')
        form = forms.NotificationsForm({'notifications': []}, instance=user)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        for label in 'video_comment', 'video_approved':
            notice_type = notification.NoticeType.objects.get(label=label)
            self.assertFalse(notification.should_send(user, notice_type, "1"))

        form = forms.NotificationsForm({'notifications': ['video_approved']},
                                       instance=user)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        notice_type = notification.NoticeType.objects.get(
            label='video_approved')
        self.assertTrue(notification.should_send(user, notice_type, "1"))

    def test_admin_settings(self):
        """
        Admins should have the full range of settings available.
        """
        admin = User.objects.get(username='admin')
        form = forms.NotificationsForm(instance=admin)
        self.assertEquals(len(form.fields['notifications'].choices), 7)
        self.assertEquals(form.initial, {
                'notifications': ['video_approved', 'video_comment',
                                  'admin_new_playlist']
                })

        superuser = User.objects.get(username='superuser')
        form = forms.NotificationsForm(instance=superuser)
        self.assertEquals(len(form.fields['notifications'].choices), 7)
        self.assertEquals(form.initial, {
                'notifications': ['video_approved', 'video_comment',
                                  'admin_new_playlist']
                })

    def test_save_admin_settings(self):
        """
        Saving the form should save the admin's settings.
        """
        for username in 'admin', 'superuser':
            admin = User.objects.get(username=username)
            form = forms.NotificationsForm({'notifications': [
                        'admin_new_comment',
                        'admin_new_submission',
                        'admin_queue_daily',
                        'admin_queue_weekly']}, instance=admin)
            self.assertTrue(form.is_valid(), form.errors)
            form.save()
            for label in 'video_comment', 'video_approved':
                notice_type = notification.NoticeType.objects.get(label=label)
                self.assertFalse(notification.should_send(admin, notice_type,
                                                          "1"))
            for label in ('admin_new_comment', 'admin_new_submission',
                          'admin_queue_daily', 'admin_queue_weekly'):
                notice_type = notification.NoticeType.objects.get(label=label)
                self.assertTrue(notification.should_send(admin, notice_type,
                                                         "1"))

