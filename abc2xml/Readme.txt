---- abc2xml ----

abc2xml is a command line utility that translates ABC notation into MusicXML.

Most elements from ABC are translated, but some translations are only partially
implemented. In general %%commands are not implemented except:
- %%score, %%staves. When multiple %%score instructions are present only the first one is honoured.
- %%scale, %%pagewidth, %%pageheight, %%leftmargin and %%rightmargin. The scale value is
the distance between two stafflines in millimeters. The other values are also in millimeters unless
they are followed by a unit (cm,in,pt).
- %%MIDI program and %%MIDI channel (or I:MIDI ..) are translated when used in a current voice
(i.e. after a V: definition). Instrument/channel changes mid-voice are translated to a text direction
which carries the midi parameters as playback setting. In %%MIDI program num, the number should range from
0 to 127. In %%MIDI channel num, the number is starts from one. The midi translation supports
mapping multiple voices whith different instruments to one stave. (i.e. the resulting xml part will
have multiple instruments). This feature, though present in MusicXML is not supported by MuseScore,
nor by Finale Notepad. These programs only allow one instrument per stave.
- %%MIDI transpose is translated and has the same effect as transpose= in the clef, i.e.
only play back is transposed, not notation.
- %%MIDI drummap is translated to an equivalent I:percmap
- All %%instructions can be inlined: %%command ... == [I:command ...]

---- Usage: ----

When you have Python installed:
> python abc2xml.py [-h] [-r] [-m SKIP NUM] [-o DIR] [-p PFMT] [-z MODE] [--meta MAP] file1 [file2 ...]

When you use the Win32 executable:
> abc2xml.exe [-h] [-r] [-m SKIP NUM] [-o DIR] [-p PFMT] [-z MODE] file1 [file2 ...]

Translates all .abc files in the file list to MusicXML. Output goes to stdout unless the -o option
is given. Wildcards in file names are expanded.
Option -h prints help message with explanation of the options
Option -r shows whole measure rests in a merged staff. Otherwise (default), when a voice has no notes
in a particular measure, the corresponding rest (of a whole measure) will not be shown when the voice
is merged with other voices that do have notes in that measure.
Option -m skip num skips skip tunes and then reads at most num tunes.
Can be used when abc files contain multiple tunes (tune books) to select only a subset of the tunes.
The default skips nothing (skip=0) and reads 1 tune (num=1).
Option -o dir translates every .abc file to a separate .xml file with the same name
into directory dir. For example, -o. puts all xml files into the same directory where
the input files reside.
Option -p fmt sets the page format of the ouput. fmt should be a string with 7 floating point
values sepatated by comma's without any spaces. The values are: scale, page-height, -width, and
page margin left, -right, -top, -bottom. A scale value of 1.0 sets the distance between two staff
lines to 6pt (2.117 mm). When the -p option is omitted the values default to A4 with left/right margins
of 18 mm, top/bottom marings of 10 mm and scale = 0.75. The margin values are in millimeters.
Option -z mode or --mxl mode writes compressed xml files with extention .mxl.
If mode is a or add both .xml and .mxl files will be written. If mode is r or replace only .mxl
files are written.
Option --meta map defines a mapping of ABC info fields onto MusicXML meta data types. The map is a string
without spaces and using comma as separator. It specifies the MusicXML tag name for one or more ABC info
field headers. For instance: --meta R:poet,Z:translator maps the R: info field onto the poet meta data
type, and the Z: info field onto the translator meta data type. Valid MusicXML meta data types are:
composer, lyricist, poet, arranger and translator. It depends on the music editor used, where and if the
meta data appears on the score front page. MuseScore, for instance, displays composer, poet and translator
in various useful positions in the header of the score.
There are two default mappings: C: is mapped to the composer meta data type and S: is mapped to the
source meta data type. All other ABC info fields: R:,Z:,N:,O:,A:,G:,H:,B:,D:,F: are by default translated
to the miscellaneous meta data type, unless the user provides a mapping for them with the --meta option.

---- Download ----

The python script: abc2xml.py-71.zip
http://wim.vree.org/svgParse/abc2xml.py-71.zip

Stand alone win32 executable: abc2xml.exe-71.zip
http://wim.vree.org/svgParse/abc2xml.exe-71.zip

---- Non standard additions: ----

 (may change when a different ABC standard would be decided).

- jazz chord symbols. A whole bunch of them. When a chord symbol is not recognized it is translated
as text annotation.
- glissando&apos;s are implemented as decorations of the note where the glissando starts and
the note where it ends. For instance: !-(! C D E !-) F G draws a glissando from C to F. A glissando
can start and end on notes within a chord. There may be more parallel glissando&apos;s. There is a
wavy glissando and one with a streight line: !-(! ... !-)! and !~(! ... !~)!
- tremolo: Single or between two chords (or notes). A single tremolo is indicated by a
decoration: !/!, !//! or !///!. The number of slashes translates to the number of bars of the tremolo.
A tremolo between two chords (or notes) is given by decorating the first one with !/-!, !//-! or !///-!.
For instance: !/-![CGE][CGE] or !///-!CC.
- percussion maps. A voice (V:) of key (K:) definition can have the attribute map=perc. When this
attribute is specified, all voices of the current part are considered as percussion voices. Parts are
defined by the I:score instruction. When no I:score is present, each voice becomes a separate part. When
[K:map=off] is encountered percussion mapping is switched off and following notes are translated normally.
 For a percussion part notes can be mapped to percussion instruments by a percussion map. For each
percussion insturment an I:percmap should be defined, as follows:
I:percmap abc-note staff-step midi-number [xml-notehead]

abc-note = abc note name in the music code (^A,,)
 staff-step = an abc note without accidental (E,). This is how the note appears on the staff.
Also an * can be specified, which then takes its value from abc-note.
 midi-number = 0-based number for midi channel 10 instrument. (or an equivalent abc note like F,, for 41
or even an * which copies its value from abc-note)
 xml-notehead (optional) = text that is literally copied into the xml notehead element (e.g. x or circle-x).
An appended plus/minus sign translates to a filled/open noteshape (e.g. diamond+, square+, normal-). A filled
halve note will look like a quarter. An empty quarter looks like a halve note. Without appended sign the filling
is determined by the duration of the note (default behaviour).
- An I:percmap is valid for all voices in the part in which it occurs (from the metrical position onwards).
When defined in the header it is valid for all voices.
- When clef=perc or map=perc is found and no percmap is present, suitable percmap entries are derived. The new entries
map encountered abcnotes to an equivalent midi note number. Also accidentals ^_ are mapped to noteheads x and circle-x.
(when I:percmap instructions were present in the abc code, also a warning message is issued that an entry is missing)