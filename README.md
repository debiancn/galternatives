**Note:** [GitHub mirror](https://github.com/debiancn/galternatives) is also available for forking/PR/translating.

G Alternatives is a tool that provides a simple GUI interface for `update-alternatives`, allowing system administrator to select which programs provide specific services for the user by default. Some advanced features are also provided, including adding/removing/editing alternative groups/options or managing a custom database directory.

The program trys to be Python 2/3 compatible, but **with no guarantee**, and support for Python 2 will be dropped in the near future. It's intended to be installed via `apt install galternatives`, but for those who don't like to install, the tarball (`python3 -m galternatives`) should also works.

Any question or enhancement is welcomed. Please send your feedback to package
maintainers of `galternatives` [package in Debian](https://tracker.debian.org/pkg/galternatives)
or submit bugs onto Debian Bug Tracking System (BTS) using `reportbug` tool in
Debian.

Requirements
-------------
Gtk+ >= 3.10  
python-gi  
gettext (for i18n support)

License
---------
GPL-1+
