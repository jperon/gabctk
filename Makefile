com:
	cp python.com gabctk.com
	zip -r gabctk.com .args ./*.py midiutil/*.py abc2xml/*.py

release: com
	zip gabctk.zip gabctk.com

run:
	python gabctk.py
