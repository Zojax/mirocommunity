"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from caspio_source.models import CaspioSource

from django.contrib.sites.models import Site

from django.test import TestCase

from SOAPpy import WSDL
import os 
WSDL_URL= os.path.join(os.path.dirname(__file__),'API.xml')

class CaspioSourceTest(TestCase):
    
    fixtures = ['localtv.site.json',]
    
    def test_sourcemodel(self):
    	site = Site.objects.get(id=1)
        obj = CaspioSource.objects.create(site=site,id_field_name=1,table_name='test',video_title_field='title',url_field_name='http://some.com')        
    	self.assertEqual(obj.id, 1)
        self.assertEqual(obj.table_name,'test')
        self.assertEqual(obj.video_title_field, 'title')
        self.assertEqual(obj.url_field_name, 'http://some.com')
    
    def test_update_item(self):
        def get_wsdl(self):
            res = WSDL.Proxy(open(WSDL_URL))# wsdl=WSDL.Proxy(WSDL_Url)
            def SelectData(self, *kv, **kw):
                return [{}]
            res.SelectData = SelectData
            return res
        CaspioSource.get_wsdl= get_wsdl
        site = Site.objects.get(id=1)
        obj2 = CaspioSource.objects.create(site=site,id_field_name=1,table_name='test',video_title_field='title',url_field_name='http://some.com')    
        obj2.update_items()
         
        
        
        
          
        
               
        

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}

