#!/bin/sh

test -d translations || cd ..

intltool-merge -d translations galternatives.desktop.in galternatives.desktop

for desc in descriptions/*.in; do
    intltool-merge -d translations ${desc} ${desc%.in}
done

cd translations

LANGS=$(find . -name \*.po | cut -d '.' -f 2 | tr -d '/')
for lang in ${LANGS}; do
    echo ${lang}:
    msgfmt --statistics -o ${lang}.mo ${lang}.po
done
