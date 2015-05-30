Gabctk
======

Outil pour travailler sur les fichiers gabc.

[English Documentation](http://www.sspxusa.org/goodies/gabc2mid/)

Gabc
----

Le *gabc* est le langage utilisé par le logiciel
[Gregorio](http://home.gna.org/gregorio/).
Vous en trouverez la description [ici](http://home.gna.org/gregorio/gabc/).


Gabctk
------

Ce script est dérivé de [gabc2mid](https://github.com/jperon/gabc2mid) ;
l'optique du projet s'étant élargie, gabc2mid restera tel qu'il est à présent
(sauf correction de bug), et les développements auront lieu ici.
Gabctk parcourt le code *gabc*, en extrait ce qui concerne la mélodie,
et produit celle-ci sous la forme d'un fichier midi et/ou lilypond.
Il peut aussi extraire le texte dans un fichier texte.
La syntaxe est la suivante :

    gabctk.py -i </chemin/vers/le/fichier/source.gabc> \
             [-o </chemin/vers/le/fichier/destination.mid>] \
             [-l </chemin/vers/le/fichier/destination.ly>] \
             [-b </chemin/vers/le/fichier/destination.tab>] \
             [-e </chemin/vers/le/fichier/destination.txt>] \
             [-m </chemin/vers/le/fichier/destination.mus>] \
             [-t tempo] \
             [-d transposition] \
             [-a alerte] \

Toutes les options entre crochets sont facultatives.

Si, à la place d'un nom de fichier, vous voulez utiliser l'entrée ou la sortie
standard, spécifiez `-`. Par exemple, pour écouter un gabc grâce à `timidity` :

    gabctk.py -i <fichier/source.gabc> -o - | timidity -

Ou encore, pour extraire le texte du gabc et l'afficher :

    gabctk.py -i <fichier/source.gabc> -e -

Le tempo est exprimé en temps premiers par minute :
sa valeur par défaut est 165.

La transposition est exprimée en demi-tons. En son absence, gabctk transposera
automatiquement le chant sur une tessiture facile à chanter.

Si des alertes sont définies, gabctk renverra un message chaque fois
qu'il détecte la chaîne de caractères dans le texte du chant.
Par exemple, `gabctk -i \<Fichier.gabc\> -a j -a eumdem` renverra un message
si le texte contient des *j* ou le mot *eumdem*.

Si vous ne voulez pas modifier les options par défaut,
vous pouvez aussi utiliser la syntaxe suivante :

    gabctk.py </chemin/vers/le/fichier/source.gabc>
             [</chemin/vers/le/fichier/destination.mid>]
             OU
             [</chemin/vers/le/fichier/destination.ly>]
