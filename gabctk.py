#! /usr/bin/python3
# -*- coding: UTF-8 -*-

"""GabcTk

Ce programme vise à servir à toutes sortes de traitements sur les fichiers gabc
(cf. [Gregorio](https://gregorio-project.github.io)).

Actuellement, il permet de convertir les gabc en midi et en lilypond, et de
vérifier si certains caractères n'ont pas été saisis dans le texte de la
partition.

"""


# Librairies externes ##################################################

import os
import sys
from argparse import ArgumentParser, FileType
import re
import unicodedata as ud
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from midiutil.MidiFile import MIDIFile  # noqa
from abc2xml import abc2xml  # noqa
abc2xml.info = lambda x, warn=1: x


# Variables globales ###################################################

TITRE = "Cantus"
H_LA = 57  # Le nombre correspond au "pitch" MIDI.
TEMPO = 165
DUREE_EPISEME = 1.7
DUREE_AVANT_QUILISMA = 2
DUREE_POINT = 2.3
DEBUG = False
ABC_ENTETE = '''
X: 1
T: %(titre)s
L: 1/8
M: none
K: clef=treble
K: transpose=%(transposition)s
U: P = !uppermordent!
%(musique)s
w: %(paroles)s
'''

# pylint:disable=W1401
LILYPOND_ENTETE = '''\\version "2.18"

\header {
  title = "%(titre)s"
  tagline = ""
  composer = ""
}

\\paper {
 #(include-special-characters)
}

MusiqueTheme = {
 \\key %(tonalite)s\\major
%(musique)s}

Paroles = \\lyricmode {
%(paroles)s
}

\\score{
  <<
    \\new Staff <<
      \\set Staff.midiInstrument = "flute"
      \\set Staff.autoBeaming = ##f
      \\new Voice = "theme" {
        \\cadenzaOn \\transpose c %(transposition)s{\\MusiqueTheme}
      }
    >>
    \\new Lyrics \\lyricsto theme {
      \\Paroles
    }
  >>
  \\layout{
    \\context {
      \\Staff
      \\override TimeSignature #'stencil = #point-stencil
      \\override Slur #'stencil = ##f
    }
  }
  \\midi{}
}'''


# Méthodes globales ####################################################


def aide(erreur, code, commande=os.path.basename(sys.argv[0])):
    """Affichage de l'aide"""
    # Tenir compte du message propre à chaque erreur, ainsi que du nom
    # sous lequel la commande a été appelée.
    sys.stderr.write(
        ('Erreur : ' + erreur + '\n' if erreur != '' else '')
        + 'Usage : \n    '
        + commande + ' '
        + '-i <input.gabc>\n          '
        + '[-o <output.mid>]\n          '
        + '[-l <output.ly>]\n          '
        + '[-c <output.abc>]\n          '
        + '[-x <output.xml>]\n          '
        + '[-e <texte.txt>]\n          '
        + '[-t <tempo>]\n          '
        + '[-d <transposition>]\n          '
        + '[-n <titre>]\n          '
        + '[-a <alertes>]\n          '
        + '[-v]\n'
        )
    # Renvoyer le code correspondant à l'erreur,
    # pour interagir avec d'autres programmes.
    sys.exit(code)


def traiter_options(arguments):  # pylint:disable=R0912
    """Fonction maîtresse"""
    # Analyse des arguments de la ligne de commande.
    args = ArgumentParser()
    args.add_argument('entree', nargs='*', help='Fichier gabc à traiter')
    args.add_argument(
        '-i', '--input', nargs='*', help='Fichier gabc à traiter'
    )
    args.add_argument(
        '-o', '--midi', nargs='?', help='Sortie Midi',
    )
    args.add_argument(
        '-l', '--lily', nargs='?', help='Sortie Lilypond'
    )
    args.add_argument(
        '-c', '--abc', nargs='?', help='Sortie ABC'
    )
    args.add_argument(
        '-x', '--mxml', nargs='?', help='Sortie MusicXML'
    )
    args.add_argument(
        '-e', '--export', nargs='?',
        help='Ficher texte où exporter les paroles seules'
    )
    args.add_argument(
        '-m', '--musique', nargs='?',
        help='Fichier texte où exporter les notes seules'
    )
    args.add_argument(
        '-b', '--tab', nargs='?', help='Sortie tablature'
    )
    args.add_argument(
        '-t', '--tempo', nargs=1, type=int, help='Tempo en notes par minute',
        default=TEMPO
    )
    args.add_argument(
        '-d', '--transposition', nargs=1, type=int,
        help='Transposition en demi-tons'
    )
    args.add_argument(
        '-n', '--titre', nargs=1, help='Titre de la pièce',
    )
    args.add_argument(
        '-a', '--alerter', nargs='*', help='Caractères à signaler'
    )
    args.add_argument(
        '-v', '--verbose', action='store_true', help='Degré de verbosité'
    )
    opts = args.parse_args(arguments)
    if not opts.entree and opts.input:
        opts.entree = opts.input
    for entree in opts.entree:
        gabctk(entree, opts)


def sansaccents(input_str):
    """Renvoie la chaîne d'entrée sans accents"""
    nkfd_form = ud.normalize('NFKD', input_str)
    return "".join([c for c in nkfd_form if not ud.combining(c)]).replace(
        '℣', 'V'
    )\
        .replace('℟', 'R')\
        .replace('æ', 'ae')\
        .replace('œ', 'oe')\
        .replace('ǽ', 'ae')\
        .replace('œ́', 'oe')


