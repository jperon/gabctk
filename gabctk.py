#! /usr/bin/python3
# -*- coding: UTF-8 -*-


# Variables globales ###################################################

TITRE = "Cantus"
DUREE_EPISEME = 1.7
DUREE_AVANT_QUILISMA = 2
DUREE_POINT = 2.3
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
        \\override Score.Slur #'stencil = ##f
        \\cadenzaOn \\transpose c %(transposition)s \\MusiqueTheme
        \\revert Score.Slur #'stencil
      }
    >>
    \\new Lyrics \\lyricsto theme {
      \\Paroles
    }
  >>
  \layout{}
  \midi{}
}'''


# Librairies externes ##################################################

import os
import sys
import getopt
import re
from midiutil.MidiFile3 import MIDIFile
import unicodedata as ud
try:
    import jrnl as l
except ImportError:
    pass


# Méthodes globales ####################################################


def aide(commande, erreur, code):
    """Affichage de l'aide"""
    # Tenir compte du message propre à chaque erreur, ainsi que du nom
    # sous lequel la commande a été appelée.
    print(
        'Erreur : '
        + erreur + '\n'
        + 'Usage : \n    '
        + commande + ' '
        + '-i <input.gabc> '
        + '[-o <output.mid>] '
        + '[-l <output.ly>] '
        + '[-e <texte.txt>] '
        + '[-t <tempo>] '
        + '[-d <transposition>] '
        + '[-n <titre>]'
        + '[-a <alertes>] '
        + '[-v]'''
        )
    # Renvoyer le code correspondant à l'erreur,
    # pour interagir avec d'autres programmes.
    sys.exit(code)


def gabctk(commande, arguments):
    """Fonction maîtresse"""
    # Initialisation des variables correspondant aux paramètres.
    debug = False
    tempo = 165
    entree = sortieMidi = sortieLily = transposition = paroles = ''
    alertes = corrections = []
    # Analyse des arguments de la ligne de commande.
    try:
        opts, args = getopt.getopt(
            arguments,
            "hi:o:l:e:b:t:d:n:a:v",
            [
                "help",             # Aide
                "entree=",          # Fichier gabc
                "midi=",            # Fichier MIDI
                "lily=",            # Fichier ly
                "export=",          # Fichier texte
                "tab=",             # Fichier "tablature" pour accompagnement
                "tempo=",           # Tempo de la musique
                "transposition=",   # Transposition
                "titre=",           # Titre de la pièce
                "alerter=",         # Caractères à signaler
                "verbose"           # Verbosité de la sortie
            ]
        )
    except getopt.GetoptError:
        aide(commande, 'Argument invalide', 1)
    for opt, arg in opts:
        if opt == '-h':
            aide(commande, 0)
        elif opt in ("-i", "--entree"):
            entree = FichierTexte(arg)
        elif opt in ("-o", "--midi"):
            sortieMidi = Fichier(arg)
        elif opt in ("-l", "--lily"):
            sortieLily = FichierTexte(arg)
        elif opt in ("-e", "--export"):
            texte = FichierTexte(arg)
        elif opt in ("-b", "--tab"):
            tab = FichierTexte(arg)
        elif opt in ("-t", "--tempo"):
            tempo = int(arg)
        elif opt in ("-d", "--transposition"):
            transposition = int(arg)
        elif opt in ("-n", "--titre"):
            global TITRE
            TITRE = arg
        elif opt in ("-a", "--alerter"):
            alertes.append(arg)
        elif opt in ("-v", "--verbose"):
            debug = True
    # Si les arguments n'ont pas été saisis explicitement,
    # considérer le premier comme étant le gabc en entrée ;
    # en l'absence de deuxième, donner à la sortie midi et à la sortie
    # lilypond le même nom, en changeant l'extension.
    try:
        if entree == '':
            entree = FichierTexte(arguments[0])
        if sortieMidi == '':
            try:
                if arguments[1][-4:] == '.mid':
                    sortieMidi = Fichier(arguments[1])
                elif arguments[1][-3:] == '.ly':
                    sortieLily = FichierTexte(arguments[1])
            except IndexError:
                sortieMidi = Fichier(re.sub('.gabc', '.mid', arguments[0]))
                sortieLily = FichierTexte(re.sub('.gabc', '.ly', arguments[0]))
    # S'il n'y a aucun argument, afficher l'aide.
    except IndexError:
        aide(commande, 'aucun argument', 0)
    # Extraire le contenu du gabc.
    try:
        gabc = Gabc(entree.contenu)
    # Si le gabc n'existe pas, afficher l'aide.
    except FileNotFoundError:
        aide(commande, 'fichier inexistant', 2)
    # Extraire la partition.
    partition = Partition(
        gabc=gabc.partition,
        transposition=transposition
        )
    # Créer les objets midi et lilypond.
    midi = Midi(partition, tempo)
    lily = Lily(partition, tempo)
    i = 0
    # Si l'utilisateur a demandé une sortie verbeuse, afficher :
    if debug:
        # − les en-têtes gabc ;
        print(gabc.entetes, '\n')
        # − la partition gabc (sans les en-têtes) ;
        print(gabc.contenu, '\n')
        # − la liste des couples (clé, signe gabc) ;
        print(gabc.partition, '\n')
        # − les paroles seules ;
        print(partition.texte, '\n')
        # −_les notes seules ;
        for neume in partition.musique:
            print(neume, '\n')
        print(lily.musique)
        # − les paroles en format lilypond ;
        print(lily.texte, '\n')
        # − la tessiture obtenue après transposition.
        print(
            Note(hauteur=partition.tessiture['minimum']).nom,
            " - ",
            Note(hauteur=partition.tessiture['maximum']).nom,
            " (",
            str(partition.transposition),
            ')',
            '\n'
            )
    # Créer le fichier midi.
    try:
        midi.ecrire(sortieMidi.chemin)
    except AttributeError:
        pass
    try:
        lily.ecrire(sortieLily.chemin)
    except AttributeError:
        pass
    # S'assurer de la présence de certains caractères,
    # à la demande de l'utilisateur.
    try:
        partition.verifier(alertes)
    except:
        pass
    # Création d'une variable contenant les paroles.
    paroles = partition.paroles
    # S'assurer des alertes définies par l'utilisateur.
    verifier(alertes, paroles)
    # Si l'utilisateur l'a demandé,
    # écrire les paroles dans un fichier texte.
    try:
        texte.ecrire(paroles + '\n')
    except UnboundLocalError:
        pass
    # Si l'utilisateur l'a demandé,
    # écrire une tablature dans un fichier texte.
    try:
        tablature = ''
        for mot in partition.texte:
            for syllabe in mot:
                tablature += (
                    '{}\t{}\n'.format(
                        syllabe,
                        ' '.join([note.ly for note in partition.musique[i]])
                        )
                    )
                i += 1
            tablature += '//\n'
        tab.ecrire(tablature + '\n')
    except UnboundLocalError:
        pass


