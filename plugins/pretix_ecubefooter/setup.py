from setuptools import setup, find_packages

setup(
    name='pretix-ecubefooter',
    version='1.0.0',
    description='Ecube custom footer for Pretix',
    author='Ecube Inc.',
    author_email='info@ecube-entertainment.com',
    license='Apache Software License',
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    install_requires=['pretix'],
    entry_points="""
[pretix.plugin]
pretix_ecubefooter=pretix_ecubefooter:PluginApp
""",
)

