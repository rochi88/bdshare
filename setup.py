from setuptools import setup, find_packages

with open('README.md') as readme_file:
    README = readme_file.read()

with open('HISTORY.md') as history_file:
    HISTORY = history_file.read()

setup_args = dict(
    name='bdshare',
    version='0.0.1',
    description='A utility for crawling historical and Real-time Quotes',
    long_description_content_type="text/markdown",
    long_description=README + '\n\n' + HISTORY,
    license='MIT',
    packages=find_packages(),
    author='Raisul Islam',
    author_email='raisul.exe@gmail.com',
    keywords=['crawling','dse'],
    url='https://github.com/rochi88/bdshare',
    download_url='https://github.com/rochi88/bdshare/archive/master.zip'
)

install_requires = [
    'beautifulsoup4',	# bdshare require
    'lxml', # bdshare require
    'xlrd', # bdshare require
    'requests', # bdshae require
    'pandas'
]

if __name__ == '__main__':
    setup(**setup_args, install_requires=install_requires)