gabc2mid
========

Conversion de gabc en midi.

[English Documentation](http://www.sspxusa.org/goodies/gabc2mid/)

Gabc
----

Le *gabc* est le langage utilisé par le logiciel [Gregorio](http://home.gna.org/gregorio/). Vous en trouverez la description [ici](http://home.gna.org/gregorio/gabc/).

Gabc2mid
--------

Ce script parcourt le code *gabc*, en extrait ce qui concerne la mélodie, et produit celle-ci sous la forme d'un fichier midi. Il peut aussi extraire le texte dans un fichier texte. La syntaxe est la suivante :

gabc2mid.py -i \</chemin/vers/le/fichier/source.gabc\> [-o \</chemin/vers/le/fichier/destination.mid\>] [-e \</chemin/vers/le/fichier/destination.txt\>] [-t tempo] [-d transposition] [-a alerte]

Seul le premier argument est obligatoire : tous les autres sont optionnels.

En l'absence du deuxième argument (fichier midi de destination), gabc2mid produira un fichier midi dans le même dossier que la source, portant le même nom.

En l'absence du troisième argument (fichier texte de destination), aucun fichier texte ne sera produit.

Le tempo est exprimé en temps premiers par minute : sa valeur par défaut est 165.

La transposition est exprimée en demi-tons. En son absence, gabc2mid transposera automatiquement le chant sur une tessiture facile à chanter. Le programme renvoie sur la sortie standard la plus basse et la plus haute notes obtenues.

Si des alertes sont définies, gabc2mid renverra un message chaque fois qu'il détecte la chaîne de caractères dans le texte du chant. Par exemple, *gabc2mid -i <Fichier.gabc> -a j -a eumdem* renverra un message si le texte contient des *j* ou le mot *eumdem*.

Si vous ne voulez pas modifier les options par défaut, vous pouvez aussi utiliser la syntaxe suivante :

gabc2mid.py \</chemin/vers/le/fichier/source.gabc\> [\</chemin/vers/le/fichier/destination.mid\>]

