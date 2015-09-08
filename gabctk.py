#! /usr/bin/python3
# -*- coding: UTF-8 -*-

"""GabcTk

Ce programme vise à servir à toutes sortes de traitements sur les fichiers gabc
(cf. [Gregorio](https://gregorio-project.github.io)).

Actuellement, il permet de convertir les gabc en midi et en lilypond, et de
vérifier si certains caractères n'ont pas été saisis dans le texte de la
partition.

"""

# Variables globales ###################################################

TITRE = "Cantus"
TEMPO = 165
DUREE_EPISEME = 1.7
DUREE_AVANT_QUILISMA = 2
DUREE_POINT = 2.3
DEBUG = False
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


# Librairies externes ##################################################

import os
import sys
import getopt
import re
from midiutil.MidiFile3 import MIDIFile
import unicodedata as ud


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
    # Initialisation des variables correspondant aux paramètres.
    options = {'sortie': {}, 'alertes': []}
    # Analyse des arguments de la ligne de commande.
    try:
        opts = getopt.getopt(
            arguments,
            "hi:o:l:e:m:b:t:d:n:a:v",
            [
                "help",             # Aide
                "entree=",          # Fichier gabc
                "midi=",            # Fichier MIDI
                "lily=",            # Code ly
                "export=",          # Texte
                "musique=",         # Code gabc
                "tab=",             # Fichier "tablature" pour accompagnement
                "tempo=",           # Tempo de la musique
                "transposition=",   # Transposition
                "titre=",           # Titre de la pièce
                "alerter=",         # Caractères à signaler
                "verbose"           # Verbosité de la sortie
            ]
        )[0]
    except getopt.GetoptError as err:
        aide('Argument invalide : ' + err.args[1], 1)
    for opt, arg in opts:
        if opt == '-h':
            aide('', 0)
        elif opt in ("-i", "--entree"):
            options['entree'] = FichierTexte(arg)
        elif opt in ("-o", "--midi"):
            options['sortie']['midi'] = arg
        elif opt in ("-l", "--lily"):
            options['sortie']['lily'] = FichierTexte(arg)
        elif opt in ("-e", "--export"):
            options['sortie']['texte'] = FichierTexte(arg)
        elif opt in ("-m", "--musique"):
            options['sortie']['gabc'] = FichierTexte(arg)
        elif opt in ("-b", "--tab"):
            options['sortie']['tab'] = FichierTexte(arg)
        elif opt in ("-t", "--tempo"):
            options['tempo'] = int(arg)
        elif opt in ("-d", "--transposition"):
            options['transposition'] = int(arg)
        elif opt in ("-n", "--titre"):
            options['titre'] = arg
        elif opt in ("-a", "--alerter"):
            options['alertes'].append(arg)
        elif opt in ("-v", "--verbose"):
            options['debug'] = True
    # Si les arguments n'ont pas été saisis explicitement,
    # considérer le premier comme étant le gabc en entrée ;
    # en l'absence de deuxième, donner à la sortie midi
    # le même nom, en changeant l'extension.
    try:
        if 'entree' not in options:
            options['entree'] = FichierTexte(arguments[0])
        if 'midi' not in options['sortie']:
            try:
                if arguments[1][-4:] == '.mid':
                    options['sortie']['midi'] = arguments[1]
            except IndexError:
                options['sortie']['midi'] = \
                    re.sub('.gabc', '.mid', arguments[0])
    # S'il n'y a aucun argument, afficher l'aide.
    except IndexError:
        aide('aucun argument', 0)
    # Envoi de l'entrée vers la méthode de traitement
    gabctk(**options)


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
def gabctk(
        entree=None,
        sortie=None,
        alertes=None,
        tempo=TEMPO,
        titre=None,
        transposition=None,
        debug=DEBUG,
):
    """Export dans les différents formats"""
    # Extraire le contenu du gabc.
    try:
        gabc = Gabc(entree.contenu)
    # Si le gabc n'existe pas, afficher l'aide.
    except FileNotFoundError:
        aide('fichier inexistant', 2)
    # Extraire la partition.
    partition = gabc.partition(transposition=transposition)
    titre = \
        titre if titre \
        else gabc.entetes['name'] if 'name' in gabc.entetes \
        else TITRE
    sortie_verbeuse(debug, gabc, partition)
    # Créer le fichier midi.
    if 'midi' in sortie:
        midi = Midi(partition, titre=titre, tempo=tempo)
        midi.ecrire(sortie['midi'])
    # Créer le fichier lilypond
    if 'lily' in sortie:
        lily = Lily(partition, titre=titre, tempo=tempo)
        lily.ecrire(sortie['lily'].chemin)
    # S'assurer de la présence de certains caractères,
    # à la demande de l'utilisateur.
    # Création d'une variable contenant les paroles.
    paroles = partition.texte
    # S'assurer des alertes définies par l'utilisateur.
    verifier(alertes, paroles)
    # Si l'utilisateur l'a demandé,
    # écrire les paroles dans un fichier texte.
    if 'texte' in sortie:
        sortie['texte'].ecrire(paroles + '\n')
    if 'gabc' in sortie:
        sortie['gabc'].ecrire(partition.gabc)
    # Si l'utilisateur l'a demandé,
    # écrire une tablature dans un fichier texte.
    if 'tab' in sortie:
        tablature = re.sub(
            '^\s+', '',
            '\n'.join(
                '{0}\t{1}'.format(syllabe, neume.ly) for syllabe, neume in
                zip(partition.syllabes, partition.musique)
            ).replace('\n ', '\n//\n')
        )
        sortie['tab'].ecrire(tablature + '\n')


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
        if self._transposition:
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
        self.precedent.appliquer({
            "'": 'ictus',
            '_': 'episeme',
            '.': 'point',
            'w': 'quilisma',
            '~': 'liquescence',
        }[self.gabc])


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

    def g2mid(self, gabc=None):
        """Renvoi de la note correspondant à une lettre gabc"""
        if not gabc:
            gabc = self.gabc
        # Définition de la gamme.
        h_la = 57  # Le nombre correspond au "pitch" MIDI.
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
            chr(lettre):0 for lettre in range(ord('a'), ord('p') + 1)
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
            "fis", "g", "aes", "a", "bes", "b", "c"
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

    def ecrire(self, chemin):
        """Enregistrement du code lilypond dans un fichier"""
        sortie = FichierTexte(chemin)
        sortie.ecrire(LILYPOND_ENTETE % {
            'titre': self.titre,
            'tonalite': self.tonalite,
            'musique': self.musique,
            'transposition': self.transposition,
            'paroles': self.texte
        })