def sortie_verbeuse(debug, gabc, partition):
    """Affichage d'informations de débogage

    − les en-têtes gabc ;
    − la partition gabc (sans les en-têtes) ;
    − la partition (texte et ensemble syllabes/neumes).
    """
    if debug:
        print(gabc.entetes, '\n')
        print(gabc.contenu, '\n')
        print(partition.texte)
        print(partition.syllabes)


# pylint:disable=R0913
def gabctk(entree, opts):
    """Export dans les différents formats"""
    # Extraire le contenu du gabc.
    try:
        f_gabc = FichierTexte(entree)
        gabc = Gabc(f_gabc.contenu)
        nom = f_gabc.nom
    # Si le gabc n'existe pas, afficher l'aide.
    except FileNotFoundError:
        aide('fichier inexistant', 2)
    # Extraire la partition.
    partition = gabc.partition(transposition=opts.transposition)
    titre = \
        opts.titre if opts.titre \
        else gabc.entetes['name'] if 'name' in gabc.entetes \
        else TITRE
    sortie_verbeuse(opts.verbose, gabc, partition)
    # Créer le fichier midi.
    if opts.midi:
        midi = Midi(partition, titre=titre, tempo=opts.tempo)
        midi.ecrire(FichierTexte(opts.midi, nom, '.mid').chemin)
    # Créer le fichier lilypond
    if opts.lily:
        lily = Lily(partition, titre=titre, tempo=opts.tempo)
        lily.ecrire(FichierTexte(opts.lily, nom, '.ly'))
    # Créer le fichier abc
    if opts.abc or opts.mxml:
        abc = Abc(partition, titre=titre, tempo=opts.tempo)
        if opts.abc:
            abc.ecrire(
                FichierTexte(opts.abc, nom, '.abc'), abc=True
            )
        if opts.mxml:
            abc.ecrire(
                FichierTexte(opts.mxml, nom, '.xml'), abc=False, xml=True
            )
    # S'assurer de la présence de certains caractères,
    # à la demande de l'utilisateur.
    # Création d'une variable contenant les paroles.
    paroles = partition.texte
    # S'assurer des alertes définies par l'utilisateur.
    if opts.alerter:
        verifier(opts.alerter, paroles)
    # Si l'utilisateur l'a demandé,
    # écrire les paroles dans un fichier texte.
    if opts.export:
        FichierTexte(opts.export).ecrire(paroles + '\n')
    if opts.musique:
        FichierTexte(opts.musique).ecrire(partition.gabc)
    # Si l'utilisateur l'a demandé,
    # écrire une tablature dans un fichier texte.
    if opts.tab:
        tablature = re.sub(
            '^\s+', '',
            '\n'.join(
                '{0}\t{1}'.format(syllabe, neume.ly) for syllabe, neume in
                zip(partition.syllabes, partition.musique)
            ).replace('\n ', '\n//\n')
        )
        FichierTexte(opts.tab).ecrire(tablature + '\n')


def verifier(alertes, texte):
    """Contrôle de la présence de certains caractères

    (à la demande de l'utilisateur)"""
    for alerte in alertes:
        if alerte in texte:
            sys.stderr.write("!!! " + alerte + " !!!")


# Classes ##############################################################

# # Classes servant à l'analyse du gabc, de la mélodie et des paroles.


class Gabc:
    """Description du fichier gabc"""
    def __init__(self, code):
        self.code = code

    @property
    def parties(self):
        """Tuple contenant d'une part les en-têtes,
        d'autre part le corps du gabc"""
        regex = re.compile('%%\n')
        resultat = regex.split(self.code)
        return resultat

    @property
    def entetes(self):
        """En-têtes du gabc, sous forme d'un dictionnaire"""
        resultat = {
            info[0]: re.sub(
                '^ +| +$', '',
                ':'.join(info[1:]).replace(';', '').replace('\r', '')
            )
            for info in [
                ligne.split(':')
                for ligne in self.parties[0].split('\n')
                if ':' in ligne
                ]
            }
        categories = {
            'alleluia': 'alleluia',
            'antiphona': 'antiphona',
            'antienne': 'antiphona',
            'antiphon': 'antiphona',
            'communio': 'communio',
            'communion': 'communio',
            'graduale': 'graduale',
            'graduel': 'graduale',
            'gradual': 'graduale',
            'hymnus': 'hymnus',
            'hymne': 'hymnus',
            'hymn': 'hymnus',
            'introitus': 'introitus',
            'introit': 'introitus',
            'kyriale': 'kyriale',
            'lectio': 'lectio',
            'leçon': 'lectio',
            'lecon': 'lectio',
            'lesson': 'lectio',
            'offertorium': 'offertorium',
            'offertoire': 'offertorium',
            'offertory': 'offertorium',
            'responsorium': 'responsorium',
            'responsum': 'responsorium',
            'répons': 'responsorium',
            'repons': 'responsorium',
            'response': 'responsorium',
            'sequentia': 'sequentia',
            'sequence': 'sequentia',
            'tractus': 'tractus',
            'trait': 'tractus',
            'tract': 'tractus',
            'versus': 'versus',
            'verset': 'versus',
            'verse': 'versus',
            }
        try:
            categorie = sansaccents(resultat['office-part'].lower())
            if categorie in categories.keys():
                resultat['office-part'] = categorie
            else:
                resultat['office-part'] = 'varia'
        except KeyError:
            resultat['office-part'] = 'varia'
        if 'name' not in resultat:
            resultat['name'] = TITRE
        return resultat

    @property
    def contenu(self):
        """Partition gabc sans en-têtes ni commentaires"""
        resultat = self.parties[1]
        resultat = re.sub('%.*\n', '', resultat)
        resultat = re.sub('\n', ' ', resultat)
        return resultat

    def partition(self, transposition=None):
        """Extraction de la partition à partir du contenu gabc"""
        contenu = self.contenu
        # Signes indiquant les commandes personnalisées (que l'on ignore).
        commandeperso = re.compile("\[[^\[^\]]*\]")
        contenu = commandeperso.sub('', contenu)
        # Signes indiquant que l'on passe du mode texte au mode musique.
        neume = re.compile("\([^\(\)]*\)")
        texte = re.compile("\)?[^\(\)]*\(")
        syllabes = [
            txt.replace('(', '').replace(')', '')
            for txt in texte.findall(contenu)
        ]
        neumes = [
            nme.replace('(', '').replace(')', '')
            for nme in neume.findall(contenu)
        ]
        partition = Partition(
            self.entetes['name'], transposition=transposition
        )
        reprise = re.compile("<i>.*i*j\..*</i>")
        for i, syllabe in enumerate(syllabes):
            rep = reprise.search(syllabe)
            if rep:
                syllabes[i - 2] += ' ' + rep.group(0)
                syllabes[i] = reprise.sub('', syllabe)
        # Extraction des différents signes
        mot = []
        for txt, nme in zip(syllabes, neumes):
            try:
                if txt[0] == ' ':
                    partition.append(Mot(
                        gabc=mot,
                        precedent=partition[-1]
                        if len(partition) else None
                    ))
                    mot = []
            except IndexError:
                partition.append(Mot(
                    gabc=mot,
                    precedent=partition[-1]
                    if len(partition) else None
                ))
                mot = []
            mot.append((txt, nme))
        partition.append(Mot(
            gabc=mot,
            precedent=partition[-1]
        ))
        return partition


