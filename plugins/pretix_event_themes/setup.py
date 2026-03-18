from setuptools import setup, find_packages

setup(
    name="pretix-event-themes",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "pretix.plugin": [
            "pretix_event_themes=pretix_event_themes:PretixPluginMeta",
        ],
    },
)

