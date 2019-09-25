import setuptools

import randombag

setuptools.setup(
    name=randombag.__name__,
    version=randombag.__version__,
    author=randombag.__author__,
    url=randombag.__url__,
    packages=['randombag'],
    extras_require={
        'numpy': ['numpy'],
    },
    python_requires='>=3.7.0',
    include_package_data=True,
    data_files=[
        ('', ['README.md', 'CHANGELOG.md']),
    ],
)
