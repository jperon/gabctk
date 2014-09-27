#! /usr/bin/python3
# -*- coding: UTF-8 -*-

DUREE_EPISEME = 1.7
DUREE_AVANT_QUILISMA = 2
DUREE_POINT = 2.3
ENTETE_LILYPOND = (
'''\\version "2.16"

\header {
  tagline = ""
  composer = ""
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
)

import os,sys,getopt
import re
from midiutil.MidiFile3 import MIDIFile

def gabc2tk(commande,arguments):
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
                                "hi:o:l:e:t:d:a:v",
                                [
                                    "help",                             # Aide
                                    "entree=",                          # Fichier gabc
                                    "midi=",                            # Fichier MIDI
                                    "lily=",                            # Fichier ly
                                    "export=",                          # Fichier texte
                                    "tempo=",                           # Tempo de la musique
                                    "transposition=",                   # Transposition
                                    "alerter=",                         # Caractères à signaler s'ils se trouvent dans le gabc
                                    "verbose"                           # Verbosité de la sortie
                                ]
                                )
    except getopt.GetoptError:
        aide(commande,'Argument invalide',1)
    for opt, arg in opts:
        if opt == '-h':
            aide(commande,0)
        elif opt in ("-i", "--entree"):
            entree = FichierTexte(arg)
        elif opt in ("-o", "--midi"):
            sortieMidi = Fichier(arg)
        elif opt in ("-l", "--lily"):
            sortieLily = FichierTexte(arg)
        elif opt in ("-e", "--export"):
            texte = FichierTexte(arg)
        elif opt in ("-t", "--tempo"):
            tempo = int(arg)
        elif opt in ("-d", "--transposition"):
            transposition = int(arg)
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
                sortieMidi = Fichier(re.sub('.gabc','.mid',arguments[0]))
                sortieLily = FichierTexte(re.sub('.gabc','.ly',arguments[0]))
    # S'il n'y a aucun argument, afficher l'aide.
    except IndexError: aide(commande,'aucun argument',0)
    # Extraire le contenu du gabc.
    try: gabc = Gabc(entree.contenu)
    # Si le gabc n'existe pas, afficher l'aide.
    except FileNotFoundError:
        aide(commande,'fichier inexistant',2)
    # Extraire la partition.
    partition = Partition(
                        gabc = gabc.partition,
                        transposition = transposition
                        )
    # Afficher la tessiture obtenue après transposition.
    print(Note(hauteur = partition.tessiture['minimum']).nom
        + " - "
        + Note(hauteur = partition.tessiture['maximum']).nom)
    # Créer les objets midi et lilypond.
    midi = Midi(partition,tempo)
    lily = Lily(partition,tempo)
    # Si l'utilisateur a demandé une sortie verbeuse, afficher :
    if debug:
        ## la partition gabc (sans les en-têtes) ;
        print(gabc.contenu)
        print()
        ## la liste des couples (clé, signe gabc) ;
        print(gabc.partition)
        print()
        ## les paroles seules ;
        print(partition.texte)
        print()
        ## les notes seules.
        print([note.nom for note in partition.musique])
        print()
        ## les paroles en format lilypond
        print(lily.texte)
        print()
    # Créer le fichier midi.
    try:
        midi.ecrire(sortieMidi.chemin)
    except AttributeError: pass
    try:
        lily.ecrire(sortieLily.chemin)
    except AttributeError: pass
    # S'assurer de la présence de certains caractères,
    # à la demande de l'utilisateur.
    try: partition.verifier(alertes)
    except: pass
    # Si l'utilisateur l'a demandé,
    # écrire les paroles dans un fichier texte.
    for mot in partition.texte:
            paroles += ''.join(syllabe for syllabe in mot) + ' '
    try: texte.ecrire(paroles + '\n')
    except UnboundLocalError: pass

def aide(commande,erreur,code):
    """Affichage de l'aide"""
    # Tenir compte du message propre à chaque erreur, ainsi que du nom
    # sous lequel la commande a été appelée.
    print('Erreur : '
            + erreur + '\n'
            + 'Usage : \n    '
            + commande + ' '
            + '-i <input.gabc> '
            + '[-o <output.mid>] '
            + '[-e <texte.txt>] '
            + '[-t <tempo>] '
            + '[-d <transposition>] '
            + '[-a <alertes>] '
            + '[-v]''')
    # Renvoyer le code correspondant à l'erreur,
    # pour interagir avec d'autres programmes.
    sys.exit(code)

