import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
def _read_file(filename):
    try:
        with open(os.path.join(here, filename)) as f:
            return f.read()
    except IOError:  # Travis???
        return ''
README = _read_file('README.rst')
CHANGES = _read_file('CHANGES.rst')


setup(name='repoze.retry',
      version='2.1',
      description='Middleware which implements a retryable exceptions',
      long_description=README + '\n\n' + CHANGES,
      long_description_content_type="text/x-rst",
      classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware",
        ],
      python_requires=">=3.9",
      install_requires=[
        'setuptools',
      ],
      keywords='wsgi middleware retry',
      author="Agendaless Consulting",
      author_email="repoze-dev@lists.repoze.org",
      url="http://www.repoze.org",
      license="BSD-derived (http://www.repoze.org/LICENSE.txt)",
      packages=find_packages(),
      include_package_data=True,
      namespace_packages=['repoze'],
      zip_safe=False,
      test_suite = "repoze.retry.tests",
      entry_points="""
      [paste.filter_app_factory]
      retry = repoze.retry:make_retry
      """,
)
