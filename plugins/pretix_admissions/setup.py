from setuptools import setup, find_packages

setup(
    name="pretix-admissions",
    version="1.2.0",
    description="Standalone admissions credentials and scan logging for Pretix",
    author="Ecube",
    author_email="info@ecube-entertainment.com",
    license="Apache Software License",
    url="https://ecube-entertainment.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    entry_points="""
[pretix.plugin]
pretix_admissions=pretix_admissions:PretixPluginMeta
""",
)