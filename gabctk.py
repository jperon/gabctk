#! /usr/bin/python3
# -*- coding: UTF-8 -*-

import os,sys,getopt
import re
from midiutil.MidiFile3 import MIDIFile

def gabc2mid(arguments):
    """Fonction maîtresse"""
    # Initialisation des variables correspondant aux paramètres.
    debug = False
    tempo = 165
    entree = sortie = transposition = ''
    alertes = corrections = []
    # Analyse des arguments de la ligne de commande
    try:
        opts, args = getopt.getopt(
                                arguments,
                                "hi:o:e:t:d:a:v",
                                [
                                    "help",                             # Aide
                                    "entree=",                          # Fichier gabc
                                    "sortie=",                          # Fichier midi
                                    "export=",                          # Fichier texte
                                    "tempo=",                           # Tempo de la musique
                                    "transposition=",                   # Transposition
                                    "alerter=",                         # Caractères à signaler s'ils se trouvent dans le gabc
                                    "verbose"                           # Verbosité de la sortie
                                ]
                                )
    except getopt.GetoptError:
        aide('Argument invalide',1)
    for opt, arg in opts:
        if opt == '-h':
            aide(0)
        elif opt in ("-i", "--entree"):
            entree = FichierTexte(arg)
            sortie = Fichier(re.sub('.gabc','.mid',arg))
        elif opt in ("-o", "--sortie"):
            sortie = Fichier(arg)
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
    # considérer le premier comme étant le gabc en entrée,
    # et donner à la sortie le même nom en changeant l'extension.
    try:
        if entree == '':
            entree = FichierTexte(arguments[0])
        if sortie == '':
            sortie = Fichier(re.sub('.gabc','.mid',arguments[0]))
    # S'il n'y a aucun argument, afficher l'aide.
    except IndexError: aide('aucun argument',0)
    # Extraire le contenu du gabc.
    try: gabc = Gabc(entree.contenu)
    # Si le gabc n'existe pas, afficher l'aide.
    except FileNotFoundError:
        aide('fichier inexistant',2)
    # Extraire la partition.
    partition = Partition(
                        gabc = gabc.musique,
                        transposition = transposition
                        )
    # Afficher la tessiture obtenue après transposition.
    print(Note(hauteur = partition.tessiture['minimum']).nom
        + " - "
        + Note(hauteur = partition.tessiture['maximum']).nom)
    # Si l'utilisateur a demandé une sortie verbeuse, afficher :
    if debug:
        ## la partition gabc (sans les en-têtes)
        print(gabc.partition)
        ## la liste des couples (clé, signe gabc)
        print(gabc.musique)
        ## les paroles seules
        print(partition.texte)
        ## les notes seules
        print([note.nom for note in partition.notes])
    # Créer le fichier midi
    midi = Midi(partition.notes,tempo)
    midi.ecrire(sortie.chemin)
    # S'assurer de la présence de caractères "alertes"
    try: partition.verifier(alertes)
    except: pass
    # Si l'utilisateur l'a demandé,
    # écrire les paroles dans un fichier texte
    try: texte.ecrire(partition.texte)
    except UnboundLocalError: pass

def aide(erreur,code):
    """Affichage de l'aide"""
    # Tenir compte du message propre à chaque erreur.
    print('Erreur : '
            + erreur + '\n'
            + '''Usage :
            gabctk.py'''
            + '-i <input.gabc> '
            + '[-o <output.mid>] '
            + '[-e <texte.txt>] '
            + '[-t <tempo>] '
            + '[-v]''')
    # Renvoyer le code correspondant à l'erreur,
    # pour interagir avec d'autres programmes.
    sys.exit(code)

