from setuptools import setup, find_packages
from bdshare import __version__ , __author__


with open('README.md') as readme_file:
    README = readme_file.read()

with open('CHANGELOG.md') as history_file:
    HISTORY = history_file.read()

setup_args = dict(
    name='bdshare',
    version=__version__,
    description='A utility for crawling historical and Real-time Quotes of dse',
    long_description_content_type="text/markdown",
    long_description=README + '\n\n' + HISTORY,
    license='MIT',
    packages=find_packages(),
    author=__author__,
    author_email='raisul.exe@gmail.com',
    keywords=['crawling', 'dse'],
    url='https://github.com/rochi88/bdshare',
    download_url='https://github.com/rochi88/bdshare/archive/master.zip'
)

install_requires = [
    'beautifulsoup4',
    'requests',
    'html5lib',
    'pandas'
]

classifiers = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Topic :: Software Development :: Libraries :: Python Modules',
]

if __name__ == '__main__':
    setup(**setup_args, install_requires=install_requires, classifiers=classifiers)
