from setuptools import setup, find_packages

setup(
    name="speed-the-arxiv",
    version="1.0.0",
    description="A Flask web app for searching and managing arXiv papers with SciRate integration.",
    author="Your Name",
    author_email="scali.stefano@gmail.com",
    packages=find_packages(),
    py_modules=["speedthearxiv"],
    install_requires=[
        "Flask",
        "requests",
        "feedparser",
        "PyYAML",
        "habanero",
        "waitress",
        "beautifulsoup4",
        "aiohttp"
    ],
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "speedthearxiv=speedthearxiv:main"
        ]
    },
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: Flask",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)