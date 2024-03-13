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


.PHONY: all
all: $(DESKTOP) $(DESC) $(METAINFO) $(TRANSLATION)

%.desktop: %.desktop.in
	intltool-merge -d translations $< $@

%.metainfo.xml: %.metainfo.xml.in
	intltool-merge -d translations -x $< $@

locale/%/LC_MESSAGES/galternatives.mo: translations/%.po
	mkdir -p $(dir $@)
	msgfmt --statistics -o $@ $<

.PHONY: extract
extract: translations/POTFILES.in
	(cd translations; intltool-update -g galternatives -p)

translations/POTFILES.in: $(SRC) $(DESKTOP_SRC) $(DESC_SRC) $(METAINFO_SRC) $(GLADE)
	echo '[encoding: UTF-8]' > $@
	echo $? | sed -e 's/ /\n/g' >> $@

%.glade: %.ui
	ln -s $(notdir $<) $@

.PHONY: update
update: $(TRANSLATION_SRC:.po=.update.po)

%.update.po: %.po
	msgmerge -o $@ $< translations/galternatives.pot
	mv $@ $<

.PHONY: clean
clean:
	rm -f $(DESKTOP) $(DESC) $(UI:.ui=.glade) translations/POTFILES.in
	rm -rf locale