class Partition(list):
    """Partition de musique.

    Une partition est un texte orné de musique. Elle contient donc des mots,
    eux-mêmes composés de syllabes, ces dernières ornées de neumes.

    """
    def __init__(self, titre, transposition=None, *args, **params):
        list.__init__(self, *args, **params)
        self.titre = titre
        self.tonalite = ['c', 'M']
        self._transposition = transposition

    @property
    def gabc(self):
        """Code gabc de la musique"""
        return re.sub(
            '(::|:|;)', '\\1\n',
            ' '.join(signe.gabc for signe in self.musique)
        )

    @property
    def musique(self):
        """Liste de signes musicaux"""
        musique = []
        for mot in self:
            musique += mot.musique
        return musique

    @property
    def syllabes(self):
        """Liste des syllabes des mots de la partition"""
        syllabes = []
        for mot in self:
            syllabes += mot
        return syllabes

    @property
    def tessiture(self):
        """Notes extrêmes de la mélodie"""
        minimum = maximum = 0
        # Parcours de toutes les notes de la mélodie, pour déterminer
        # la plus haute et la plus basse.
        for neume in self.musique:
            for note in (notes for notes in neume if isinstance(notes, Note)):
                if minimum == 0 or note.hauteur < minimum:
                    minimum = note.hauteur
                if note.hauteur > maximum:
                    maximum = note.hauteur
        if self._transposition:
            minimum += self._transposition
            maximum += self._transposition
        return {'minimum': minimum, 'maximum': maximum}

    @property
    def texte(self):
        """Texte de la partition"""
        return ' '.join(str(mot) for mot in self)

    @property
    def transposition(self):
        """Transposition automatique de la partition si besoin"""
        if self._transposition is not None:
            return self._transposition
        else:
            # Calcul de la hauteur idéale.
            return 66 - int(sum(self.tessiture.values())/2)


class ObjetLie:  # pylint:disable=R0903
    """Objet lié au précédent

    Cette classe est celle dont héritent chacun des types d'éléments. Elle
    sert surtout à référencer l'élément précédent, de façon à simplifier
    certaines opérations rétroactives.

    """
    def __init__(self, precedent):
        self._precedent = None
        self.precedent = precedent

    def __getattr__(self, attribut):
        try:
            return getattr(self.precedent, attribut)
        except AttributeError:
            raise

    def __setattr__(self, attribut, valeur):
        try:
            object.__setattr__(self, attribut, valeur)
        except AttributeError:
            try:
                setattr(self.precedent, attribut, valeur)
            except AttributeError:
                raise

    @property
    def precedent(self):
        """Renvoie la référence à l'objet précédent"""
        return self._precedent

    @precedent.setter
    def precedent(self, precedent):
        """Enregistre la référence de l'objet suivant"""
        self._precedent = precedent
        if precedent:
            self.precedent.suivant = self


class Mot(ObjetLie, list):
    """Ensemble de syllabes

    Cet objet peut être défini à partir:

    - d'une liste d'objets Syllabe ;
    - d'une liste de tuples (syllabe, musique) en langage gabc.

    """
    def __init__(self, gabc=None, precedent=None, *args, **params):
        ObjetLie.__init__(self, precedent=precedent)
        list.__init__(self, *args, **params)
        if gabc:
            for syl in gabc:
                self.append(Syllabe(
                    gabc=syl,
                    mot=self,
                    precedent=(
                        self[-1] if len(self)
                        else self.precedent.dernieresyllabe if self.precedent
                        else None
                    )
                ))
            self.dernieresyllabe = self[-1]

    def __repr__(self):
        return str(self)

    def __str__(self):
        return ''.join(str(syllabe) for syllabe in self)

    @property
    def musique(self):
        """Liste des signes musicaux du mot"""
        return [syllabe.musique for syllabe in self]


