import setuptools

import leyline

setuptools.setup(
    name=leyline.__name__,
    version=leyline.__version__,
    author=leyline.__author__,
    url=leyline.__url__,
    packages=['leyline'],
    python_requires='>=3.7.0',
    include_package_data=True,
    data_files=[
        ('', ['README.md', 'CHANGELOG.md']),
    ],
)
