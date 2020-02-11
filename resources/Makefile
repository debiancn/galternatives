DESKTOP_SRC := $(wildcard *.desktop.in)
DESKTOP := $(DESKTOP_SRC:.in=)
DESC_SRC := $(wildcard descriptions/*.desktop.in)
DESC := $(DESC_SRC:.in=)
METAINFO_SRC := $(wildcard *.metainfo.xml.in)
METAINFO := $(METAINFO_SRC:.in=)
GLADE := $(wildcard glade/*.glade)
UI := $(wildcard glade/*.ui)
GLADE += $(UI:.ui=.glade)
TRANSLATION_SRC := $(wildcard translations/*.po)
TRANSLATION := $(TRANSLATION_SRC:translations/%.po=locale/%/LC_MESSAGES/galternatives.mo)
SRC := $(wildcard ../galternatives/*.py)
space :=
space +=

.PHONY: all extract update clean

# all

all: $(DESKTOP) $(DESC) $(METAINFO) $(TRANSLATION)

%.desktop: %.desktop.in
	intltool-merge -d translations $< $@

%.metainfo.xml: %.metainfo.xml.in
	intltool-merge -d translations -x $< $@

locale/%/LC_MESSAGES/galternatives.mo: translations/%.po
	mkdir -p $(dir $@)
	msgfmt --statistics -o $@ $<

# extract

extract: translations/POTFILES.in
	(cd translations; intltool-update -g galternatives -p)

translations/POTFILES.in: $(SRC) $(DESKTOP_SRC) $(DESC_SRC) $(METAINFO_SRC) $(GLADE)
	echo '[encoding: UTF-8]' > $@
	echo $(subst $(space),\\n,$(SRC)) >> $@
	echo $(subst $(space),\\n,$(DESKTOP_SRC)) >> $@
	echo $(subst $(space),\\n,$(DESC_SRC)) >> $@
	echo $(subst $(space),\\n,$(METAINFO_SRC)) >> $@
	echo $(subst $(space),\\n,$(GLADE)) >> $@

%.glade: %.ui
	ln -s $(notdir $<) $@

# update

update: $(TRANSLATION_SRC:.po=.update.po)

%.update.po: %.po
	msgmerge -o $@ $< translations/galternatives.pot
	mv $@ $<

# clean

clean:
	rm -f $(DESKTOP) $(DESC) $(UI:.ui=.glade) translations/POTFILES.in
	rm -rf locale