class Syllabe(ObjetLie):
    """Ensemble de lettres, auquel est associé un neume

    Cet objet peut être défini à partir d'un tuple (syllabe, musique)
    en langage gabc.

    """
    def __init__(self, gabc, mot=None, precedent=None):
        ObjetLie.__init__(self, precedent=precedent)
        self.mot = mot
        self.texte = gabc[0]
        if len(mot):
            try:
                alterations = precedent.musique[-1].alterations
            except AttributeError:
                alterations = None
        else:
            alterations = None
        self.neume = Neume(
            gabc=gabc[1],
            syllabe=self,
            alterations=alterations
        )
        # Lilypond ne peut pas associer une syllabe à un "neume" sans note.
        # Il est donc nécessaire de traiter à part le texte pour lui.
        if (
                self.precedent and self.precedent.ly_texte != ''
                and not self.precedent.neume.possede_note
        ):
            self.ly_texte = self.precedent.ly_texte + ' ' + self.texte
            self.precedent.ly_texte = ''
        else:
            self.ly_texte = self.texte
        try:
            while self.ly_texte[0] == ' ':
                self.ly_texte = self.ly_texte[1:]
        except IndexError:
            pass

    def __repr__(self):
        return str((self.texte, str(self.neume)))

    def __str__(self):
        return self.texte

    @property
    def ly(self):  # pylint:disable=C0103
        """Texte de la syllabe adapté pour lilypond"""
        ly_texte = self.ly_texte
        special = re.compile(re.escape('<v>') + '.*' + re.escape('</v>'))
        if special.search(ly_texte):
            ly_texte = special.sub('', ly_texte)
        if (
                not len(ly_texte)
                and not (
                    len(self.neume) == 1
                    and isinstance(self.neume[0], Clef)
                )
        ):
            ly_texte = ''
        ly_texte = ly_texte.replace(' ', '_')
        ly_texte = re.sub('([0-9]+\.?)', '\\set stanza = "\\1"', ly_texte)
        return ly_texte\
            .replace('*', '&zwj;*')\
            .replace('<i>', '').replace('</i>', '')\
            .replace('<b>', '').replace('</b>', '')\
            .replace('{', '').replace('}', '')\
            .replace('<sp>R/</sp>', '℟')\
            .replace('<sp>V/</sp>', '℣')\
            .replace('<sp>ae</sp>', 'æ')\
            .replace("<sp>'ae</sp>", 'ǽ')\
            .replace("<sp>'æ</sp>", 'ǽ')\
            .replace('<sp>AE</sp>', 'Æ')\
            .replace("<sp>'AE</sp>", 'Ǽ')\
            .replace("<sp>'Æ</sp>", 'Ǽ')\
            .replace('<sp>oe</sp>', 'œ')\
            .replace("<sp>'oe</sp>", 'œ́')\
            .replace("<sp>'œ</sp>", 'œ́')\
            .replace('<sp>OE</sp>', 'Œ')\
            .replace("<sp>'OE</sp>", 'Œ́')\
            .replace("<sp>'Œ</sp>", 'Œ́')

    @property
    def abc(self):
        """Texte de la syllabe adapté pour abc"""
        abc_texte = self.texte
        try:
            if abc_texte[0] == ' ':
                abc_texte = abc_texte[1:]
        except IndexError:
            pass
        special = re.compile(re.escape('<v>') + '.*' + re.escape('</v>'))
        if special.search(abc_texte):
            abc_texte = special.sub('', abc_texte)
        if (
                not len(abc_texte)
                and not (
                    len(self.neume) == 1
                    and isinstance(self.neume[0], Clef)
                )
        ):
            abc_texte = ''
        abc_texte = abc_texte.replace(' ', '~')
        return abc_texte\
            .replace('-', '')\
            .replace('*', '~✶').replace('~~', '~')\
            .replace('<i>', '').replace('</i>', '')\
            .replace('<b>', '').replace('</b>', '')\
            .replace('{', '').replace('}', '')\
            .replace('<sp>R/</sp>', '℟')\
            .replace('<sp>V/</sp>', '℣')\
            .replace('<sp>ae</sp>', 'æ')\
            .replace("<sp>'ae</sp>", 'ǽ')\
            .replace("<sp>'æ</sp>", 'ǽ')\
            .replace('<sp>AE</sp>', 'Æ')\
            .replace("<sp>'AE</sp>", 'Ǽ')\
            .replace("<sp>'Æ</sp>", 'Ǽ')\
            .replace('<sp>oe</sp>', 'œ')\
            .replace("<sp>'oe</sp>", 'œ́')\
            .replace("<sp>'œ</sp>", 'œ́')\
            .replace('<sp>OE</sp>', 'Œ')\
            .replace("<sp>'OE</sp>", 'Œ́')\
            .replace("<sp>'Œ</sp>", 'Œ́')

    @property
    def musique(self):
        """Liste des notes associées à la syllabe"""
        return self.neume


