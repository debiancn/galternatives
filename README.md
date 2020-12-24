**Note:** [GitHub mirror](https://github.com/debiancn/galternatives) is also available for forking/PR/translating.

G Alternatives is a tool that provides a simple GUI interface for `update-alternatives`, allowing system administrator to select which programs provide specific services for the user by default. Some advanced features are also provided, including adding/removing/editing alternative groups/options or managing a custom database directory.

Python 3 required. It's intended to be installed via `apt install galternatives`, but for those who don't like to install, the tarball (`python3 -m galternatives`) should also work.

Any question or enhancement is welcomed. Please send your feedback to package
maintainers of `galternatives` [package in Debian](https://tracker.debian.org/pkg/galternatives)
or submit bugs onto Debian Bug Tracking System (BTS) using `reportbug` tool in
Debian.

Requirements
-------------
Gtk+ >= 3.10  
python3  
python3-gi  
gettext (for i18n support)

Packaging repository
------------------------

* Official packaging and development repository: [Salsa chinese-team/galternatives](https://salsa.debian.org/chinese-team/galternatives)

License
---------
GPL-1+ for the whole project. See `LICENSE.GPL-1`, `LICENSE.GPL-2` and `LICENSE.GPL-3`
for full license text. GPL-2 is chosen as the representative (`LICENSE` file).