def sansaccents(input_str):
    """Renvoie la chaîne d'entrée sans accents"""
    nkfd_form = ud.normalize('NFKD', input_str)
    return "".join([c for c in nkfd_form if not ud.combining(c)])


def verifier(alertes, texte):
    """Contrôle de la présence de certains caractères

    (à la demande de l'utilisateur)"""
    for alerte in alertes:
        if alerte in texte:
            print("!!! " + alerte + " !!!")


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
        resultat = self.code
        regex = re.compile('%%\n')
        resultat = regex.split(resultat)
        return resultat

    @property
    def entetes(self):
        """En-têtes du gabc, sous forme d'un dictionnaire"""
        resultat = {
            info[0]: ':'.join(info[1:]).replace(';', '').replace('\r', '')
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
        return resultat

    @property
    def contenu(self):
        """Partition gabc sans les en-têtes"""
        resultat = self.parties[1]
        resultat = re.sub('%.*\n', '', resultat)
        resultat = re.sub('\n', ' ', resultat)
        return resultat

    @property
    def partition(self):
        """Liste de couples (clé, signe gabc)"""
        resultat = []
        contenu = self.contenu
        # Recherche des clés.
        regex = re.compile('[cf][b]?[1234]')
        cles = regex.findall(contenu)
        # Découpage de la partition en fonction des changements de clé.
        partiestoutes = regex.split(contenu)
        parties = partiestoutes[0] + partiestoutes[1], partiestoutes[2:]
        # Définition des couples (clé, signe).
        for i, cle in enumerate(cles):
            try:
                for j, n in enumerate(parties[i]):
                    # Élimination des "déchets" initiaux.
                    if j < 2:
                        pass
                    elif j == 3 and n == ' ':
                        pass
                    # Enregistrement des informations utiles.
                    else:
                        resultat.append((cle, n))
            # Si, si, c'est arrivé…
            except IndexError:
                sys.stderr.write(
                    "Il semble que vous ayez des "
                    + "changements de clé sans notes subséquentes. "
                    + "Le résultat n'est pas garanti.\n"
                    )
        return resultat


class Partition:
    """Partition de musique.

    Cette classe a deux propriétés fondamentales, qui sont des listes :
    − musique, qui contient les notes ;
    − texte, qui contient les paroles."""
    def __init__(self, **parametres):
        # A priori, pas de bémol à la clé.
        self.b = ''
        # S'il y a un bémol à la clé, en tenir compte.
        if 'bemol' in parametres:
            self.b = self.b + parametres['bemol']
            parametres['tonalite'] = ['f', 'M']
        # Cas où l'instance de classe est initialisée avec le code gabc
        # (cas le plus courant).
        if 'gabc' in parametres:
            self.musique, self.texte = self.g2p(parametres['gabc'])
            # Si bémol à la clé, adapter la tonalité (mais le bémol
            # ainsi détecté sera traité dans la méthode g2p de la classe
            # Note.
            if len(parametres['gabc'][0][0]) == 3:
                parametres['tonalite'] = ['f', 'M']
        # Si l'instance de classe est initialisée avec l'ensemble des
        # notes (pour tessiture ou transposition).
        if 'partition' in parametres:
            self.musique = parametres['pitches']
        # Définition de la tonalité : a priori, ut majeur, mais la
        # transposition et la conversion en lilypond peuvent compliquer
        # les choses.
        if 'tonalite' in parametres:
            self.tonalite = parametres['tonalite']
        else:
            self.tonalite = ['c', 'M']
        # A priori, pas de transposition manuelle
        # (elle sera alors calculée automatiquement).
        self.transposition = None
        # Si transposition définie, en tenir compte.
        if 'transposition' in parametres:
            try:
                self.transposition = int(parametres['transposition'])
            except ValueError:
                pass
        # Effectuer la transposition si nécessaire.
        if self.transposition is None:
            self.transposer()

    def g2p(self, gabc):
        """Analyse du code gabc

        pour en sortir :
            − la mélodie (liste d'objets notes) ;
            − le texte (chaîne de caractères)."""
        # # Remarque : la traduction en musique a nécessité certains
        # # choix d'interprétation, qui n'engagent que l'auteur de ce
        # # script…
        # Pour plus de clarté, définition de variables correspondant
        # aux différentes familles de signes.
        # Certains signes ne sont pas pris en compte pour le moment :
        # ils n'étaient pas nécessaires à la génération d'un fichier
        # MIDI.
        gabcnotes = "abcdefghijklm"
        episeme = '_'
        point = '.'
        ictus = "'"
        quilisma = 'w'
        liquescence = '~'
        speciaux = 'osvOSV'
        barres = '`, ;:'
        bemol = "x"
        becarre = "y"
        coupures = '/ '
        # Le '!' sert, en ce qui nous concerne, ou bien à rien, ou bien
        # à rendre une coupure insécable.
        cesures = '!'
        # Initialisation des variables.
        texte = []
        mot = []
        syllabe = ''
        melodie = []
        neume = []
        b = self.b
        cesure = False
        # La variable musique est un drapeau :
        # 0 indique que l'on est dans le texte ;
        # 1 indique que l'on est dans un neume, entre deux parenthèses ;
        #   NB : pour les besoins de l'informatique, on considère ici un
        #   neume comme l'ensemble des notes comprises entre deux
        #   parenthèses, et une syllabe comme le texte situé juste avant
        #   la parenthèse ouvrante. Il peut donc y avoir des syllabes
        #   vides.
        # 2 indique que l'on est dans une commande spéciale, entre
        #   crochets. Attention : ces commandes sont purement et
        #   simplement ignorées.
        musique = 0
        for i, signe in enumerate(gabc):
            # Traitement du texte.
            if musique == 0:
                # Si une parenthèse s'ouvre, un neume commence.
                if signe[1] == '(':
                    musique = 1
                # Traitement des espaces.
                elif signe[1] == ' ':
                    # Le premier espace indique un changement de mot.
                    # On ajoute le mot au texte, on réinitialise le mot.
                    # S'il y a plusieurs espaces, on les ignore.
                    if syllabe == '':
                        if mot != []:
                            texte.append(mot)
                        mot = []
                    # Les autres espaces appartiennent à la syllabe,
                    # mais on ignore les espaces répétitifs.
                    else:
                        syllabe = (syllabe + ' ').replace('  ', ' ')
                # Les accolades pour centrer les notes sont ignorées.
                elif signe[1] in ['{', '}']:
                    pass
                # Ce qui n'est pas espace est considéré comme lettre.
                else:
                    syllabe += signe[1]
            # Traitement de la musique.
            elif musique == 1:
                # Si une parenthèse se ferme, un neume se termine.
                if signe[1] == ')':
                    # Calcul des durées : la dernière note d'un
                    # neume n'est jamais plus courte que la pénultième.
                    try:
                        if neume[-1].duree < neume[-2].duree:
                            neume[-1].duree = neume[-2].duree
                    except IndexError:
                        pass
                    # L'exception suivante est levée si le dernier
                    # symbole est une barre ou une coupure. En ce cas,
                    # on s'assure (ce qui ne devrait jamais arriver
                    # en fin de neume) qu'elle n'était pas précédée
                    # de notes auxquelles appliquer le traitement
                    # précédent.
                    except AttributeError:
                        try:
                            i = -2
                            while not isinstance(neume[i], Note):
                                i -= 1
                            derniere = neume[i]
                            i -= 1
                            while not isinstance(neume[i], Note):
                                i -= 1
                            avantderniere = neume[i]
                            if derniere.duree < avantderniere.duree:
                                derniere.duree = avantderniere.duree
                        except IndexError:
                            pass
                    # Ajout du neume à la mélodie, de la syllabe au mot,
                    # réinitialisation de la syllabe et du neume.
                    mot.append(syllabe)
                    melodie.append(neume)
                    syllabe = ''
                    neume = []
                    musique = 0
                # Ignorer les commandes personnalisées. Attention : si
                # l'auteur du gabc a de "mauvaises pratiques" et abuse de
                # telles commandes, cela peut amener des incohérences.
                # Pour cette raison, on renvoie un avertissement.
                elif signe[1] == '[':
                    musique = 2
                    print("Commande personnalisée ignorée")
                # A priori, on s'attend à rencontrer une note.
                elif signe[1].lower() in gabcnotes:
                    signesspeciaux = 0
                    notesretenues = 0
                    neume.append(
                        Note(
                            gabc=signe,
                            gabchauteur=signe,
                            bemol=b
                            )
                        )
                # Strophas, oriscus, etc.
                elif signe[1] in speciaux:
                    signesspeciaux += 1
                    # Si le signe spécial est répété, répéter la note.
                    # On obtient ainsi une "répercussion" (très
                    # matérielle, convenons-en…).
                    if signesspeciaux > 1:
                        neume.append(
                            Note(
                                gabc=signe,
                                hauteur=neume[-1].gabc,
                                bemol=b
                                )
                            )
                # Durées et épisèmes.
                elif signe[1] in (
                        ictus, episeme, point, quilisma, liquescence
                ):
                    if signe[1] == ictus:
                        neume[-1].ly += '-!'
                    elif signe[1] == episeme:
                        while not isinstance(neume[notesretenues], Note):
                            notesretenues -= 1
                        if neume[notesretenues].duree == DUREE_EPISEME:
                            notesretenues -= 1
                        while not isinstance(neume[notesretenues], Note):
                            notesretenues -= 1
                        neume[notesretenues].duree = DUREE_EPISEME
                        neume[notesretenues].ly += '--'
                    elif signe[1] == point:
                        while not isinstance(neume[notesretenues], Note):
                            notesretenues -= 1
                        if neume[notesretenues].duree == DUREE_POINT:
                            notesretenues -= 1
                        while not isinstance(neume[notesretenues], Note):
                            notesretenues -= 1
                        neume[notesretenues].duree = DUREE_POINT
                        neume[notesretenues].ly = neume[notesretenues].ly\
                            .replace('8', '4')
                    elif signe[1] == quilisma:
                        neume[-2].duree = DUREE_AVANT_QUILISMA
                        if '--' not in neume[-2].ly:
                            neume[-2].ly += '--'
                        neume[-1].ly += '\prall'
                    elif signe[1] == liquescence:
                        neume[-1].ly = '\\tiny %s \\normalsize' % neume[-1].ly
                    neume.append(SigneRythmique(gabc=signe))
                # Altérations.
                elif signe[1] in (bemol, becarre):
                    if signe[1] == bemol:
                        b = b + neume[-1].gabc[1]
                        neume = neume[:-1]
                    elif signe[1] == becarre:
                        b = b.replace(neume[-1].gabc[1], '')
                        neume = neume[:-1]
                    neume.append(Alteration(gabc=signe))
                # Fin d'élément neumatique : faute de pouvoir déterminer
                # aussi précisément que dans les manuscrits la valeur
                # des coupures, s'assurer pour le moins que la dernière
                # note d'un élément n'est pas plus courte que la
                # pénultième.
                elif signe[1] in coupures:
                    try:
                        if neume[-1].duree < neume[-2].duree:
                            neume[-1].duree = neume[-2].duree
                    except IndexError:
                        pass
                    # Cas où le symbole précédent n'était pas une note.
                    except AttributeError:
                        try:
                            if neume[-2].duree < neume[-3].duree:
                                neume[-2].duree = neume[-3].duree
                        except AttributeError:
                            try:
                                if neume[-3].duree < neume[-4].duree:
                                    neume[-3].duree = neume[-4].duree
                            except AttributeError:
                                if neume[-4].duree < neume[-5].duree:
                                    neume[-4].duree = neume[-5].duree
                    # Traitement des coupures doubles (ou plus, mais
                    # cela ne devrait pas arriver).
                    try:
                        if neume[-1].gabc[1] == ''\
                                and type(neume[-2]) == Coupure:
                                    neume = neume[:-1]
                                    cesure = True
                        if type(neume[-1]) == Coupure:
                            neume[-1] = Coupure(
                                gabc=(
                                    signe[0],
                                    neume[-1].gabc[1] + signe[1]
                                    )
                                )
                        else:
                            neume.append(Coupure(gabc=signe))
                            if not cesure:
                                neume.append(Barre(gabc=(signe[0], '')))
                            else:
                                cesure = False
                    # Dans le cas exceptionnel où l'on a une parenthèse
                    # dans le texte, une exception est levée, que l'on
                    # ignore.
                    # TODO: Cela entraîne des aberrations dans la
                    # mélodie, non traitées pour l'instant vue la rareté
                    # du cas.
                    except IndexError:
                        pass
                elif signe[1] in cesures:
                    cesure = True
                # Une barre annule les altérations accidentelles,
                # et provoque un "posé", d'où léger rallongement de la
                # note précédente.
                elif signe[1] in barres:
                    if signe[1] == ';':
                        pose = .5
                    elif signe[1] == ':':
                        pose = 1
                    else:
                        pose = 0
                    try:
                        neume[-1].duree += pose
                    except IndexError:
                        i = -1
                        while not isinstance(melodie[-1][i], Note):
                            i -= 1
                        melodie[-1][i].duree += pose
                    # Si l'exception suivante est levée, c'est que l'on
                    # a affaire à une double barre.
                    except AttributeError:
                        neume = neume[:-1]
                        signe = (signe[0], '::')
                    b = '' + self.b
                    neume.append(Barre(gabc=signe))
            # Traitement par le vide des commandes personnalisées.
            elif musique == 2:
                if signe[1] == ']':
                    musique = 1
        return melodie, texte

    def transposer(self):
        """Transposition automatique de la partition.

        On transpose automatiquement sur une tessiture moyenne."""
        # Calcul de la hauteur idéale.
        self.transposition = 66 - int(sum(self.tessiture.values())/2)

    @property
    def paroles(self):
        """Paroles de la partition.

        Retour d'une chaîne de caractères contenant les paroles.
        """
        return ' '.join(
            ''.join(syllabe for syllabe in mot)
            for mot in self.texte if mot != ['']
        )

    @property
    def tessiture(self):
        """Notes extrêmes de la mélodie"""
        minimum = maximum = 0
        # Parcours de toutes les notes de la mélodie, pour déterminer
        # la plus haute et la plus basse.
        for neume in self.musique:
            for note in (notes
                         for notes in neume
                         if type(notes) == Note):
                if minimum == 0 or note.hauteur < minimum:
                    minimum = note.hauteur
                if note.hauteur > maximum:
                    maximum = note.hauteur
        # ## TODO: voir pourquoi la bidouille abjecte qui suit est  ####
        # ## nécessaire…                                            ####
        minimum += 1
        if self.transposition:
            minimum += self.transposition
            maximum += self.transposition
        return {'minimum': minimum, 'maximum': maximum}


class Element:
    """Élément d'une partition

    Il peut s'agir d'une note, d'un épisème, d'une barre…

    """
    def __init__(self, **parametres):
        if 'gabc' in parametres:
            self.gabc = parametres['gabc']

    def __repr__(self):
        return self.gabc[1]


class Alteration(Element):
    """Bémols et bécarres"""
    def __init__(self, **parametres):
        Element.__init__(self, **parametres)

    @property
    def ly(self):
        """Les altérations influent sur les notes suivantes"""
        return ''

    @property
    def nom(self):
        """Nom de l'altération"""
        return self.gabc[1]


class Barre(Element):
    """Barres délimitant les incises"""
    def __init__(self, **parametres):
        Element.__init__(self, **parametres)

    @property
    def ly(self):
        """Expression en lilypond"""
        # TODO: trouver une meilleure expression pour la demi-barre.
        return '''\\bar "%s"''' % self.nom

    @property
    def nom(self):
        """Correspondance entre les barres gabc et les barres lilypond"""
        return {
            '': "",
            ',': "'",
            ';': "'",
            ':': "|",
            '::': "||"
            }[self.gabc[1]]


class Coupure(Element):
    """Coupures neumatiques"""
    def __init__(self, **parametres):
        Element.__init__(self, **parametres)

    @property
    def ly(self):
        """Traitement (par le vide) des coupures en lilypond"""
        return ''

    @property
    def nom(self):
        """Nom de la coupure"""
        return self.gabc[1]


class SigneRythmique(Element):
    """Épisèmes, points"""
    def __init__(self, **parametres):
        Element.__init__(self, **parametres)

    @property
    def ly(self):
        """L'épisème ou le point influent déjà sur la note précédente"""
        return ''

    @property
    def nom(self):
        """Nom du signe"""
        return self.gabc[1]


class Note(Element):
    """Note de musique"""
    def __init__(self, **parametres):
        Element.__init__(self, **parametres)
        self.b = ''
        if 'bemol' in parametres:
            self.b = parametres['bemol']
        if 'hauteur' in parametres:
            self.hauteur = parametres['hauteur']
        if 'duree' in parametres:
            self.duree = parametres['duree']
        if 'gabchauteur' in parametres:
            self.hauteur, self.duree = self.g2mid(parametres['gabchauteur'])
        self.ly = self.g2ly()

    @property
    def nom(self):
        """Renvoi du nom "canonique" de la note"""
        o = int(self.hauteur / 12) - 2
        n = int(self.hauteur % 12)
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
                'Si')[n] + str(o)

    def g2ly(self):
        """Renvoi du code lilypond correspondant à la note"""
        o = int(self.hauteur / 12) - 1
        n = int(self.hauteur % 12)
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
                'b')[n]
        # Hauteur de la note :
        # on prévoit de la1 à sol7, ce qui est plutôt large !
        note += (", , ",
                 ", ",
                 "",
                 "'",
                 "''",
                 "'''",
                 "''''")[o-1]
        # Durée de la note : croche par défaut, pourra être précisée
        # par la suite.
        note += '8'
        return note

    def g2mid(self, gabc):
        """Renvoi de la note correspondant à une lettre gabc"""
        # Définition de la gamme.
        la = 57                 # Le nombre correspond au "pitch" MIDI.
        si = la + 2
        do = la + 3
        re = do + 2
        mi = re + 2
        fa = mi + 1
        sol = fa + 2
        gammehauteurs = (la, si, do, re, mi, fa, sol)
        gammenotes = ('la', 'si', 'do', 're', 'mi', 'fa', 'sol')
        gabcnotes = "abcdefghijklm"
        # Analyse de la clé : les lettres du gabc définissant une
        # position sur la portée et non une hauteur de note, la note
        # correspondant à une lettre dépend de la clé.
        # N.B : c1, f1 et f2 n'existent pas normalement, mais cela ne
        # nous regarde pas !
        cle = gabc[0]
        # Traitement des bémols à la clé.
        if len(cle) == 3:
            cle = cle[0] + cle[2]
            bemol = {
                "c4": 'bi',
                "c3": 'g',
                "c2": 'el',
                "c1": 'cj',
                "f4": 'fm',
                "f3": 'dk',
                "f2": 'bi',
                "f1": 'g'
                }
            if bemol[cle] not in self.b:
                self.b += bemol[cle]
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
        o = 0
        if cle == 'f3':
            o = -12
        hauteurs = {}
        notes = {}
        for j in gabcnotes:
            try:
                i += 1
                hauteurs[j] = gammehauteurs[i] + o
                notes[j] = gammenotes[i]
            except IndexError:
                i -= 7
                o += 12
                hauteurs[j] = gammehauteurs[i] + o
                notes[j] = gammenotes[i]
        # Par défaut, la durée est à 1 : elle pourra être modifiée par
        # la suite, s'il se rencontre un épisème, un point, etc.
        duree = 1
        lettre = gabc[1].lower()
        hauteur = hauteurs[lettre]
        # Si la note est altérée par un bémol, l'abaisser d'un demi-ton.
        # N.B : le grégorien n'admet que le si bémol, mais il n'y avait
        # pas de raison de se limiter à ce dernier. Cependant, on
        # renvoie un avertissement si un autre bémol est rencontré, car
        # il peut s'agir d'une erreur.
        if lettre in self.b:
            if notes[lettre] != 'si':
                print(notes[lettre] + ' bémol rencontré')
            hauteur -= 1
        return hauteur, duree


