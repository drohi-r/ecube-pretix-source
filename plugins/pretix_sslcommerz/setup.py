from setuptools import setup, find_packages

setup(
    name='pretix-sslcommerz',
    version='1.0.0',
    description='SSLCommerz payment gateway plugin for pretix',
    author='Ecube Entertainment',
    license='Apache Software License',
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    install_requires=[
        'pretix',
        'requests',
    ],
    entry_points={
        'pretix.plugin': [
            'pretix_sslcommerz=pretix_sslcommerz:PretixPluginMeta',
        ],
    },
)