class Neume(list):
    """Ensemble de signes musicaux"""
    def __init__(
            self, gabc=None, syllabe=None, alterations=None, *args, **params
    ):
        list.__init__(self, *args, **params)
        self.syllabe = syllabe
        self.element_ferme = True
        self.possede_note = False
        self.alterations = alterations
        self.traiter_gabc(gabc)

    @property
    def gabc(self):
        """Code gabc du neume"""
        return(
            ''.join((signe.gabc for signe in self))
            if len(self)
            else ''
        )

    @property
    def ly(self):  # pylint:disable=C0103
        """Expression lilypond du neume"""
        return ''.join(signe.ly for signe in self)

    @property
    def abc(self):
        """Expression lilypond du neume"""
        return ''.join(signe.abc for signe in self)

    def traiter_gabc(self, gabc):
        """Extraction des signes à partir du code gabc"""
        # Expression correspondant aux clés.
        cle = re.compile('[cf][b]?[1234]')
        # Ce dictionnaire renvoie l'objet correspondant à chaque signe.
        signes = {
            Note:           re.compile("[abcdefghijklmABCDEFGHIJKLM]"),
            SigneRythmique: re.compile("[_.'w~]"),
            NoteSpeciale:   re.compile("[osvOSV]"),
            Barre:          re.compile("[`,;:]"),
            Alteration:     re.compile("[xy#]"),
            Coupure:        re.compile("[/ ]"),
            Custo:          re.compile("\+"),
            Fin:            re.compile("z"),
            Cesure:         re.compile("!"),
        }
        if cle.search(gabc) and cle.fullmatch(gabc):
            # Traitement d'une clef toute simple (initiale)
            self.append(Clef(
                gabc=gabc,
                neume=self,
            ))
        elif cle.search(gabc):
            # Traitement des changements de clef
            clef = cle.findall(gabc)[0]
            autres = cle.split(gabc)
            for sgn in autres[0]:
                self.traiter_gabc(sgn)
            self.append(Clef(
                gabc=clef,
                neume=self,
            ))
            for sgn in autres[1]:
                self.traiter_gabc(sgn)
        else:
            for signe in gabc:
                for typesigne, regex in signes.items():
                    if regex.fullmatch(signe):
                        try:
                            alterations = self.alterations
                        except AttributeError:
                            alterations = None
                        self.append(typesigne(
                            gabc=signe,
                            neume=self,
                            precedent=self[-1] if len(self)
                            else None,
                            alterations=alterations
                        ))
        for signe in self:
            if isinstance(signe, Note):
                signe.ouvrir_neume()
                break
        for signe in reversed(self):
            if isinstance(signe, Note):
                signe.fermer_neume()
                break


class Signe(ObjetLie):
    """Signe musical

    Il peut s'agir d'une note, d'un épisème, d'une barre…

    """
    def __init__(
            self,
            gabc,
            neume=None,
            precedent=None,
            suivant=None,
            alterations=None
    ):
        ObjetLie.__init__(self, precedent=precedent)
        self.gabc = gabc
        self.neume = neume
        self.suivant = suivant
        if alterations:
            self.alterations = alterations
        self._ly = ''
        self._abc = ''

    @property
    def ly(self):  # pylint:disable=C0103
        """Code lilypond par défaut

        Cette méthode permet d'éviter qu'un signe n'ayant pas d'expression en
        ly renvoie l'expression de la note précédente.
        """
        return self._ly

    @ly.setter
    def ly(self, valeur):  # pylint:disable=C0103
        """'Setter' pour l'expression ly"""
        self._ly = valeur

    @property
    def abc(self):
        """Code abc par défaut

        Cette méthode permet d'éviter qu'un signe n'ayant pas d'expression en
        abc renvoie l'expression de la note précédente.
        """
        return self._abc

    @abc.setter
    def abc(self, valeur):
        """'Setter' pour l'expression abc"""
        self._abc = valeur

    def __repr__(self):
        return str(type(self).__name__) + ' : ' + self.gabc

    def __str__(self):
        return self.gabc


class Alteration(Signe):
    """Bémols et bécarres"""
    def __init__(self, gabc, **params):
        Signe.__init__(self, gabc, **params)
        self.gabc = self.precedent.gabc + gabc
        if self.precedent.premier_element:
            self.neume.element_ferme = True
        self.precedent = self.precedent.precedent
        self.neume.pop()

    @property
    def alterations(self):
        """Liste des altérations

        Sous forme d'un dictionnaire, où les notes marquées d'un bémol sont
        associées à la valeur -1, marquées d'un dièze à 1, les autres à 0.
        """
        try:
            alterations = self.precedent.alterations
        except AttributeError:
            alterations = {
                chr(lettre): 0 for lettre in range(ord('a'), ord('p') + 1)
            }
        alterations[self.gabc[0]] = {'x': -1, 'y': 0, '#': 1}[self.gabc[1]]
        return alterations


class Barre(Signe):
    """Barres délimitant les incises"""
    def __init__(self, gabc, **params):
        Signe.__init__(self, gabc, **params)
        if isinstance(self.precedent, Barre):
            if self.precedent.gabc == ':' and self.gabc == ':':
                self.gabc = self.precedent.gabc + gabc
                self.precedent = self.precedent.precedent
                self.neume.pop()
            else:
                raise ErreurSyntaxe('Double barre bizarre')
        try:
            self.precedent.duree_egaliser()
        except AttributeError:
            pass
        try:
            self.precedent.fermer_element()
        except AttributeError:
            pass
        self.poser_note_precedente()

    def poser(self, pose):
        """Ignorer le posé venant de la barre suivante"""
        pass

    def poser_note_precedente(self):
        """Augmente la durée de la note précédente"""
        pose = {
            "`": 0,
            ",": 0,
            ";": 0.5,
            ":": 1,
            "::": 1.2,
        }[self.gabc]
        try:
            self.precedent.poser(pose)
        except AttributeError:
            self.neume.syllabe.mot.precedent[-1].neume[-1].poser(pose)

    @property
    def ly(self):
        """Correspondance entre les barres gabc et les barres lilypond"""
        return ''' \\bar "{}"'''.format({
            '': "",
            ',': "'",
            ';': "'",
            ':': "|",
            '::': "||"
        }[self.gabc])

    @property
    def abc(self):
        """Correspondance entre les barres gabc et les barres abc"""
        return {
            '': "",
            ',': "!shortphrase![|]",
            ';': "!mediumphrase![|]",
            ':': "|",
            '::': "||"
        }[self.gabc]


class Clef(Signe):
    """Clefs"""
    def __init__(self, gabc, **params):
        Signe.__init__(self, gabc, **params)
        self.neume.syllabe.mot.cle = self


