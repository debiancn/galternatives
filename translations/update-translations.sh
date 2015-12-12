#!/bin/sh

test -d translations && cd translations

./extract-translations.sh
./update-po.sh
./merge-translations.sh