class Gabc:
    """Contenu du fichier gabc"""
    def __init__(self,contenu):
        self.contenu = contenu
    @property
    def partition(self):
        '''Partition gabc sans les en-têtes'''
        resultat = self.contenu
        regex = re.compile('%%\n')
        resultat = regex.split(resultat)[1]
        resultat = re.sub('%.*\n','',resultat)
        resultat = re.sub('\n',' ',resultat)
        return resultat
    @property
    def musique(self):
        '''Liste de couples (clé, signe gabc)'''
        resultat = []
        partition = self.partition
        # Recherche des clés
        regex = re.compile('[cf][b]?[1234]')
        cles = regex.findall(partition)
        # Découpage de la partition en fonction des changements de clé
        partiestoutes = regex.split(partition)
        parties = partiestoutes[0] + partiestoutes[1], partiestoutes[2:]
        # Définition des couples (clé, signe)
        for i in range(len(cles)):
            cle = cles[i]
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
        self.b = ''                                                     # A priori,  pas de bémol à la clé.
        transposition = None
        if 'partition' in parametres:
            self.notes = parametres['pitches']
        if 'bemol' in parametres:
            self.b = self.b + parametres['bemol']
        if 'gabc' in parametres:
            self.notes,self.texte = self.g2p(parametres['gabc'])
        if 'transposition' in parametres:
            try: transposition = int(parametres['transposition'])
            except ValueError: pass
        self.transposer(transposition)
    def g2p(self,gabc):
        """Analyser le code gabc pour en sortir :
            − la mélode (liste d'objets notes) ;
            − le texte (chaîne de caractères."""
        gamme = "abcdefghijklm"
        episeme = '_'
        point = '.'
        quilisma = 'w'
        speciaux = 'osvOSV'
        barres = '`,;:'
        bemol = "x"
        becarre = "y"
        coupures = '/ '
        notes = []
        b = '' + self.b
        mot = 0
        texte = ''
        neume = 0
        neumeencours = ''
        musique = 0
        for i in range(len(gabc)):
            signe = gabc[i]
            if musique == 1:
                if signe[1].lower() in gamme:
                    j = 0
                    s = 0
                    note = Note(gabc = signe, bemol = b)
                    notes.append(note)
                    memoire = signe
                elif signe[1] in speciaux:
                    s += 1
                    if s > 1:
                        note = Note(gabc = memoire, bemol = b)
                        notes.append(note)
                elif signe[1] == episeme:
                    neumeencours = neume
                    j -= 1
                    notes[j].duree = 1.7
                elif signe[1] == point:
                    j -= 1
                    notes[j].duree = 2.3
                elif signe[1] == quilisma:
                    notes[-2].duree = 2
                elif signe[1] == bemol:
                    b = b + memoire[1]
                    notes = notes[:-1]
                elif signe[1] == becarre:
                    re.sub(memoire[1],'',b)
                    notes = notes[:-1]
                elif signe[1] in coupures:
                    if notes[-1].duree < notes[-2].duree:
                        notes[-1].duree = notes[-2].duree
                elif signe[1] in barres or signe[1] in coupures:
                    b = '' + self.b
                    if signe[1] == ';':
                        notes[-1].duree += .5
                    elif signe[1] == ':':
                        notes[-1].duree += 1
                else:
                    if signe[1] == ')':
                        musique = 0
                    if signe[1] == '[':
                        musique = 2
                    if neumeencours == neume \
                    and notes[-1].duree < notes[-2].duree:
                        notes[-1].duree = notes[-2].duree
            elif musique == 0:
                if signe[1] == '(':
                    musique = 1
                    neume += 1
                elif signe[1] in ('{', '}'): pass
                else:
                    if signe[1] == ' ':
                        mot += 1
                        b = '' + self.b
                        try:
                            if texte[-1] != ' ':
                                texte += signe[1]
                        except IndexError: pass
                    else: texte += signe[1]
            elif musique == 2:
                if signe[1] == ']':
                    musique = 1
        return notes, texte
    def transposer(self,transposition):
        if transposition == None:
            t = 66 - int(sum(self.tessiture.values())/2)
        else: t = transposition
        for i in range(len(self.notes)):
            self.notes[i].hauteur += t
    @property
    def tessiture(self):
        """Notes extrêmes de la mélodie"""
        minimum = maximum = 0
        for note in self.notes:
            if minimum == 0 or note.hauteur < minimum:
                minimum = note.hauteur
            if note.hauteur > maximum:
                maximum = note.hauteur
        return {'minimum': minimum, 'maximum': maximum}
    def verifier(self,alertes):
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
            self.hauteur,self.duree = self.g2p(parametres['gabc'])
    @property
    def nom(self):
        o = int(self.hauteur / 12) - 1
        n = int(self.hauteur % 12)
        return ('Do',
                'Do#',
                'Ré',
                'Ré#',
                'Mi',
                'Fa',
                'Fa#',
                'Sol',
                'Sol#',
                'La',
                'La#',
                'Si')[n] + str(o)
    def g2p(self,gabc):
        la = 57
        si = la + 2
        do = la + 3
        re = do + 2
        mi = re + 2
        fa = mi + 1
        sol = fa + 2
        octave = 12
        cle = gabc[0]
        if len(cle) == 3:
            cle = cle[0] + cle[2]
            si = la + 1
        note = gabc[1]
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
        gamme = (la, si, do, re, mi, fa, sol)
        i = decalage[cle] - 1
        o = 0
        if cle == 'f3': o = -12
        notes = {}
        for j in "abcdefghijklm":
            try:
                i += 1
                notes[j] = gamme[i] + o
            except IndexError:
                i -= 7
                o += 12
                notes[j] = gamme[i] + o
        duree = 1
        h = note.lower()
        hauteur = notes[h]
        if h in self.b:
            hauteur -= 1
        return hauteur,duree

class Midi:
    """Musique midi"""
    def __init__(self,partition,tempo):
        piste = 0
        temps = 0
        self.sortieMidi = MIDIFile(1)
        self.sortieMidi.addTrackName(piste,temps,"Gregorien")
        self.sortieMidi.addTempo(piste,temps, tempo)
        self.sortieMidi.addProgramChange(piste,0,temps,74)
        for note in partition:
            channel = 0
            pitch = note.hauteur
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
        binfile = open(chemin, 'wb')
        self.sortieMidi.writeFile(binfile)
        binfile.close()

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
        fichier = open(self.chemin,'r')
        texte = fichier.read(-1)
        fichier.close()
        return texte
    def ecrire(self,contenu):
        fichier = open(self.chemin,'w')
        fichier.write(contenu)
        fichier.close()

if __name__ == '__main__':
    gabc2mid(sys.argv[1:])
