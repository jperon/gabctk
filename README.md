gabc2mid
========

Conversion de gabc en midi.

Gabc
----

Le *gabc* est le langage utilisé par le logiciel [Gregorio](http://home.gna.org/gregorio/). Vous en trouverez la description [ici](http://home.gna.org/gregorio/gabc/).

Gabc2mid
--------

Ce script parcourt le code *gabc*, en extrait ce qui concerne la mélodie, et produit celle-ci sous la forme d'un fichier midi. Il peut aussi extraire le texte dans un fichier texte. La syntaxe est la suivante :

gabc2mid.py -i \</chemin/vers/le/fichier/source.gabc\> [-o \</chemin/vers/le/fichier/destination.mid\>] [-e \</chemin/vers/le/fichier/destination.txt\>] [-t tempo] [-d transposition]

Seul le premier argument est obligatoire : tous les autres sont optionnels.

En l'absence du deuxième argument (fichier midi de destination), gabc2mid produira un fichier midi dans le même dossier que la source, portant le même nom.

En l'absence du troisième argument (fichier texte de destination), aucun fichier texte ne sera produit.

Le tempo est exprimé en temps premiers par minute : sa valeur par défaut est 165.

La transposition est exprimée en demi-tons. En son absence, gabc2mid transposera automatiquement le chant sur une tessiture facile à chanter.

Si vous ne voulez pas modifier les options par défaut, vous pouvez aussi utiliser la syntaxe suivante :

gabc2mid.py \</chemin/vers/le/fichier/source.gabc\> [\</chemin/vers/le/fichier/destination.mid\>]
