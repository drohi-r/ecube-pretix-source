from setuptools import find_packages, setup

setup(
    name="pretix-ecubetickets",
    version="1.0.0",
    description="Ecube branded PDF ticket output for Pretix",
    author="Ecube",
    author_email="info@ecube-entertainment.com",
    license="Apache Software License",
    url="https://ecube-entertainment.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "reportlab",
    ],
    entry_points="""
[pretix.plugin]
pretix_ecubetickets=pretix_ecubetickets:PretixPluginMeta
""",
)
