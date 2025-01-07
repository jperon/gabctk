Gabctk
======

Tool to work on gabc files.

Gabc
----

*gabc* is the language used by the
[Gregorio](https://gregorio-project.github.io/)
software.
You can find the description [here](https://gregorio-project.github.io/gabc/).


Gabctk
------

This script is derived from [gabc2mid](https://github.com/jperon/gabc2mid);
as the scope of the project has grown, gabc2mid will remain as it is now
( except for bug fixes), and the developments will take place here.
Gabctk parses the *gabc* code, extracts what concerns the melody,
and produces it as a midi and/or lilypond file, abc,
musicxml file.
It can also extract the text in a text file.
The syntax is the following:

    gabctk.py -i </path/to/file/source.gabc> \
             [-n title] \
             [-o </path/to/file/destination.mid>] \
             [-l </path/to/file/destination.ly>] \
             [-c </path/to/file/destination.abc>] \
             [-x </path/to/file/destination.xml>] \
             [-b </path/to/file/destination.tab>] \
             [-e </path/to/file/destination.txt>] \
             [-m </path/to/file/destination.mus>] \
             [-t tempo] \
             [-d transposition] \
             [-a alert] \
             [-v verbosity]

All the options in square brackets are optional. `gabc -h` displays a short help.

If, instead of a filename, you want to use the standard input or output, specify `-`. For example, to listen to a gabc with `timidity` :

    gabctk.py -i <file/source.gabc> -o - | timidity -

Or, to extract the text from the gabc and display it:

    gabctk.py -i <file/source.gabc> -e -

The tempo is expressed in beats per minute:
its default value is 165.

Transposition is expressed in semitones. In its absence, gabctk will automatically transpose the song to an easy-to-sing range. For the formats
abc and musicxml formats, the management of the transposition is left to abc and the
software compatible with these formats. The notes will therefore remain
graphically in place, but the melody will be played at the pitch indicated by
this parameter.

If alerts are defined, gabctk will return a message each time it detects the
it detects the string in the song text.
For example, `gabctk.py -i \<File.gabc\> -a j -a eumdem` will return a message
if the text contains *j* or the word *eumdem*.

It is also possible to convert several files at the same time. In this case,
parameter to `-o`, `-l`, `-c`, `-x` or `-b` is a folder and not an individual file. For example, to convert to midi all
gabc files in the current directory:

    gabctk.py -i *.gabc -o .

Standalone executable
---------------------

Thanks to [cosmopolitan](https://github.com/jart/cosmopolitan/), a standalone
`gabctk.com` executable can be found in [Releases](https://github.com/jperon/gabctk/releases),
or generated from sources with `make com` command (providden `zip` command is available to shell).
Its use is identical to what’s described above, replacing `gabctk.py` by `gabctk.com`.
