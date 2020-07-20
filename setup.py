# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Scrapy project for feeds into INSPIRE-HEP (http://inspirehep.net)."""

from setuptools import setup, find_packages

readme = open('README.rst').read()

install_requires = [
    'autosemver==0.5.2',
    'jsonresolver==0.2.1',
    'Twisted==17.5.0',
    'Automat==0.6.0',
    'dulwich==0.17.3',
    'inspire-schemas==59.3.2',
    'inspire-crawler==1.1.2',
    'invenio-celery==1.0.0b2',
    'invenio-pidstore==1.0.0',
    'invenio-i18n==1.0.0',
    'invenio-rest==1.0.0',
    'invenio-files-rest==1.0.0b1',
    'invenio-records-rest==1.4.2',
    'invenio-records-files==1.0.0a11',
    'invenio-accounts==1.0.2',
    'pluggy==0.12.0',
    'cookiecutter==1.4.0',
    'invenio-base==1.0.2',
    'Flask-Breadcrumbs==0.4.0',
    'pyasn1-modules==0.0.9',
    'Scrapy==1.4.0',
    # TODO: unpin once they support wheel building again
    'scrapyd==1.2.0',
    'scrapyd-client==1.0.1',
    'six==1.11.0',
    'requests==2.20.0',
    'celery==3.1.26.post2',
    'redis==2.10.6',
    'pyasn1==0.2.3',  # Needed for dependency resolving.
    'LinkHeader==0.4.3',
    'furl==0.5.6',
    'ftputil==3.3.1',
    'python-dateutil==2.6.1',
]

tests_require = [
    'check-manifest==0.41',
    'coverage==4.5.4',
    'isort==4.2.2',
    'pytest==4.6.4',
    'pytest-cov==2.10.0',
    'pytest-pep8==1.0.6',
    'responses==0.5.1',
    'pydocstyle==1.0.0',
    'freezegun==0.3.11'
]

extras_require = {
    'docs': [
        'Sphinx>=1.4',
    ],
    'tests': tests_require,
    'sentry': [
        'raven==5.1.1',
        'scrapy-sentry',
    ],
}

setup_requires = [
    'pytest-runner~=2.7.0',
]

extras_require['all'] = []
for name, reqs in extras_require.items():
    extras_require['all'].extend(reqs)


URL = 'https://github.com/inspirehep/hepcrawl'

setup(
    name='hepcrawl',
    packages=find_packages(),
    description=__doc__,
    long_description=readme,
    url=URL,
    bugtracker_url=URL + '/issues/',
    author="CERN",
    author_email='admin@inspirehep.net',
    entry_points={'scrapy': ['settings = hepcrawl.settings']},
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    autosemver=True,
    setup_requires=setup_requires,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=extras_require,
    package_data={
        'hepcrawl': ['*.cfg'],
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Environment :: Console',
        'Framework :: Scrapy',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
)