class Fin(Signe):
    """Le z de gabc

    Il signifie ou bien une fin de ligne forcée, ou bien un guidon automatique
    en fin de ligne.
    """
    def __init__(self, gabc, **params):
        Signe.__init__(self, gabc, **params)


class Custo(Signe):
    """Guidon en fin de ligne ou avant un changement de clef

    Il indique quelle est la note suivante.
    """
    def __init__(self, gabc, **params):
        Signe.__init__(self, gabc, **params)
        self.precedent = self.precedent.precedent
        self.neume.pop()


class Coupure(Signe):
    """Coupures neumatiques"""
    def __init__(self, gabc, **params):
        Signe.__init__(self, gabc, **params)
        try:
            self.precedent.duree_egaliser()
        except AttributeError:
            pass
        try:
            self.precedent.fermer_element()
        except AttributeError:
            pass

    def __repr__(self):
        if self.gabc == ' ':
            return '\\ '
        else:
            return Signe.__repr__(self)


class Cesure(Signe):
    """Césures neumatiques (symbole !)"""
    pass


class SigneRythmique(Signe):
    """Épisèmes, points"""
    def __init__(self, gabc, **params):
        Signe.__init__(self, gabc, **params)
        try:
            self.precedent.appliquer({
                "'": 'ictus',
                '_': 'episeme',
                '.': 'point',
                'w': 'quilisma',
                '~': 'liquescence',
            }[self.gabc])
        except AttributeError:
            print("Bizarrerie : signe rythmique sans note.")


class Note(Signe):
    """Note de musique"""
    def __init__(self, gabc, **params):
        Signe.__init__(
            self,
            gabc=gabc,
            **params
        )
        self.hauteur = self.g2mid()
        # Par défaut, la durée est à 1 : elle pourra être modifiée par
        # la suite, s'il se rencontre un épisème, un point, etc.
        self.duree = 1
        self._ly = self.g2ly()
        self._abc = self.g2abc()
        self._nuances = []
        self.neume.possede_note = True
        if self.neume.element_ferme:
            self.ouvrir_element()
            self.premier_element = True
        else:
            self.premier_element = False

    def duree_egaliser(self):
        """Rend la durée de la note au moins égale à celle de la précédente"""
        try:
            if self.duree < self.precedent.duree:
                self.duree = self.precedent.duree
        except AttributeError:
            pass

    def appliquer(self, nuance):
        """Prise en compte des divers signes rythmiques"""
        if nuance not in self._nuances:
            self._nuances.append(nuance)
            if nuance == 'episeme':
                self.retenir(DUREE_EPISEME)
            elif nuance == 'point':
                self.retenir(DUREE_POINT)
                self.fermer_element()
                try:
                    self.precedent.fermer_element()
                except AttributeError:
                    pass
            elif nuance == 'quilisma':
                self.precedent.retenir(DUREE_AVANT_QUILISMA)
        else:
            if nuance in ('quilisma', 'liquescence'):
                raise ErreurSyntaxe('Deux {}s consécutifs.'.format(nuance))
            else:
                self.precedent.appliquer(nuance)

    def poser(self, pose):
        """Appliquer le posé réclamé par la barre suivante"""
        self.duree += pose

    def retenir(self, duree):
        """Définir la durée à cette valeur si elle n'est pas déjà supérieure"""
        if self.duree < duree:
            self.duree = duree

    @property
    def ly(self):
        # pylint:disable=C0103
        ly = ' ' + self._ly
        if 'point' in self._nuances:
            ly = ly.replace('8', '4')
        if 'episeme' in self._nuances:
            ly += '--'
        if 'ictus' in self._nuances:
            ly += '-!'
        if 'quilisma' in self._nuances:
            ly += '\prall'
        if 'liquescence' in self._nuances:
            ly = ' \\tiny{} \\normalsize'.format(ly)
        return ly

    @property
    def abc(self):
        abc = self._abc
        if 'point' in self._nuances:
            while abc[-1] == ' ':
                abc = abc[:-1]
            abc = abc + '2'
        if 'episeme' in self._nuances:
            abc = '!tenuto!' + abc
        if 'ictus' in self._nuances:
            abc = '!wedge!' + abc
        if 'quilisma' in self._nuances:
            abc = 'P' + abc
        if 'liquescence' in self._nuances:
            pass
        return abc

    def ouvrir_element(self):
        """Indique à la note qu'elle ouvre un élément neumatique

        Ceci est surtout nécessaire pour lilypond
        """
        self.neume.element_ferme = False
        self._ly += '['

    def fermer_element(self):
        """Indique à la note qu'elle clôt un élément neumatique

        Ceci est surtout nécessaire pour lilypond
        """
        self._abc += ' '
        if 'point' in self._nuances:
            self._ly = self._ly.replace('[', '')
        else:
            self._ly = (self._ly + ']').replace('[]', '')
        self.neume.element_ferme = True

    def ouvrir_neume(self):
        """Indique à la note qu'elle ouvre un neume

        Ceci est surtout nécessaire pour lilypond
        """
        self._ly += '('

    def fermer_neume(self):
        """Indique à la note qu'elle clôt un neume

        Ceci est surtout nécessaire pour lilypond
        """
        self.duree_egaliser()
        self._ly = (self._ly + ')').replace('()', '')
        self.fermer_element()

    @property
    def note(self):
        """Renvoi du nom "canonique" de la note"""
        octve = int(self.hauteur / 12) - 2
        nte = int(self.hauteur % 12)
        return ('Do',
                'Do#',
                'Ré',
                'Mib',
                'Mi',
                'Fa',
                'Fa#',
                'Sol',
                'Sol#',
                'La',
                'Sib',
                'Si')[nte] + str(octve)

    def g2ly(self):
        """Renvoi du code lilypond correspondant à la note"""
        octve = int(self.hauteur / 12) - 1
        nte = int(self.hauteur % 12)
        # Nom de la note
        note = ('c',
                'cis',
                'd',
                'ees',
                'e',
                'f',
                'fis',
                'g',
                'gis',
                'a',
                'bes',
                'b')[nte]
        # Hauteur de la note :
        # on prévoit de la1 à sol7, ce qui est plutôt large !
        note += (", , ",
                 ", ",
                 "",
                 "'",
                 "''",
                 "'''",
                 "''''")[octve-1]
        # Durée de la note : croche par défaut, pourra être précisée
        # par la suite.
        note += '8'
        return note

    def g2abc(self):
        """Renvoi du code abc correspondant à la note"""
        # Nom de la note
        return (
            'A,', '_B' 'B,',
            'C', '_D', 'D', '_E', 'E', 'F', '_G', 'G', '_A', 'A', '_B', 'B',
            'c', '_d', 'd', '_e', 'e', 'f', '_g', 'g', '_a', 'a', '_b', 'b',
            "c'", "_d'", "d'", "_e'", "e'", "f'", "_g'", "g'", "_a'", "a'"
        )[self.hauteur - 58]

    def g2mid(self, gabc=None):
        """Renvoi de la note correspondant à une lettre gabc"""
        if not gabc:
            gabc = self.gabc
        # Définition de la gamme.
        h_la = H_LA
        gamme = {
            'notes': ('la', 'si', 'do', 're', 'mi', 'fa', 'sol'),
            'hauteurs': (
                h_la,
                h_la + 2,
                h_la + 3,
                h_la + 5,
                h_la + 7,
                h_la + 8,
                h_la + 10
            ),
        }
        gabcnotes = "abcdefghijklm"
        # Analyse de la clé : les lettres du gabc définissant une
        # position sur la portée et non une hauteur de note, la note
        # correspondant à une lettre dépend de la clé.
        # N.B : c1, f1 et f2 n'existent pas normalement, mais cela ne
        # nous regarde pas !
        cle = self.neume.syllabe.mot.cle.gabc
        alterations = {
            chr(lettre): 0 for lettre in range(ord('a'), ord('p') + 1)
        }
        try:
            alterations = self.alterations if self.alterations else alterations
        except AttributeError:
            pass
        # Traitement des bémols à la clé.
        if len(cle) == 3:
            cle = cle[0] + cle[2]
            alterations[{
                "c4": 'bi',
                "c3": 'g',
                "c2": 'el',
                "c1": 'cj',
                "f4": 'fm',
                "f3": 'dk',
                "f2": 'bi',
                "f1": 'g'
            }[cle]] = -1
        decalage = {
            "c4": 0,
            "c3": 2,
            "c2": 4,
            "c1": 6,
            "f4": 3,
            "f3": 5,
            "f2": 0,
            "f1": 2
        }
        i = decalage[cle] - 1
        octve = -12 if cle == 'f3' else 0
        hauteurs = {}
        notes = {}
        for j in gabcnotes:
            i += 1
            if i == 7:
                i %= 7
                octve += 12
            notes[j] = gamme['notes'][i]
            hauteurs[j] = gamme['hauteurs'][i] + octve
        lettre = gabc.lower()[0]
        hauteur = hauteurs[lettre]
        hauteur += alterations[lettre]
        # Si la note est altérée par un bémol, l'abaisser d'un demi-ton.
        # N.B : le grégorien n'admet que le si bémol, mais il n'y avait
        # pas de raison de se limiter à ce dernier. Cependant, on
        # renvoie un avertissement si un autre bémol est rencontré, car
        # il peut s'agir d'une erreur.
        if alterations[lettre] == -1 and notes[lettre] != 'si':
            sys.stderr.write(notes[lettre] + ' bémol rencontré')
        return hauteur


