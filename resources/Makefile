DESKTOP_SRC := $(wildcard *.desktop.in)
DESKTOP := $(DESKTOP_SRC:.in=)
POLICY_SRC := $(wildcard *.policy.in)
POLICY := $(POLICY_SRC:.in=)
DESC_SRC := $(wildcard descriptions/*.desktop.in)
DESC := $(DESC_SRC:.in=)
GLADE := $(wildcard glade/*.glade)
TRANSLATION_SRC := $(wildcard translations/*.po)
TRANSLATION := $(TRANSLATION_SRC:translations/%.po=locale/%/LC_MESSAGES/galternatives.mo)
SRC := $(wildcard ../galternatives/*.py)
space :=
space +=

.PHONY: all extract update clean

all: $(DESKTOP) $(POLICY) $(DESC) $(TRANSLATION)

extract: translations/POTFILES.in
	(cd translations; intltool-update -g galternatives -p)

update: $(TRANSLATION_SRC:.po=.update.po)

%.desktop: %.desktop.in
	intltool-merge -d translations $< $@

%.policy: %.policy.in
	intltool-merge -x translations $< $@

locale/%/LC_MESSAGES/galternatives.mo: translations/%.po
	mkdir -p $(dir $@)
	msgfmt --statistics -o $@ $<

translations/POTFILES.in:
	echo '[encoding: UTF-8]' > $@
	echo $(subst $(space),\\n,$(SRC)) >> $@
	echo $(subst $(space),\\n,$(DESKTOP_SRC)) >> $@
	echo $(subst $(space),\\n,$(POLICY_SRC)) >> $@
	echo $(subst $(space),\\n,$(DESC_SRC)) >> $@
	echo $(subst $(space),\\n,$(GLADE)) >> $@

%.update.po: %.po
	msgmerge -o $@ $< translations/galternatives.pot
	mv $@ $<

clean:
	rm -f $(DESKTOP) $(POLICY) $(DESC) translations/POTFILES.in
	rm -rf locale