class Gabc:
    """Description du fichier gabc"""
    def __init__(self,code):
        self.code = code
    @property
    def contenu(self):
        '''Partition gabc sans les en-têtes'''
        resultat = self.code
        regex = re.compile('%%\n')
        resultat = regex.split(resultat)[1]
        resultat = re.sub('%.*\n','',resultat)
        resultat = re.sub('\n',' ',resultat)
        return resultat
    @property
    def partition(self):
        '''Liste de couples (clé, signe gabc)'''
        resultat = []
        contenu = self.contenu
        # Recherche des clés.
        regex = re.compile('[cf][b]?[1234]')
        cles = regex.findall(contenu)
        # Découpage de la partition en fonction des changements de clé.
        partiestoutes = regex.split(contenu)
        parties = partiestoutes[0] + partiestoutes[1], partiestoutes[2:]
        # Définition des couples (clé, signe).
        for i,cle in enumerate(cles):
            try:
                for n in parties[i]:
                    resultat.append((cle,n))
            # Si, si, c'est arrivé…
            except IndexError:
                sys.stderr.write("Il semble que vous ayez des "
                    + "changements de clé sans notes subséquentes. "
                    + "Le résultat n'est pas garanti.\n")
        return resultat

class Partition:
    """Partition de musique"""
    def __init__(self,**parametres):
        # A priori, pas de bémol à la clé.
        self.b = ''
        # S'il y a un bémol à la clé, en tenir compte.
        if 'bemol' in parametres:
            self.b = self.b + parametres['bemol']
            parametres['tonalite'] = ['f','M']
        # Cas où l'instance de classe est initialisée avec le code gabc
        # (cas le plus courant).
        if 'gabc' in parametres:
            self.musique,self.texte = self.g2p(parametres['gabc'])
            # Si bémol à la clé, adapter la tonalité (mais le bémol
            # ainsi détecté sera traité dans la méthode g2p de la classe
            # Note.
            if len(parametres['gabc'][0][0]) == 3:
                parametres['tonalite'] = ['f','M']
        # Si l'instance de classe est initialisée avec l'ensemble des
        # notes (pour tessiture ou transposition).
        if 'partition' in parametres:
            self.musique = parametres['pitches']
        # Définition de la tonalité : a priori, ut majeur, mais la
        # transposition et la conversion en lilypond peuvent compliquer
        # les choses.
        if 'tonalite' in parametres:
            self.tonalite = parametres['tonalite']
        else: self.tonalite = ['c','M']
        # A priori, pas de transposition manuelle
        # (elle sera alors calculée automatiquement).
        self.transposition = None
        # Si transposition définie, en tenir compte.
        if 'transposition' in parametres:
            try: self.transposition = int(parametres['transposition'])
            except ValueError: pass
        # Effectuer la transposition si nécessaire.
        if self.transposition == None:
            self.transposer()


    def g2p(self,gabc):
        """Analyser le code gabc pour en sortir :
            − la mélodie (liste d'objets notes) ;
            − le texte (chaîne de caractères)."""
        ## Remarque : la traduction en musique a nécessité certains
        ## choix d'interprétation, qui n'engagent que l'auteur de ce
        ## script…
        # Pour plus de clarté, définition de variables correspondant
        # aux différentes familles de signes.
        # Certains signes ne sont pas pris en compte pour le moment :
        # ils n'étaient pas nécessaires à la génération d'un fichier
        # MIDI.
        gabcnotes = "abcdefghijklm"
        episeme = '_'
        point = '.'
        quilisma = 'w'
        speciaux = 'osvOSV'
        barres = '`,;:'
        bemol = "x"
        becarre = "y"
        coupures = '/ '
        # Initialisation des variables.
        notes = []
        b = '' + self.b
        nmot = 0
        mot = []
        texte = []
        neume = 0
        neumeencours = ''
        premierenote = True
        neumeouvert = False
        # La variable musique est un drapeau :
        # 0 indique que l'on est dans le texte ;
        # 1 indique que l'on est dans un neume, entre deux parenthèses ;
        # 2 indique que l'on est dans une commande spéciale, entre
        #   crochets. Attention : ces commandes sont purement et
        #   simplement ignorées.
        musique = 0
        for i in range(len(gabc)):
            signe = gabc[i]
            # Traitement des notes de musique.
            if musique == 1:
                if signe[1].lower() in gabcnotes:
                    j = 0
                    s = 0
                    note = Note(gabc = signe, bemol = b)
                    notes.append(note)
                    # Si la note est la première d'un élément
                    # neumatique, commencer la ligature.
                    if premierenote:
                        notes[-1].ly += '['
                        premierenote = False
                    if not neumeouvert:
                        notes[-1].ly += '('
                        neumeouvert = True
                    # La variable memoire sert à garder le souvenir de
                    # la hauteur de note, afin de traiter certains cas
                    # particuliers (altérations, distrophas…).
                    memoire = signe
                # Strophas, oriscus, etc.
                elif signe[1] in speciaux:
                    s += 1
                    # Si le signe spécial est répété, répéter la note.
                    # On obtient ainsi une "répercussion" (très
                    # matérielle, convenons-en…).
                    if s > 1:
                        note = Note(gabc = memoire, bemol = b)
                        notes.append(note)
                # Durées.
                elif signe[1] == episeme:
                    neumeencours = neume
                    j -= 1
                    notes[j].duree = DUREE_EPISEME
                    notes[j].ly += '--'
                elif signe[1] == point:
                    j -= 1
                    notes[j].duree = DUREE_POINT
                    notes[j].ly = notes[j].ly.replace('8','4')
                    notes[j].ly = notes[j].ly.replace('[','')
                    notes[j].ly = notes[j].ly.replace(']','')
                    ccl = False
                    k = 0
                    while not ccl:
                        k += 1
                        try:
                            ccl = notes[j-k].ly_ccl(False)
                        except IndexError: pass
                    premierenote = True
                elif signe[1] == quilisma:
                    notes[-2].duree = DUREE_AVANT_QUILISMA
                    if '--' not in notes[-2].ly: notes[-2].ly += '--'
                    notes[-1].ly += '\prall'
                # Altérations.
                elif signe[1] == bemol:
                    b = b + memoire[1]
                    if '[' in notes[-1].ly: premierenote = True
                    if '(' in notes[-1].ly:
                        notes[-1].ly.replace('(','')
                        neumeouvert = False
                    notes = notes[:-1]
                elif signe[1] == becarre:
                    re.sub(memoire[1],'',b)
                    if '[' in notes[-1].ly: premierenote = True
                    if '(' in notes[-1].ly:
                        notes[-1].ly.replace('(','')
                        neumeouvert = False
                    notes = notes[:-1]
                # Fin d'élément neumatique : faute de pouvoir déterminer
                # aussi précisément que dans les manuscrits la valeur
                # des coupures, s'assurer pour le moins que la dernière
                # note d'un élément n'est pas plus courte que la
                # pénultième.
                elif signe[1] in coupures:
                    if notes[-1].duree < notes[-2].duree:
                        notes[-1].duree = notes[-2].duree
                    ### Discutable : faut-il couper le "neume" en
                    ### notation moderne (ce que ne fait pas
                    ### Solesmes) quand on rencontre une coupure
                    ### neumatique ?
                    notes[-1].ly_ccl(premierenote)
                    premierenote = True
                # Une barre annule les altérations accidentelles,
                # et provoque un "posé", d'où léger rallongement de la
                # note précédente.
                ### TODO: les barres en Lilypond seraient à revoir.
                elif signe[1] in barres:
                    b = '' + self.b
                    notes[-1].ly_ccl(premierenote)
                    premierenote = True
                    if signe[1] == ',':
                        notes[-1].ly += ''' \\bar"'"\n'''
                    if signe[1] == ';':
                        notes[-1].duree += .5
                        notes[-1].ly += ''' \\bar "'"\n'''
                    elif signe[1] == ':':
                        notes[-1].duree += 1
                        if ' \\bar "|"' in notes[-1].ly:
                            notes[-1].ly = notes[-1].ly.replace('|','||')
                        else: notes[-1].ly += ' \\bar "|"\n'
                    notes[-1].ly = notes[-1].ly.replace('\\bar ""\n \\bar',
                                                        '\\bar')
                else:
                    # Dans le calcul des durées : la dernière note d'un
                    # neume n'est jamais plus courte que la pénultième.
                    if neumeencours == neume \
                    and notes[-1].duree < notes[-2].duree:
                        notes[-1].duree = notes[-2].duree
                    if signe[1] == ')':
                        musique = 0
                        try:
                            ccl = False
                            k = 0
                            while not ccl:
                                k += 1
                                ccl = notes[-1].ly_ccl(premierenote)
                            premierenote = True
                            if neumeouvert:
                                notes[-1].ly += ')'
                            notes[-1].ly = notes[-1].ly.replace('()','')
                        except IndexError: pass
                        neumeouvert = False
            # Ignorer les commandes personnalisées. Attention : si
            # l'auteur du gabc a de "mauvaises pratiques" et abuse de
            # telles commandes, cela peut amener des incohérences.
            # Pour cette raison, on renvoie un avertissement.
                    if signe[1] == '[':
                        musique = 2
                        print("Commande personnalisée ignorée")
            # Traitement du texte.
            elif musique == 0:
                if signe[1] == '(':
                    musique = 1
                    neume += 1
                    mot.append('')
                    # La prochaine note est la première d'un élément
                    premierenote = True
                    # La prochaine lettre est la première d'une syllabe
                    premierelettre = True
                # Ignorer les accolades
                # (qui servent à centrer les notes sur une lettre).
                elif signe[1] in ('{', '}'): pass
                else:
                    # Le changement de mot en grégorien implique
                    # l'annulation des altérations accidentelles.
                    if signe[1] == ' ':
                        if premierelettre:
                            nmot += 1
                            b = '' + self.b
                            texte.append([syllabe
                                        for syllabe in mot
                                        if syllabe != ''])
                            mot = ['']
                            try:
                                if '\\bar' not in notes[-1].ly:
                                    notes[-1].ly += ' \\bar ""\n'
                            except IndexError: pass
                            premierelettre = False
                        else:
                            if len(mot[-1]) > 0: mot[-1] += signe[1]
                    else:
                        mot[-1] += signe[1]
            # "Traitement" (par le vide !) des commandes spéciales.
            elif musique == 2:
                if signe[1] == ']':
                    musique = 1
        # La dernière double-barre est une double-barre conclusive.
        notes[-1].ly = notes[-1].ly.replace('||','|.')
        return notes, [mot for mot in texte if mot != []]
    def transposer(self):
        """Transposition de la partition automatiquement
        sur une tessiture moyenne."""
        # Calcul si nécessaire de la hauteur idéale.
        self.transposition = 66 - int(sum(self.tessiture.values())/2)
        ## Transposition effective. MAJ : on laisse cela aux
        ## différentes classes traitant chaque sortie.
        #for i in range(len(self.musique)):
        #    self.musique[i].hauteur += t
    @property
    def tessiture(self):
        """Notes extrêmes de la mélodie"""
        minimum = maximum = 0
        # Parcours de toutes les notes de la mélodie, pour déterminer
        # la plus haute et la plus basse.
        for note in self.musique:
            if minimum == 0 or note.hauteur < minimum:
                minimum = note.hauteur
            if note.hauteur > maximum:
                maximum = note.hauteur
        #### TODO: voir pourquoi la bidouille abjecte qui suit est  ####
        #### nécessaire…                                            ####
        minimum += 1
        if self.transposition:
            minimum += self.transposition
            maximum += self.transposition
        return {'minimum': minimum, 'maximum': maximum}
    def verifier(self,alertes):
        """Contrôle de la présence de certains caractères
        (à la demande de l'utilisateur"""
        for alerte in alertes:
            if alerte in self.texte:
                print("!!! " + alerte + " !!!")

