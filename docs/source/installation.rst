============
Installation
============

This walks you through installing Miro LocalTv on your system.


Setting up virtualenv (optional)
================================

You don't necessarily need to use virtualenv, but it is highly
recommended.  Indeed, the rest of the tutorial assumes that you do.
You *can* manually manage your pythonpath and etc, but virtualenv does
that all for you and gives you a nice isolated environment.  This is
great, for example, if you have multiple websites that all need
different Django versions, using multiple virtualenv environments can
help isolate them all so that they can cleanly coexist on the same
server.

To install virtualenv, use ``easy_install``::

    sudo easy_install -UaZ virtualenv

to get the base virtualenv executable installed on your system (which
is really just used for setting up virtualenv environments).

See http://pypi.python.org/pypi/virtualenv for more details.


Installing Django, LocalTv and dependencies
===========================================

Building the virtual environment
--------------------------------

Assuming you already have the virtualenv executable installed, you can
install a virtualenv environment like so::

    virtualenv /path/to/virtualenv

replacing ``/path/to/virtualenv`` with the directory you want the
virtual environment to be in.

To activate the virtual enviroment, ``cd`` to the virtual environment
directory and type the command::

    source bin/activate

You later deactivate the virtual environment with::

    deactivate


Building the directory structure
--------------------------------
Recommended additional directories


The general structure looks like this:

* *bin/*: binaries and executables

* *include/*: links to python binaries & etc

* *lib/*: python modules, both stdlib, those installed with
  setuptools, and those not in development

You don't have to do this, but I think this makes for a pretty clean
virtualenv environment to add these following directories:

* *src/*: python modules in development

* *djangoproject/*: subdirectories with django settings and root
  urls for different sites should live in here

* *htdocs/*: A directory for most of your static media

  - *static/*: Usually site-specific static media.  (Good to make a git repository for this location or whatever)

    * *images/*: images for the look and feel of this particular site

    *  *js/*: javascript for the look and feel of this
       particular site

    * *css/*: css for the look and feel of this particular
      site

    * *templates/*: templates, such as base.html, to define
      the base look of your site, as well as a place to override
      app-specific templates on a site level

  - *admin/*: symlink the directory to django's static admin
    resources here.  Not totally necessary but it makes things a bit
    easier.

  - *site_media/*: the site_media directory for django.  Django
    apps install stuff here, so it will most likely be dynamically
    populated

* *var/*: kinda like system /var

  - *pid/*: put your pidfiles for django & etc here

  - *var/log/*: django logfiles & etc go here

  - *var/db/*: A nice place to put your sqlite database, if that is
    what you are using


Django
------

Presently LocalTv works with Django 1.0.2.  While in the virtualenv
environment you can type the following::

    easy_install -UaZ Django

This should do everything you need for django, including putting it in
the virtualenv python path.

Dependencies
------------

Installing dependencies will be a little bit tricker.  In general, it
is recommended that you do these svn/git checkouts in the *src/*
directory described in [[recommended additional directories]].

::

    cd src/

You are welcome to use a different directory structure, but you will
need to figure out how to modify ``easy_install.pth`` for your needs on
your own.

DjangoOpenId
------------

Problem is that it has some outdated crap in it.  We might need to
fork it with git::

    svn co http://django-openid.googlecode.com/svn/trunk DjangoOpenid

This also needs several dependencies which are easily installed::

    easy_install -UaZ elementtree
    easy_install -UaZ python-urljr
    easy_install -UaZ python-yadis
    easy_install -UaZ http://openidenabled.com/files/python-openid/packages/python-openid-1.2.0.tar.gz


DjangoEvolution
---------------

::

    svn co http://django-evolution.googlecode.com/svn/trunk/ django-evolution

lxml
----

If you're running a recent version of Debian or Ubuntu, the following
should be sufficient::

    sudo apt-get install python-lxml

Otherwise, consult the [[http://codespeak.net/lxml/installation.html][lxml install docs]].


LocalTv
-------

::

    git clone https://git.participatoryculture.org/localtv LocalTv


VidScraper
----------

::

    git clone https://git.participatoryculture.org/vidscraper VidScraper

You'll also need to install simplejson::

    easy_install -UaZ simplejson


Modifying easy_install.pth
--------------------------

From the base of your virtualenv environment, open the file at::

    editor ./lib/python2.*/site-packages/easy-install.pth

Where python2.* is the python version used in your virtualenv.

Your ``easy-install.pth`` probably looks something like::

    import sys; sys.__plen = len(sys.path)
    ./setuptools-0.6c8-py2.5.egg
    ./Django-1.0.2_final-py2.5.egg
    import sys; new=sys.path[sys.__plen:]; del sys.path[sys.__plen:]; p=getattr(sys,'__egginsert',0); sys.path[p:p]=new; sys.__egginsert = p+len(new)

