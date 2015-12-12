#!/bin/sh

test -d translations && cd translations

LANGS=$(find . -name \*.po | cut -d '.' -f 2 | tr -d '/')
for lang in ${LANGS}; do
    echo ${lang}:
    mkdir -p ../debian/galternatives/usr/share/locale/${lang}/LC_MESSAGES
    cp ${lang}.mo ../debian/galternatives/usr/share/locale/${lang}/LC_MESSAGES/galternatives.mo
done
