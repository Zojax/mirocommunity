"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from caspio_source.models import CaspioSource

from django.contrib.sites.models import Site

from django.test import TestCase


class CaspioSourceTest(TestCase):
    
    fixtures = ['localtv.site.json',]
    
    def test_sourcemodel(self):
    	site = Site.objects.get(id=1)
        obj = CaspioSource.objects.create(site=site)        
    	self.assertEqual(obj.id, 1)
        

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}

