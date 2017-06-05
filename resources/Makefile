DESKTOP := $(wildcard *.desktop.in)
DESC := $(wildcard descriptions/*.desktop.in)
GLADE := $(wildcard glade/*.glade)
TRANSLATION := $(wildcard translations/*.po)
SRC := $(wildcard ../galternatives/*.py)
space :=
space +=

.PHONY: all clean

all: $(DESKTOP:.desktop.in=.desktop) $(DESC:.desktop.in=.desktop) $(TRANSLATION:.po=.mo)

%.desktop: %.desktop.in
	intltool-merge -d translations $< $@

descriptions/%.desktop: descriptions/%.desktop.in
	intltool-merge -d translations $< $@

translations/%.mo: translations/%.po
	msgfmt --statistics -o $@ $<

extract: translations/POTFILES.in
	(cd translations; intltool-update -g galternatives -p)

translations/POTFILES.in:
	echo '[encoding: UTF-8]' > $@
	echo $(subst $(space),\\n,$(SRC)) >> $@
	echo $(subst $(space),\\n,$(DESKTOP)) >> $@
	echo $(subst $(space),\\n,$(DESC)) >> $@
	echo $(subst $(space),\\n,$(GLADE)) >> $@


update:
	$(foreach oldpo, $(TRANSLATION), \
		msgmerge -o $(oldpo).new $(oldpo) translations/galternatives.pot; \
		mv $(oldpo).new $(oldpo); \
	)

clean:
	rm -f $(DESKTOP:.desktop.in=.desktop) $(DESC:.desktop.in=.desktop) $(TRANSLATION:.po=.mo) translations/POTFILES.in
