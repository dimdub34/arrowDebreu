# -*- coding: utf-8 -*-
"""=============================================================================
This modules contains the variables and the parameters.
Do not change the variables.
Parameters that can be changed without any risk of damages should be changed
by clicking on the configure sub-menu at the server screen.
If you need to change some parameters below please be sure of what you do,
which means that you should ask to the developer ;-)
============================================================================="""
from datetime import time


# variables --------------------------------------------------------------------
CARA = 0
CRRA = 1
TREATMENTS_NAMES = {CARA: "CARA", CRRA: "CRRA"}
BUY = BUYER = 0
SELL = SELLER = 1
PILE = 0
FACE = 1

# parameters -------------------------------------------------------------------
TREATMENT = CARA
TAUX_CONVERSION = 1
NOMBRE_PERIODES = 1
MARKET_TIME = time(0, 0, 30)  # hour, minute, second
SUMMARY_TIME = time(0, 1, 30)  # timer on the summary screen
TAILLE_GROUPES = 2
# la place du joueur dans le groupe détermine sa dotation et son aversion
ENDOWMENT = [(5, 25), (5, 25), (5, 25), (25, 5), (25, 5), (25, 5)]
AVERSION = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]


GROUPES_CHAQUE_PERIODE = False
MONNAIE = u"euro"
PARTIE_ESSAI = False