class Note:
    """Note de musique"""
    def __init__(self,**parametres):
        self.b = ''
        if 'bemol' in parametres:
            self.b = parametres['bemol']
        if 'hauteur' in parametres:
            self.hauteur = parametres['hauteur']
        if 'duree' in parametres:
            self.duree = parametres['duree']
        if 'gabc' in parametres:
            self.gabc = parametres['gabc']
            self.hauteur,self.duree = self.g2mid(parametres['gabc'])
        self.ly = self.g2ly()
    @property
    def nom(self):
        """Renvoi du nom "canonique" de la note."""
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
        """Renvoi du code lilypond correspondant à la note."""
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
        note += (",,",
                ",",
                "",
                "'",
                "''",
                "'''",
                "''''")[o-1]
        # Durée de la note : croche par défaut, pourra être précisée
        # par la suite.
        note += '8'
        return note
    def ly_ccl(self,premierenote):
        if premierenote:
            return True
        if '4' in self.ly:
            return False
        if '\n' not in self.ly:
            if ']' not in self.ly:
                if '[' in self.ly:
                    self.ly = self.ly.replace('[','')
                else:
                    self.ly += ']'
            return True
    def g2mid(self,gabc):
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
        gammenotes = ('la','si','do','re','mi','fa','sol')
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
        if cle == 'f3': o = -12
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
            if notes[lettre] != 'si' :
                print(notes[lettre] + ' bémol rencontré')
            hauteur -= 1
        return hauteur,duree

