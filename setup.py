import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='abstractrepo-sqlalchemy',
    author='Smoren',
    author_email='ofigate@gmail.com',
    description='Abstract CRUD repository implementation for SqlAlchemy',
    keywords='repo, repository, crud, sqlalchemy',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Smoren/abstractrepo-sqlalchemy-pypi',
    project_urls={
        'Documentation': 'https://github.com/Smoren/abstractrepo-sqlalchemy-pypi',
        'Bug Reports': 'https://github.com/Smoren/abstractrepo-sqlalchemy-pypi/issues',
        'Source Code': 'https://github.com/Smoren/abstractrepo-sqlalchemy-pypi',
    },
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    classifiers=[
        # see https://pypi.org/classifiers/
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: Developers',

        'Topic :: Software Development :: Libraries',
        'Topic :: Database :: Front-Ends',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Utilities',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3 :: Only',

        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
    install_requires=["abstractrepo>=1.4.2", "sqlalchemy>=2.0.0"],
    extras_require={
        'dev': ['check-manifest', 'coverage'],
        'test': ['coverage', 'pytest-asyncio'],
    },
)