# # Classes servant à l'export en différents formats.


class Lily:
    """Partition lilypond"""
    def __init__(self, partition, tempo):
        self.transposition = (
            "c, ", "des, ", "d, ", "ees, ", "e, ", "f, ",
            "fis, ", "g, ", "aes, ", "a, ", "bes, ", "b, ",
            "c", "des", "d", "ees", "e", "f",
            "fis", "g", "aes", "a", "bes", "b", "c"
            )[(partition.transposition + 12) % 24]
        self.musique = self.notes(partition.musique)
        self.tonalite = partition.tonalite[0]
        self.texte = self.paroles(partition.texte, partition.musique)

    def notes(self, musique):
        """Renvoi de la mélodie lilypond à partir des notes de la partition"""
        # Initialisation des variables.
        notes = ''
        prochainenote = ''
        # Drapeaux permettant de savoir où l'on en est :
        #   − ligatureouverte indique si l'élément neumatique est
        #     commencé ;
        #   − neumeouvert indique si le neume est commencé, ce qui se
        #     traduit dans le code lilypond par une liaison (qui permet
        #     d'associer l'ensemble des notes qu'elle couvre à la
        #     syllabe concernée) ; cette liaison est rendue invisible
        #     du fait des paramètres du préambule lilypond ;
        #   − noire indique si la note est une noire (auquel cas elle
        #     ne peut s'insérer dans une ligature).
        ligatureouverte = False
        neumeouvert = False
        noire = False
        for neume in musique:
            for i, note in enumerate(neume):
                # Traitement des notes.
                if type(note) == Note:
                    # La noire va un peu nous compliquer la vie.
                    noire = ('4' in note.ly)
                    # On ferme la ligature avant la noire.
                    if ligatureouverte and noire:
                        notes += '] '
                        ligatureouverte = False
                    # On ajoute la note à la partition.
                    notes += ' ' + note.ly
                    # Si la note est la première d'un neume qui en
                    # contient plusieurs, il faut ouvrir le neume.
                    if i == 0:
                        try:
                            if neume[i+1]:
                                notes += '('
                                neumeouvert = True
                                # La première note, si elle n'est pas
                                # une noire, ouvre aussi une ligature.
                                if not noire:
                                    notes += '['
                                    ligatureouverte = True
                        # Cette exception sera levée si le neume ne
                        # comporte qu'une seule note, ce qui évite des
                        # ligatures et liaisons inutiles.
                        except IndexError:
                            pass
                    # Si une noire ou une barre nous a forcés à fermer
                    # la ligature, il faut la rouvrir ensuite.
                    elif not ligatureouverte and not noire:
                        notes += '['
                        ligatureouverte = True
                # Traitement des coupures.
                elif type(note) == Coupure:
                    notes += '] '
                    ligatureouverte = False
                # Traitement des barres.
                elif type(note) == Barre:
                    # On ferme la ligature avant la barre.
                    if ligatureouverte:
                        notes += ']'
                        ligatureouverte = False
                    # Si la barre est le dernier élément du neume, il
                    # faut achever ce dernier avant d'écrire la barre.
                    if neumeouvert and i == len(neume)-1:
                        notes += ')'
                        neumeouvert = False
                    # On ajoute la barre à la partition.
                    notes += ' ' + note.ly + '\n'
            # Si le neume comporte plusieurs notes, on ferme si besoin
            # ligatures et liaisons.
            if i > 0:
                if neumeouvert:
                    notes += ')'
                    neumeouvert = False
                if ligatureouverte:
                    notes += ']'
                    ligatureouverte = False
        # On renvoie la partition ainsi obtenue, en mettant le cas
        # échéant les épisèmes horizontaux avant les verticaux.
        return notes\
            .replace('-!--', '---!')\
            .replace(' \\normalsize)', ') \\normalsize')\
            .replace(' \\normalsize]', '] \\normalsize')

    def paroles(self, texte, musique):
        """Renvoi des paroles lilypond à partir du texte de la partition"""
        # Initialisation des variables.
        paroles = ''
        paroleprecedente = ''
        # Cet indice va nous permettre de synchroniser les syllabes avec
        # les neumes.
        i = 0
        for mot in texte:
            # Former le mot lilypond à partir des syllabes.
            parole = ' -- '.join([syllabes.replace(' ', '_')
                                 for syllabes in mot])
            # S'il y a un mot précédent à traiter, c'est qu'il n'était
            # associé qu'à une barre (ou à un neume vide, ce qui ne
            # devrait pas arriver), ce qui est souvent le cas, par
            # exemple, des étoiles. En ce cas :
            #   − ou bien la barre est suivie de notes sans paroles
            #     associées, et on leur associe alors le mot précédent ;
            #   − ou bien elle est suivie d'un nouveau mot, et le mot
            #     précédent est alors rattaché à celui d'avant.
            if paroleprecedente != '':
                if parole != '':
                    paroles += '_' + paroleprecedente
                else:
                    parole = paroleprecedente
            # Si après tout cela le mot est toujours vide, c'est que le
            # neume est long et coupé par des barres : il faut alors
            # ajouter des syllabes fantômes aux paroles lilypond.
            if parole == '':
                parole = '_'
            # On regarde ici s'il y a ou non des notes associées
            # au mot ; s'il n'y en a pas, on le met en réserve pour le
            # traitement décrit ci-dessus.
            nnotes = 0
            for syllabe in mot:
                nnotes += len(
                    [
                        notes
                        for notes in musique[i]
                        if type(notes) == Note
                    ]
                )
                i += 1
            if nnotes != 0:
                paroles += ' ' + parole
                paroleprecedente = ''
            else:
                paroleprecedente = parole
        # Les balises <v></v> peuvent contenir tout… et n'importe quoi !
        # Cela ne plaît généralement pas à lilypond, donc on les ignore.
        paroles = re.sub('<v>.*?</v>', '', paroles)
        # On renvoie ici le résultat du traitement.
        # Lilypond n'aime pas les étoiles : on doit donc appliquer un
        # filtre.
        # TODO: voir comment traiter les gras et italiques en lilypond
        # au sein d'une syllabe.
        return paroles\
            .replace('*', '&zwj;*')\
            .replace('<i>', '').replace('</i>', '')\
            .replace('<b>', '').replace('</b>', '')\
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

    def ecrire(self, chemin):
        """Enregistrement du code lilypond dans un fichier"""
        sortie = FichierTexte(chemin)
        sortie.ecrire(LILYPOND_ENTETE % {
            'titre': TITRE,
            'tonalite': self.tonalite,
            'musique': self.musique,
            'transposition': self.transposition,
            'paroles': self.texte
            }
        )


