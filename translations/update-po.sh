#!/bin/sh

LANGS=$(find . -name \*.po | cut -d '.' -f 2 | tr -d '/')
for lang in ${LANGS}; do
    echo ${lang}:
    msgmerge -o ${lang}.po.new ${lang}.po galternatives.pot
    mv ${lang}.po.new ${lang}.po
done
