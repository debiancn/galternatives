DESKTOP := $(wildcard *.desktop.in)
DESC := $(wildcard descriptions/*.desktop.in)
GLADE := $(wildcard glade/*.glade)
TRANSLATION := $(wildcard translations/*.po)
SRC := $(wildcard ../galternatives/*.py)
space :=
space +=

.PHONY: all update clean

all: $(DESKTOP:.desktop.in=.desktop) $(DESC:.desktop.in=.desktop) $(TRANSLATION:.po=.mo)

extract: translations/POTFILES.in $(GLADE:.glade=.glade.in)
	(cd translations; intltool-update -g galternatives -p)
	rm -f $(GLADE:.glade=.glade.in)

update: $(TRANSLATION:.po=.update.po)

%.desktop: %.desktop.in
	intltool-merge -d translations $< $@

%.mo: %.po
	msgfmt --statistics -o $@ $<

translations/POTFILES.in:
	echo '[encoding: UTF-8]' > $@
	echo $(subst $(space),\\n,$(SRC)) >> $@
	echo $(subst $(space),\\n,$(DESKTOP)) >> $@
	echo $(subst $(space),\\n,$(DESC)) >> $@
	echo $(subst $(space),\\n,$(GLADE:.glade=.glade.in)) >> $@

%.glade.in: %.glade
	ln -s $(notdir $<) $@

%.update.po: %.po
	msgmerge -o $@ $< translations/galternatives.pot
	mv $@ $<

clean:
	rm -f $(DESKTOP:.desktop.in=.desktop) $(DESC:.desktop.in=.desktop) $(TRANSLATION:.po=.mo) translations/POTFILES.in