class Midi:
    """Musique midi"""
    def __init__(self, partition, tempo):
        # Définition des paramètres MIDI.
        piste = 0
        temps = 0
        self.sortieMidi = MIDIFile(1)
        # Nom de la piste.
        self.sortieMidi.addTrackName(piste, temps, TITRE)
        # Tempo.
        self.sortieMidi.addTempo(piste, temps, tempo)
        # Instrument (74 : flûte).
        self.sortieMidi.addProgramChange(piste, 0, temps, 74)
        # À partir des propriétés de la note, création des évènements
        # MIDI.
        for neume in partition.musique:
            for note in (notes
                         for notes in neume
                         if type(notes) == Note):
                channel = 0
                pitch = note.hauteur + partition.transposition
                duree = note.duree
                volume = 127
                self.sortieMidi.addNote(piste,
                                        channel,
                                        pitch,
                                        temps,
                                        duree,
                                        volume)
                temps += duree

    def ecrire(self, chemin):
        """Écriture effective du fichier MIDI"""
        binfile = open(chemin, 'wb')
        self.sortieMidi.writeFile(binfile)
        binfile.close()


# # Classes génériques pour faciliter l'écriture de fichiers.


class Fichier:
    """Gestion des entrées/sorties fichier"""
    def __init__(self, chemin):
        self.dossier = os.path.dirname(chemin)
        self.nom = os.path.splitext(os.path.basename(chemin))[0]
        self.chemin = chemin


class FichierTexte:
    """Gestion des fichiers texte"""
    def __init__(self, chemin):
        if chemin == '-':
            self.chemin = '-'
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
            texte = sys.stdout.write(contenu)
        else:
            with open(self.chemin, 'w') as fichier:
                fichier.write(contenu)


if __name__ == '__main__':
    gabctk(sys.argv[0], sys.argv[1:])