The first and last lines in this file should be preserved as-is.  The
lines between that are directories that add to your ``PYTHONPATH`` when in
the virtualenv environment.

As you can see, paths can be relative.  Modify your file to look like so::

    import sys; sys.__plen = len(sys.path)
    ./setuptools-0.6c8-py2.5.egg
    ./Django-1.0.2_final-py2.5.egg
    ../../../src/django-evolution
    ../../../src/DjangoOpenid
    ../../../src/LocalTv
    ../../../src/VidScraper
    ../../../djangoproject
    import sys; new=sys.path[sys.__plen:]; del sys.path[sys.__plen:]; p=getattr(sys,'__egginsert',0); sys.path[p:p]=new; sys.__egginsert = p+len(new)

Now you should be able to import python modules out of the added directories.


Setting up the django projects
==============================

We are going to need to make multiple projects, one for the 'main
site' and one for each community subsite.


"mainsite" django project
-------------------------

Change to your djangoproject directory, as created earlier in
[[recommended additional directories]]::

    cd djangoproject/

Assuming we installed Django as described earlier, and that we have
activated our virtualenv environment, we should have the command
``django-admin.py`` in our ``PATH``.  (It should be hosted in the bin/
directory of our virtualenv environment.)  We'll use that to make the
basis of our mainsite project::

    django-admin.py startproject mainsite_project

(Note that you don't necessarily have to append _project to all of
your django projects, but I do so to avoid naming conflicts)

settings.py
-----------

Edit your ``mainsite_project/settings.py``.  Fill out the usual stuff,
including:

* the database configuration
* the MEDIA_ROOT, MEDIA_URL, ADMIN_MEDIA_PREFIX variables

Change ROOT_URLCONF to be::

    ROOT_URLCONF = 'mainsite_project.urls'

Add the path to your site-level templates, like so::

    TEMPLATE_DIRS = (
        "/path/to/virtualenv/htdocs/static/templates/",
    )

If you want to use the OpenId template versions that are bundled with
LocalTv, also add an entry for the override_templates directory, like
so::

    TEMPLATE_DIRS = (
        "/path/to/virtualenv/htdocs/static/templates/",
        "/path/to/virtualenv/src/LocalTv/localtv/override_templates/",
    )


Append "django.contrib.admin", "django_evolution", and "localtv" to
your INSTALLED_APPS::

    INSTALLED_APPS = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
        'django.contrib.admin',
        'django_evolution',
        'localtv',
    )


.. Note::

   In the future, we will need to add django_openidconsumer
   here.


urls.py
-------

::

    from django.conf.urls.defaults import *

    from django.contrib import admin
    admin.autodiscover()

    urlpatterns = patterns('',
        (r'^djadmin/(.*)', admin.site.root),
        (r'', include('localtv.mainsite.urls')),
    )


Sync the database
-----------------

::

    django-admin.py syncdb --settings=mainsite_project.settings


Subsites
--------

Now you'll need to make django projects for each community local
subsite.  Let's say Chicago is one of our cities.  In the
djangoproject directory::

    mkdir chicago_project
    touch chicago_project/__init__.py


create the site object
----------------------

Fire up the python shell::

    django-admin.py shell --settings=mainsite_project.settings

Import the Site model::

    >>> from django.contrib.sites.models import Site 
    >>> from localtv.models import SiteLocation

Add the site and the sitelocation (obviously replacing the domain name
and name with those appropriate to your site)::

    >>> chicago_site = Site(domain='chicago.example.org', name='Chicago LocalTv')
    >>> chicago_site.save()
    >>> chicago_sitelocation = SiteLocation(site=chicago_site)
    >>> chicago_sitelocation.save()

Be sure to take note of the id... we'll need it::

    >>> print chicago_site.id
    2

Repeat for any other subsites you need.


settings.py
-----------

The code here is pretty minimal in this case.

::

    from mainsite_project.settings import *

    SITE_ID = 2
    ROOT_URLCONF = 'chicago_project.urls'

Fill in SITE_ID with the id you got while creating the site object


urls.py
-------

::

    from django.conf.urls.defaults import patterns, include

    urlpatterns = patterns('',
        (r'', include('localtv.subsite.urls')),
    )



Apache / nginx / web server config
==================================

There are plenty of tutorials out there on how to configure this kind
of thing.  My only point to make is that if you need to use a fastcgi
script with apache or whatever, you want to use the python binary in
the bin/ directory of your virtualenv environment, like::

    #!/var/www/localtv/bin/python
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    os.environ['DJANGO_SETTINGS_MODULE'] = 'mainsite_project.settings'
    from django.core.servers.fastcgi import runfastcgi
    runfastcgi(daemonize='false')
