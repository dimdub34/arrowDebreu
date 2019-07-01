# -*- coding: utf-8 -*-

# built-in
import logging
from collections import OrderedDict
from twisted.internet import defer
from PyQt4.QtGui import QMessageBox

# le2m
from util import utiltools
from util.utili18n import le2mtrans
from util.utiltools import get_module_attributes, timedelta_to_time
from server.servgui.servguidialogs import DSequence, GuiPayoffs

# arrowDebreu
import arrowDebreuParams as pms
from arrowDebreuGui import DConfigure
from arrowDebreuGroup import ADGroup

logger = logging.getLogger("le2m.srv")


class Serveur(object):
    def __init__(self, le2mserv):
        self.le2mserv = le2mserv
        self.current_sequence = 0
        self.current_period = 0
        self.all = []
        self.groups = []

        # ----------------------------------------------------------------------
        # creation of the menu (will be placed in the "part" menu on the
        # server screen)
        # ----------------------------------------------------------------------
        actions = OrderedDict()
        actions[le2mtrans(u"Configure")] = self.configure
        actions[le2mtrans(u"Display parameters")] = \
            lambda _: self.le2mserv.gestionnaire_graphique. \
                display_information2(
                utiltools.get_module_info(pms), le2mtrans(u"Parameters"))
        actions[le2mtrans(u"Start")] = lambda _: self.demarrer()
        actions[le2mtrans(u"Display payoffs")] = \
            lambda _: self.display_payoffs()
        self.le2mserv.gestionnaire_graphique.add_topartmenu(
            u"Arrow Debreu", actions)

    def configure(self):
        screen_conf = DConfigure(self.le2mserv.gestionnaire_graphique.screen)
        if screen_conf.exec_():
            self.le2mserv.gestionnaire_graphique.infoserv(None)
            self.le2mserv.gestionnaire_graphique.infoserv(
                u"Traitement: {}".format(
                    pms.TREATMENTS_NAMES.get(pms.TREATMENT)))
            self.le2mserv.gestionnaire_graphique.infoserv(
                u"Nombre de périodes: {}".format(pms.NOMBRE_PERIODES)
            )
            self.le2mserv.gestionnaire_graphique.infoserv(
                u"Taille des groupes: {}".format(pms.TAILLE_GROUPES)
            )
            self.le2mserv.gestionnaire_graphique.infoserv(
                u"Temps de marché: {}".format(pms.MARKET_TIME)
            )
            self.le2mserv.gestionnaire_graphique.infoserv(
                u"Partie d'essai: {}".format(
                    u"oui" if pms.PARTIE_ESSAI else u"non"))

    @defer.inlineCallbacks
    def demarrer(self):

        # ----------------------------------------------------------------------
        #
        #                           check conditions
        #
        # ----------------------------------------------------------------------

        if not self.le2mserv.gestionnaire_graphique.question(
                le2mtrans(u"Start") + u" arrowDebreu?"):
            return

        # ----------------------------------------------------------------------
        #
        #                              init part
        #
        # ----------------------------------------------------------------------

        self.current_sequence += 1
        self.current_period = 0

        try:
            yield (self.le2mserv.gestionnaire_experience.init_part(
                "arrowDebreu", "PartieAD",
                "RemoteAD", pms))
        except Exception as e:
            logger.critical("Error init part: " + e.message)
            return
        self.all = self.le2mserv.gestionnaire_joueurs.get_players(
            'arrowDebreu')

        for j in self.all:
            j.AD_sequence = self.current_sequence

        logger.debug("Ok initialisation partie")

        # ----------------------------------------------------------------------
        # formation des groupes
        # ----------------------------------------------------------------------
        # les groupes ne sont pas reformés à chaque lancement de partie
        if not self.groups:
            try:
                gps = utiltools.form_groups(
                    self.le2mserv.gestionnaire_joueurs.get_players(),
                    pms.TAILLE_GROUPES, self.le2mserv.nom_session)
            except ValueError as e:
                QMessageBox.critical(None, "Group error", e.message)
                self.current_sequence -= 1
                return
            logger.debug("Groups: {}".format(gps))

            for g, m in sorted(gps.items()):
                logger.debug("Creation of group {}".format(g))
                try:
                    group = ADGroup(self.le2mserv, g,
                                    [i.get_part("arrowDebreu") for i in m],
                                    self.current_sequence)
                    self.le2mserv.gestionnaire_base.ajouter(group)
                except Exception as e:
                    logger.critical(
                        "Error creation group: {}".format(e.message))
                    return
                logger.debug("Ok creation group")
                self.groups.append(group)
                for j in m:
                    j.group = group

        else:
            groups_new = []
            for g in self.groups:
                group_players = [k.joueur for k in g.get_players()]
                g_comp = []
                for j in group_players:
                    for k in self.all:
                        if k.joueur == j:
                            g_comp.append(k)
                            break
                group = ADGroup(self.le2mserv, g.uid, g_comp,
                                self.current_sequence)
                self.le2mserv.gestionnaire_base.ajouter(group)
                groups_new.append(group)
                for j in g.get_players():
                    j.joueur.group = group
            self.groups = groups_new

        # enregistrement dans champs de la partie
        for j in self.all:
            j.AD_group = j.joueur.group.uid

        # Affichage composition
        self.le2mserv.gestionnaire_graphique.infoserv("Groups", bg="gray",
                                                      fg="white")
        for g in self.groups:
            self.le2mserv.gestionnaire_graphique.infoserv(
                "__ {} __".format(g))
            for j in g.get_players():
                self.le2mserv.gestionnaire_graphique.infoserv(
                    "{}".format(j.joueur))

        # ----------------------------------------------------------------------
        # envoie de la configurations aux clients
        # ----------------------------------------------------------------------
        try:
            yield (self.le2mserv.gestionnaire_experience.run_step(
                le2mtrans(u"Configure"), self.all, "configure"))
        except Exception as e:
            logger.critical("Error configure: " + e.message)
            return

        # ----------------------------------------------------------------------
        #
        #                           Loop Periods
        #
        # ----------------------------------------------------------------------

        for period in range(1, pms.NOMBRE_PERIODES + 1):

            if self.le2mserv.gestionnaire_experience.stop_repetitions:
                break

            self.current_period = period

            # ------------------------------------------------------------------
            # init period
            # ------------------------------------------------------------------

            self.le2mserv.gestionnaire_graphique.infoserv(
                [None, le2mtrans(u"Period") + u" {}".format(period)])
            self.le2mserv.gestionnaire_graphique.infoclt(
                [None, le2mtrans(u"Period") + u" {}".format(period)],
                fg="white", bg="gray")

            # players
            yield (self.le2mserv.gestionnaire_experience.run_func(
                self.all, "newperiod", period))

            # groups
            for g in self.groups:
                g.new_period(self.current_period)

            # ------------------------------------------------------------------
            # decision
            # ------------------------------------------------------------------

            yield (self.le2mserv.gestionnaire_experience.run_step(
                le2mtrans(u"Decision"), self.all, "display_decision"))

            # ------------------------------------------------------------------
            # period payoffs
            # ------------------------------------------------------------------

            self.le2mserv.gestionnaire_experience.compute_periodpayoffs(
                "arrowDebreu")

            # ------------------------------------------------------------------
            # summary
            # ------------------------------------------------------------------

            yield (self.le2mserv.gestionnaire_experience.run_step(
                le2mtrans(u"Summary"), self.all, "display_summary"))

        # ----------------------------------------------------------------------
        #
        #                            End of part
        #
        # ----------------------------------------------------------------------

        yield (self.le2mserv.gestionnaire_experience.finalize_part(
            "arrowDebreu"))

    def display_payoffs(self):
        sequence_screen = DSequence(self.current_sequence)
        if sequence_screen.exec_():
            sequence = sequence_screen.sequence
            players = self.le2mserv.gestionnaire_joueurs.get_players()
            payoffs = sorted([(j.hostname, p.AD_gain_euros) for j in players
                              for p in j.parties if p.nom == "arrowDebreu" and
                              p.AD_sequence == sequence])
            logger.debug(payoffs)
            screen_payoffs = GuiPayoffs(self.le2mserv, "arrowDebreu", payoffs)
            screen_payoffs.exec_()