class Midi:
    """Musique midi"""
    def __init__(self,partition,tempo):
        # Définition des paramètres MIDI.
        piste = 0
        temps = 0
        self.sortieMidi = MIDIFile(1)
        # Nom de la piste.
        self.sortieMidi.addTrackName(piste,temps,"Gregorien")
        # Tempo.
        self.sortieMidi.addTempo(piste,temps, tempo)
        # Instrument (74 : flûte).
        self.sortieMidi.addProgramChange(piste,0,temps,74)
        # À partir des propriétés de la note, création des évènements
        # MIDI.
        for note in partition.musique:
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
    def ecrire(self,chemin):
        """Écriture effective du fichier MIDI"""
        binfile = open(chemin, 'wb')
        self.sortieMidi.writeFile(binfile)
        binfile.close()

class Lily:
    def __init__(self,partition,tempo):
        self.transposition = (
            "c,","des,","d,","ees,","e,","f,",
            "fis,","g,","aes,","a,","bes,","b,",
            "c","des","d","ees","e","f",
            "fis","g","aes","a","bes","b","c"
            )[(partition.transposition + 11)%24]
        self.musique = ' '.join(note.ly for note in partition.musique)
        self.tonalite = partition.tonalite[0]
        self.texte = self.paroles(partition.texte)
    def paroles(self,texte):
        paroles = ''
        for mot in texte:
            paroles += ' -- '.join(syllabe.replace(' ','_')
                for syllabe in mot
                ) + ' '
        return paroles\
            .replace(' *','_*')\
            .replace(' :','_:\n')\
            .replace(' ;','_;\n')\
            .replace(' !','_!\n')\
            .replace('. ','.\n ')
    def ecrire(self,chemin):
        sortie = FichierTexte(chemin)
        sortie.ecrire(ENTETE_LILYPOND % {
                        'tonalite': self.tonalite,
                        'musique': self.musique,
                        'transposition': self.transposition,
                        'paroles': self.texte
                        }
                    )

class Fichier:
    """Gestion des entrées/sorties fichier"""
    def __init__(self,chemin):
        self.dossier = os.path.dirname(chemin)
        self.nom = os.path.splitext(os.path.basename(chemin))[0]
        self.chemin = chemin

class FichierTexte:
    """Gestion des fichiers texte"""
    def __init__(self,chemin):
        self.dossier = os.path.dirname(chemin)
        self.nom = os.path.splitext(os.path.basename(chemin))[0]
        self.chemin = chemin
    @property
    def contenu(self):
        """Lecture du contenu"""
        fichier = open(self.chemin,'r')
        texte = fichier.read(-1)
        fichier.close()
        return texte
    def ecrire(self,contenu):
        """Écriture dans le fichier"""
        fichier = open(self.chemin,'w')
        fichier.write(contenu)
        fichier.close()

if __name__ == '__main__':
    gabc2tk(sys.argv[0],sys.argv[1:])
