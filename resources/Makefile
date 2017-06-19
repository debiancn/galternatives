DESKTOP_SRC := $(wildcard *.desktop.in)
DESKTOP := $(DESKTOP_SRC:.desktop.in=.desktop)
DESC_SRC := $(wildcard descriptions/*.desktop.in)
DESC := $(DESC_SRC:.desktop.in=.desktop)
GLADE := $(wildcard glade/*.glade)
TRANSLATION_SRC := $(wildcard translations/*.po)
TRANSLATION := $(TRANSLATION_SRC:translations/%.po=locale/%/LC_MESSAGES/galternatives.mo)
SRC := $(wildcard ../galternatives/*.py)
space :=
space +=

.PHONY: all extract update clean

all: $(DESKTOP) $(DESC) $(TRANSLATION)

extract: translations/POTFILES.in $(GLADE:.glade=.glade.in)
	(cd translations; intltool-update -g galternatives -p)
	rm -f $(GLADE:.glade=.glade.in)

update: $(TRANSLATION_SRC:.po=.update.po)

%.desktop: %.desktop.in
	intltool-merge -d translations $< $@

locale/%/LC_MESSAGES/galternatives.mo: translations/%.po
	mkdir -p $(dir $@)
	msgfmt --statistics -o $@ $<

translations/POTFILES.in:
	echo '[encoding: UTF-8]' > $@
	echo $(subst $(space),\\n,$(SRC)) >> $@
	echo $(subst $(space),\\n,$(DESKTOP_SRC)) >> $@
	echo $(subst $(space),\\n,$(DESC_SRC)) >> $@
	echo $(subst $(space),\\n,$(GLADE:.glade=.glade.in)) >> $@

%.glade.in: %.glade
	ln -s $(notdir $<) $@

%.update.po: %.po
	msgmerge -o $@ $< translations/galternatives.pot
	mv $@ $<

clean:
	rm -f $(DESKTOP) $(DESC) translations/POTFILES.in
	rm -rf locale
