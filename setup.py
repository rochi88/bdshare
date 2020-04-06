from setuptools import setup, find_packages

with open('README.md') as readme_file:
    README = readme_file.read()

with open('HISTORY.md') as history_file:
    HISTORY = history_file.read()

setup_args = dict(
    name='dshare',
    version='0.0.1',
    description='A utility for crawling historical and Real-time Quotes',
    long_description_content_type="text/markdown",
    long_description=README + '\n\n' + HISTORY,
    license='MIT',
    packages=find_packages(),
    author='Raisul Islam',
    author_email='raisul.exe@gmail.com',
    keywords=['backtrader','backtester'],
    url='https://github.com/rochi88/dshare',
    download_url='https://github.com/rochi88/dshare/archive/master.zip'
)

install_requires = [
    'beautifulsoup4',	# tushare require
    'lxml', # tushare require
    'xlrd', # tushare require
    'requests', # tushae require
    'pandas'
]

if __name__ == '__main__':
    setup(**setup_args, install_requires=install_requires)