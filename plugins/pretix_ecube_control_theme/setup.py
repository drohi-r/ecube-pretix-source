from setuptools import setup, find_packages

setup(
    name="pretix-ecube-control-theme",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "pretix.plugin": [
            "pretix_ecube_control_theme=pretix_ecube_control_theme:PretixPluginMeta",
        ],
    },
)