class Midi:
    """Musique midi"""
    def __init__(self, partition, titre, tempo):
        # Définition des paramètres MIDI.
        piste = 0
        temps = 0
        self.sortiemidi = MIDIFile(1)
        # Nom de la piste.
        self.sortiemidi.addTrackName(piste, temps, sansaccents(titre))
        # Tempo.
        self.sortiemidi.addTempo(piste, temps, tempo)
        # Instrument (74 : flûte).
        self.sortiemidi.addProgramChange(piste, 0, temps, 74)
        self.traiter_partition(partition, piste, temps)

    def traiter_partition(self, partition, piste, temps):
        """Création des évènements MIDI"""
        transposition = partition.transposition
        for neume in partition.musique:
            for note in (
                    notes for notes in neume if isinstance(notes, Note)
            ):
                channel = 0
                pitch = note.hauteur + transposition
                duree = note.duree
                volume = 127
                self.sortiemidi.addNote(
                    piste,
                    channel,
                    pitch,
                    temps,
                    duree,
                    volume
                )
                temps += duree

    def ecrire(self, chemin):
        """Écriture effective du fichier MIDI"""
        with (
            open(sys.stdout.fileno(), 'wb')
            if chemin == '-'
            else open(chemin, 'wb')
        )as sortie:
            self.sortiemidi.writeFile(sortie)


# # Classe générique pour faciliter l'écriture de fichiers.


class FichierTexte():
    """Gestion des fichiers texte"""
    def __init__(self, chemin):
        self.dossier = os.path.dirname(chemin)
        self.nom = os.path.splitext(os.path.basename(chemin))[0]
        self.chemin = chemin

    @property
    def contenu(self):
        """Lecture du contenu"""
        if self.chemin == '-':
            texte = sys.stdin.read(-1)
        else:
            with open(self.chemin, 'r') as fichier:
                texte = fichier.read(-1)
        return texte

    def ecrire(self, contenu):
        """Écriture dans le fichier"""
        if self.chemin == '-':
            sys.stdout.write(contenu)
        else:
            with open(self.chemin, 'w') as fichier:
                fichier.write(contenu)


class ErreurSyntaxe(Exception):
    """Exception levée en cas d'erreur de syntaxe"""
    pass


if __name__ == '__main__':
    traiter_options(sys.argv[1:])
