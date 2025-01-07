Gabctk
======

Outil pour travailler sur les fichiers gabc.

[English Documentation](README-en.md).

Gabc
----

Le *gabc* est le langage utilisé par le logiciel
[Gregorio](https://gregorio-project.github.io/).
Vous en trouverez la description [ici](https://gregorio-project.github.io/gabc/).

Gabctk
------

Ce script est dérivé de [gabc2mid](https://github.com/jperon/gabc2mid) ;
l'optique du projet s'étant élargie, gabc2mid restera tel qu'il est à présent
(sauf correction de bug), et les développements auront lieu ici.
Gabctk parcourt le code *gabc*, en extrait ce qui concerne la mélodie,
et produit celle-ci sous la forme d'un fichier midi et/ou lilypond, abc,
musicxml.
Il peut aussi extraire le texte dans un fichier texte.
La syntaxe est la suivante :

    gabctk.py -i </chemin/vers/le/fichier/source.gabc> \
             [-n titre] \
             [-o </chemin/vers/le/fichier/destination.mid>] \
             [-l </chemin/vers/le/fichier/destination.ly>] \
             [-c </chemin/vers/le/fichier/destination.abc>] \
             [-x </chemin/vers/le/fichier/destination.xml>] \
             [-b </chemin/vers/le/fichier/destination.tab>] \
             [-e </chemin/vers/le/fichier/destination.txt>] \
             [-m </chemin/vers/le/fichier/destination.mus>] \
             [-t tempo] \
             [-d transposition] \
             [-a alerte] \
             [-v verbosité]

Toutes les options entre crochets sont facultatives. `gabc -h` affiche une aide sommaire.

Si, à la place d'un nom de fichier, vous voulez utiliser l'entrée ou la sortie
standard, spécifiez `-`. Par exemple, pour écouter un gabc grâce à `timidity` :

    gabctk.py -i <fichier/source.gabc> -o - | timidity -

Ou encore, pour extraire le texte du gabc et l'afficher :

    gabctk.py -i <fichier/source.gabc> -e -

Le tempo est exprimé en temps premiers par minute :
sa valeur par défaut est 165.

La transposition est exprimée en demi-tons. En son absence, gabctk transposera
automatiquement le chant sur une tessiture facile à chanter. Pour les formats
abc et musicxml, la gestion de la transposition est laissée à abc et aux
différents logiciels compatibles avec ces formats. Les notes resteront donc
graphiquement en place, mais la mélodie sera jouée à la hauteur indiquée par
ce paramètre.

Si des alertes sont définies, gabctk renverra un message chaque fois
qu'il détecte la chaîne de caractères dans le texte du chant.
Par exemple, `gabctk.py -i \<Fichier.gabc\> -a j -a eumdem` renverra un message
si le texte contient des *j* ou le mot *eumdem*.

Il est encore possible de convertir plusieurs fichiers à la fois. En ce cas,
il faut donner en paramètre à `-o`, `-l`, `-c`, `-x` ou `-b` un dossier
et non un fichier individuel. Par exemple, pour convertir en midi tous
les gabc du répertoire courant :

    gabctk.py -i *.gabc -o .

Exécutable autonome
-------------------

Il est possible de récupérer dans [Releases](https://github.com/jperon/gabctk/releases)
ou de créer soi-même un exécutable contenant tout ce qui est nécessaire pour utiliser
gabctk, aussi bien sous Linux que sous MacOS ou encore Windows (grâce à
[cosmopolitan](https://github.com/jart/cosmopolitan/)). Étant admis que le programme
`zip` est accessible à l’interpréteur de commandes, `make com` devrait générer
`gabctk.com`, utilisable comme décrit ci-dessus (en remplaçant `gabctk.py`
par `gabctk.com`).
