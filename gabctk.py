#! /usr/bin/python3
# -*- coding: UTF-8 -*-

DUREE_EPISEME = 1.7
DUREE_AVANT_QUILISMA = 2
DUREE_POINT = 2.3

import os,sys,getopt
import re
from midiutil.MidiFile3 import MIDIFile

def gabc2mid(commande,arguments):
    """Fonction maîtresse"""
    # Initialisation des variables correspondant aux paramètres.
    debug = False
    tempo = 165
    entree = sortie = transposition = ''
    alertes = corrections = []
    # Analyse des arguments de la ligne de commande.
    try:
        opts, args = getopt.getopt(
                                arguments,
                                "hi:o:e:t:d:a:v",
                                [
                                    "help",                             # Aide
                                    "entree=",                          # Fichier gabc
                                    "sortie=",                          # Fichier MIDI
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
    # considérer le premier comme étant le gabc en entrée ;
    # en l'absence de deuxième, donner à la sortie le même nom,
    # en changeant l'extension.
    try:
        if entree == '':
            entree = FichierTexte(arguments[0])
        if sortie == '':
            try:
                sortie = FichierTexte(arguments[1])
            except IndexError:
                sortie = Fichier(re.sub('.gabc','.mid',arguments[0]))
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
    # Si l'utilisateur a demandé une sortie verbeuse, afficher :
    if debug:
        ## la partition gabc (sans les en-têtes) ;
        print(gabc.contenu)
        ## la liste des couples (clé, signe gabc) ;
        print(gabc.partition)
        ## les paroles seules ;
        print(partition.texte)
        ## les notes seules.
        print([note.nom for note in partition.musique])
    # Créer le fichier midi.
    midi = Midi(partition.musique,tempo)
    midi.ecrire(sortie.chemin)
    # S'assurer de la présence de certains caractères,
    # à la demande de l'utilisateur.
    try: partition.verifier(alertes)
    except: pass
    # Si l'utilisateur l'a demandé,
    # écrire les paroles dans un fichier texte.
    try: texte.ecrire(partition.texte)
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
        # A priori, pas de bémol à la clé.
        self.b = ''
        # S'il y a un bémol à la clé, en tenir compte.
        if 'bemol' in parametres:
            self.b = self.b + parametres['bemol']
        # Cas où l'instance de classe est initialisée avec le code gabc
        # (cas le plus courant).
        if 'gabc' in parametres:
            self.musique,self.texte = self.g2p(parametres['gabc'])
        # Si l'instance de classe est initialisée avec l'ensemble des
        # notes (pour tessiture ou transposition).
        if 'partition' in parametres:
            self.musique = parametres['pitches']
        # A priori, pas de transposition manuelle
        # (elle sera alors calculée automatiquement).
        transposition = None
        # Si transposition définie, en tenir compte.
        if 'transposition' in parametres:
            try: transposition = int(parametres['transposition'])
            except ValueError: pass
        # Effectuer la transposition.
        self.transposer(transposition)
    def g2p(self,gabc):
        """Analyser le code gabc pour en sortir :
            − la mélode (liste d'objets notes) ;
            − le texte (chaîne de caractères)."""
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
        mot = 0
        texte = ''
        neume = 0
        neumeencours = ''
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
                elif signe[1] == point:
                    j -= 1
                    notes[j].duree = DUREE_POINT
                elif signe[1] == quilisma:
                    notes[-2].duree = DUREE_AVANT_QUILISMA
                # Altérations.
                elif signe[1] == bemol:
                    b = b + memoire[1]
                    notes = notes[:-1]
                elif signe[1] == becarre:
                    re.sub(memoire[1],'',b)
                    notes = notes[:-1]
                # Fin d'élément neumatique : faute de pouvoir déterminer
                # aussi précisément que dans les manuscrits la valeur
                # des coupures, s'assurer pour le moins que la dernière
                # note d'un élément n'est pas plus courte que la
                # pénultième.
                elif signe[1] in coupures:
                    if notes[-1].duree < notes[-2].duree:
                        notes[-1].duree = notes[-2].duree
                # Une barre annule les altérations accidentelles,
                # et provoque un "posé", d'où léger rallongement de la
                # note précédente.
                elif signe[1] in barres:
                    b = '' + self.b
                    if signe[1] == ';':
                        notes[-1].duree += .5
                    elif signe[1] == ':':
                        notes[-1].duree += 1
                else:
                    # Dans le calcul des durées : la dernière note d'un
                    # neume n'est jamais plus courte que la pénultième.
                    if neumeencours == neume \
                    and notes[-1].duree < notes[-2].duree:
                        notes[-1].duree = notes[-2].duree
                    if signe[1] == ')':
                        musique = 0
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
                # Ignorer les accolades
                # (qui servent à centrer les notes sur une lettre).
                elif signe[1] in ('{', '}'): pass
                else:
                    # Le changement de mot en grégorien implique
                    # l'annulation des altérations accidentelles.
                    if signe[1] == ' ':
                        mot += 1
                        b = '' + self.b
                        try:
                            # Ignorer les espaces répétitifs.
                            if texte[-1] != ' ':
                                texte += signe[1]
                        except IndexError: pass
                    else: texte += signe[1]
            # "Traitement" (par le vide !) des commandes spéciales.
            elif musique == 2:
                if signe[1] == ']':
                    musique = 1
        return notes, texte
    def transposer(self,transposition):
        """Transposition de la partition :
            − ou bien suivant l'intervalle défini ;
            − ou bien automatiquement sur une tessiture moyenne."""
        # Calcul si nécessaire de la hauteur idéale.
        if transposition == None:
            t = 66 - int(sum(self.tessiture.values())/2)
        else: t = transposition
        # Transposition effective.
        for i in range(len(self.musique)):
            self.musique[i].hauteur += t
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
        """Renvoi de la note correspondant à une lettre gabc"""
        # Définition de la gamme.
        la = 57                 # Le nombre correspond au "pitch" MIDI.
        si = la + 2
        do = la + 3
        re = do + 2
        mi = re + 2
        fa = mi + 1
        sol = fa + 2
        gamme = (la, si, do, re, mi, fa, sol)
        gabcnotes = "abcdefghijklm"
        # Analyse de la clé : les lettres du gabc définissant une
        # position sur la portée et non une hauteur de note, la note
        # correspondant à une lettre dépend de la clé.
        cle = gabc[0]
        # On n'a pas besoin de savoir s'il y a bémol à la clé pour
        # déterminer la hauteur des notes.
        if len(cle) == 3:
            cle = cle[0] + cle[2]
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
        notes = {}
        for j in gabcnotes:
            try:
                i += 1
                notes[j] = gamme[i] + o
            except IndexError:
                i -= 7
                o += 12
                notes[j] = gamme[i] + o
        # Par défaut, la durée est à 1 : elle pourra être modifiée par
        # la suite, s'il se rencontre un épisème, un point, etc.
        duree = 1
        lettre = gabc[1].lower()
        hauteur = notes[lettre]
        if lettre in self.b:
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
        """Écriture effective du fichier MIDI"""
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
    gabc2mid(sys.argv[0],sys.argv[1:])