class NoteSpeciale(Note):
    """Notes répercutantes

    Virga, oriscus, stropha.

    """
    def __init__(self, gabc, precedent, **params):
        Note.__init__(self, gabc=precedent.gabc, precedent=precedent, **params)
        if isinstance(precedent, NoteSpeciale):
            self.gabc = gabc
        elif isinstance(precedent, Note):
            self.gabc = self.precedent.gabc + gabc
            if precedent.premier_element:
                self.ouvrir_element()
            self.precedent = precedent.precedent
            self.neume.pop()
        else:
            raise ErreurSyntaxe(gabc + ' sans note précédente')

    def retenir(self, duree):
        Note.retenir(self, duree)


# # Classes servant à l'export en différents formats.


class Lily:
    """Partition lilypond"""
    def __init__(self, partition, titre, tempo):
        self.transposition = (
            "c, ", "des, ", "d, ", "ees, ", "e, ", "f, ",
            "fis, ", "g, ", "aes, ", "a, ", "bes, ", "b, ",
            "c", "des", "d", "ees", "e", "f",
            "fis", "g", "aes", "a", "bes", "b", "c'"
            )[(partition.transposition + 12) % 24]
        self.tonalite = partition.tonalite[0]
        self.texte, self.musique = self.traiter_partition(partition)
        self.titre = titre
        self.tempo = tempo

    @classmethod
    def traiter_partition(cls, partition):
        """Extraction du texte et des paroles depuis l'objet partition"""
        texte = ''
        musique = ''
        i = 0
        for mot in partition:
            parole = ' -- '.join(syllabe.ly for syllabe in mot)
            notes = ''.join(neume.ly for neume in mot.musique)
            if len(parole) or len(notes):
                i += 1
                texte += (
                    '%{}'.format(i) +
                    ('\n' + parole if len(parole) else '')
                    + '\n'
                )
                musique += '%{}\n'.format(i) + notes + '\n'
        return texte, musique

    def ecrire(self, fichier):
        """Enregistrement du code lilypond dans un fichier"""
        fichier.ecrire(LILYPOND_ENTETE % {
            'titre': self.titre,
            'tonalite': self.tonalite,
            'musique': self.musique,
            'transposition': self.transposition,
            'paroles': self.texte
        })


