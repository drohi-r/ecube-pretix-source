from setuptools import setup, find_packages

setup(
    name="pretix-ecube-access",
    version="1.0.0",
    description="Ecube Access unified scan orchestration for Pretix",
    author="Ecube",
    author_email="info@ecube-entertainment.com",
    license="Apache Software License",
    url="https://ecube-entertainment.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    entry_points="""
[pretix.plugin]
pretix_ecube_access=pretix_ecube_access:PretixPluginMeta
""",
)