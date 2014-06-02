#!/bin/sh

test -d translations && cd translations

for desc in ../descriptions/*.in; do
    intltool-extract --type=gettext/ini ${desc}
done

intltool-update -g galternatives -p

for desch in ../descriptions/*in.h; do
    rm -f ${desch}
done
