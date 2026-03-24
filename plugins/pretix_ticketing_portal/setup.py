from setuptools import find_packages, setup


setup(
    name="pretix-ticketing-portal",
    version="1.0.0",
    description="Installation-wide ticketing portal homepage for Pretix",
    author="Ecube",
    author_email="info@ecube-entertainment.com",
    license="Apache Software License",
    url="https://ecube-entertainment.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    entry_points="""
[pretix.plugin]
pretix_ticketing_portal=pretix_ticketing_portal:PretixPluginMeta
""",
)