class Abc:
    """Partition abc"""
    def __init__(self, partition, titre, tempo):
        self.tonalite = partition.tonalite[0]
        self.texte, self.musique = self.traiter_partition(partition)
        self.titre = titre
        self.tempo = int(tempo/2)
        self.texte, self.musique = self.traiter_partition(partition)
        self.code = ABC_ENTETE % {
            'titre': self.titre,
            'tonalite': self.tonalite,
            'musique': self.musique,
            'transposition': partition.transposition,
            'paroles': self.texte
        }

    @classmethod
    def traiter_partition(self, partition):
        """Création de la partition abc"""
        texte = ''
        musique = ''
        for m, mot in enumerate(partition):
            for i, syllabe in enumerate(mot):
                syl = syllabe.abc
                if i + 1 < len(mot):
                    syl = syl + '-'
                notes = tuple(notes for notes in syllabe.musique)
                for j, note in enumerate(notes):
                    musique += note.abc
                    if isinstance(note, Note) or isinstance(note, Alteration):
                        if j == 0:
                            texte += syl
                            if syl == '':
                                texte += '_'
                        elif not isinstance(notes[j - 1], Alteration):
                            texte += '_'
                    elif isinstance(note, Barre) and j == 0:
                        if texte[-2] == '_' and syl != '':
                            texte = texte[:-2] + syl
                        else:
                            texte = texte[:-1] + syl
            texte += ' '
            musique += ' '
        return texte, musique[:-3] + '|]'

    def ecrire(self, fichier, abc=True, xml=False):
        """Écriture effective du fichier abc"""
        if abc:
            fichier.ecrire(self.code)
        if xml:
            dossier, fichier = os.path.split(fichier.chemin)
            fichier = '' if fichier == '-' else fichier
            if fichier and not dossier:
                dossier = '.'
            abc2xml.convert(
                dossier, fichier[:-4], self.code, False, False, False
            )


class MusicXML(Abc):
    """Classe encapsulant la classe Abc pour produire du MusicXML"""
    def __init__(self, partition, titre, tempo):
        Abc.__init__(self, partition, titre, tempo)

    def ecrire(self, fichier):
        Abc.ecrire(self, fichier, abc=False, xml=True)


class Midi:
    """Musique midi"""
    def __init__(self, partition, titre, tempo):
        # Définition des paramètres MIDI.
        piste = 0
        temps = 0
        self.tempo = int(tempo/2)
        self.sortiemidi = MIDIFile(1, file_format=1)
        # Nom de la piste.
        self.sortiemidi.addTrackName(piste, temps, sansaccents(titre))
        # Tempo.
        self.sortiemidi.addTempo(piste, temps, self.tempo)
        # Instrument (74 : flûte).
        self.sortiemidi.addProgramChange(piste, 0, temps, 74)
        self.traiter_partition(partition, piste, temps)

    def traiter_partition(self, partition, piste, temps):
        """Création des évènements MIDI"""
        transposition = partition.transposition
        channel = 0
        volume = 127
        for mot in partition:
            for i, syllabe in enumerate(mot):
                syl = str(syllabe)
                if i + 1 < len(mot):
                    syl = syl + '-'
                for j, note in enumerate(
                        notes for notes in syllabe.musique
                        if isinstance(notes, Note)
                ):
                    pitch = note.hauteur + transposition
                    duree = int(note.duree)
                    self.sortiemidi.addTempo(
                        piste, temps, (self.tempo * duree / note.duree)
                    )
                    self.sortiemidi.addNote(
                        piste,
                        channel,
                        pitch,
                        temps,
                        duree / 2,
                        volume
                    )
                    if j == 0:
                        self.sortiemidi.addText(
                            piste,
                            temps,
                            syl
                        )
                    temps += duree / 2

    def ecrire(self, chemin):
        """Écriture effective du fichier MIDI"""
        with (
            open(sys.stdout.fileno(), 'wb')
            if chemin == '-'
            else open(chemin, 'wb')
        ) as sortie:
            self.sortiemidi.writeFile(sortie)


# # Classe générique pour faciliter l'écriture de fichiers.


class FichierTexte():
    """Gestion des fichiers texte"""
    def __init__(self, chemin, nom=None, ext=None):
        if os.path.isdir(chemin):
            chemin = os.path.join(chemin, nom + ext)
        self.dossier = os.path.dirname(chemin)
        self.nom = os.path.splitext(os.path.basename(chemin))[0]
        self.chemin = chemin

    @property
    def contenu(self):
        """Lecture du contenu"""
        if self.chemin == '-':
            texte = sys.stdin.read(-1)
        else:
            with open(self.chemin, 'r', encoding='utf-8') as fichier:
                texte = fichier.read(-1)
        return texte

    def ecrire(self, contenu):
        """Écriture dans le fichier"""
        if self.chemin == '-':
            sys.stdout.write(contenu)
        else:
            with open(self.chemin, 'w', encoding='utf-8') as fichier:
                fichier.write(contenu)


class ErreurSyntaxe(Exception):
    """Exception levée en cas d'erreur de syntaxe"""
    pass


if __name__ == '__main__':
    traiter_options(sys.argv[1:])
