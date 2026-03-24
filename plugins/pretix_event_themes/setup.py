from setuptools import setup

setup(
    name="pretix-event-themes",
    version="1.0.0",
    packages=[
        "pretix_event_themes",
        "pretix_event_themes.services",
        "pretix_event_themes.migrations",
    ],
    package_dir={"pretix_event_themes": "."},
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "pretix.plugin": [
            "pretix_event_themes=pretix_event_themes:PretixPluginMeta",
        ],
    },
)
