from setuptools import setup, find_packages

setup(
    name="pretix-exclusive-access",
    version="1.0.0",
    description="Approval-gated exclusive access workflow for pretix",
    author="Ecube",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
    entry_points="""
[pretix.plugin]
pretix_exclusive_access=pretix_exclusive_access:PretixPluginMeta
""",
)

