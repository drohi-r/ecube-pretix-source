from setuptools import find_packages, setup

setup(
    name="pretix-ecubemail",
    version="1.0.0",
    description="Ecube branded HTML mail renderer for Pretix",
    author="Ecube",
    author_email="info@ecube-entertainment.com",
    license="Apache Software License",
    url="https://ecube-entertainment.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "bleach",
        "css-inline",
    ],
    entry_points="""
[pretix.plugin]
pretix_ecubemail=pretix_ecubemail:PretixPluginMeta
""",
)
