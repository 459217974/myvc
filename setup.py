#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2021/7/14 11:23
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

install_requires = []
with open("requirements.txt", "r", encoding="utf8") as f:
    for line in f.readlines():
        line = line.strip()
        if line:
            install_requires.append(line)

setuptools.setup(
    name="myvc",
    version="0.0.8",
    author="CaoDa",
    author_email="459217974@qq.com",
    description="A MySQL Version Control Util",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/459217974/myvc",
    project_urls={
        "Bug Tracker": "https://github.com/459217974/myvc/issues",
    },
    classifiers=[
        "Intended Audience :: Developers",
        "Operating System :: Unix",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    install_requires=install_requires,
    entry_points={
        'console_scripts': ['myvc=myvc_app.myvc:main'],
    },
    include_package_data=True,
)
