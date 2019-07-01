# -*- coding: utf-8 -*-

# built-in
import logging
import random
from twisted.internet import defer
from PyQt4.QtGui import QColor
import numpy as np

# le2m
from client.cltremote import IRemote

# Arrow Debreu
import arrowDebreuParams as pms
from arrowDebreuGui import GuiDecision, GuiRecapitulatif

logger = logging.getLogger("le2m.remote")


class RemoteAD(IRemote):
    """
    Class remote, remote_ methods can be called by the server
    """

    def __init__(self, le2mclt):
        IRemote.__init__(self, le2mclt)
        self.player_on_srv = None

    def init_vars(self):
        self.income_pile = 0
        self.income_face = 0
        self.income = 0
        self.aversion = 0

        # ces listes sont vidées au début de chaque période
        # chq liste contient les offres en cours (celles affichées dans les
        # espaces correspondant sur l'interface graphique)
        self.offers_pile_achat = list()
        self.offers_pile_vente = list()
        self.offers_face_achat = list()
        self.offers_face_vente = list()
        self.transactions_pile = list()
        self.transactions_face = list()
        self.histo_vars = [
            "AD_period",
            "AD_nb_buy_pile",
            "AD_nb_sell_pile",
            "AD_sum_buy_pile",
            "AD_sum_sell_pile",
            "AD_nb_buy_face",
            "AD_nb_sell_face",
            "AD_sum_buy_face",
            "AD_sum_sell_face",
            "AD_income_end_pile",
            "AD_income_end_face",
            "AD_periodpayoff",
        ]
        self.histo = [
            u"Période",
             u"nb achats\npile", u"nb ventes\npile", u"somme\nachats\npile",
             u"somme\nventes\npile",
             u"nb achats\nface", u"nb ventes\nface", u"somme\nachats\nface",
             u"somme\nventes\nface",
             u"revenu\npile", u"revenu\nface", u"revenu"
             ]

    def remote_configure(self, params, player_on_srv, initial_incomes,
                         aversion):
        """
        Set the same parameters as in the server side
        :param params: the parameters
        :param player_on_srv: the player on the server side, in order to call
        :param initial_incomes: the income for the pile side (head) and the face side (tail)
        methods
        :return:
        """
        logger.debug(u"{} configure".format(self._le2mclt.uid))
        for k, v in params.viewitems():
            setattr(pms, k, v)
        self.player_on_srv = player_on_srv
        self.init_vars()
        self.income_pile, self.income_face = initial_incomes
        self.aversion = aversion
        self.income = self.get_current_income(self.income_pile,
                                              self.income_face)
        logger.info("{}: initial income: {}, {}".format(self.le2mclt.uid,
                                                        self.income_pile,
                                                        self.income_face))
        return self.income

    def remote_newperiod(self, period):
        """
        Set the current period and delete the history
        :param period: the current period
        :return:
        """
        logger.info(u"{} Period {}".format(self._le2mclt.uid, period))

        self.currentperiod = period

        # on vide les listes
        self.offers_pile_achat[:] = []
        self.offers_pile_vente[:] = []
        self.offers_face_achat[:] = []
        self.offers_face_vente[:] = []
        self.transactions_pile[:] = []
        self.transactions_face[:] = []

    def remote_display_decision(self):
        """
        Display the decision screen
        :return: deferred
        """
        logger.info(u"{} Decision".format(self._le2mclt.uid))
        if self._le2mclt.simulation:
            return self.income_pile, self.income_face, self.income
        else:
            defered = defer.Deferred()
            self.ecran_decision = GuiDecision(self, defered)
            self.ecran_decision.showFullScreen()
            return defered

    def remote_display_summary(self, period_content, group_transactions):
        """
        Display the summary screen
        :param period_content: dictionary with the content of the current period
        :return: deferred
        """
        logger.info(u"{} Summary".format(self._le2mclt.uid))

        self.histo.append([period_content.get(k) for k in self.histo_vars])
        if self._le2mclt.simulation:
            return 1
        else:
            defered = defer.Deferred()
            txt_summary = u"Vous aviez un revenu initial de {} euros si pile " \
                          u"et de {} euros si face. Votre paramètre alpha est " \
                          u"de {}. La valeur initiale de votre " \
                          u"portefeuille était de {} euros.".format(
                period_content["AD_income_start_pile"],
                period_content["AD_income_start_face"],
                self.aversion,
                self.get_current_income(period_content["AD_income_start_pile"],
                                        period_content["AD_income_start_face"]))
            ecran_recap = GuiRecapitulatif(self, defered, txt_summary,
                                           group_transactions)
            ecran_recap.showFullScreen()
            return defered

    def remote_add_offer(self, offer):
        """
        appelé par le joueur côté serveur, pour que l'offre soit ajoutée
        à la liste
        :param offer
        :type dict
        :return:
        """
        logger.info("{} - add_offer: {}".format(self.le2mclt.uid, offer))

        if offer["etat_monde"] == pms.PILE:
            if offer["achat_vente"] == pms.BUY:
                for o in self.offers_pile_achat:
                    if o["player_id"] == offer["player_id"]:
                        self.offers_pile_achat.remove(o)
                self.offers_pile_achat.append(offer)
                self.offers_pile_achat.sort(key=lambda x: x["prix"],
                                            reverse=True)
                self.update_list(
                    self.ecran_decision.listWidget_pile_offre_achat,
                    self.offers_pile_achat)

            else:
                for o in self.offers_pile_vente:
                    if o["player_id"] == offer["player_id"]:
                        self.offers_pile_vente.remove(o)
                self.offers_pile_vente.append(offer)
                self.offers_pile_vente.sort(key=lambda x: x["prix"])
                self.update_list(
                    self.ecran_decision.listWidget_pile_offre_vente,
                    self.offers_pile_vente)

        else:
            if offer["achat_vente"] == pms.BUY:
                for o in self.offers_face_achat:
                    if o["player_id"] == offer["player_id"]:
                        self.offers_face_achat.remove(o)
                self.offers_face_achat.append(offer)
                self.offers_face_achat.sort(key=lambda x: x["prix"],
                                            reverse=True)
                self.update_list(
                    self.ecran_decision.listWidget_face_offre_achat,
                    self.offers_face_achat)

            else:
                for o in self.offers_face_vente:
                    if o["player_id"] == offer["player_id"]:
                        self.offers_face_vente.remove(o)
                self.offers_face_vente.append(offer)
                self.offers_face_vente.sort(key=lambda x: x["prix"])
                self.update_list(
                    self.ecran_decision.listWidget_face_offre_vente,
                    self.offers_face_vente)

    def remote_remove_offer(self, offer):
        """
        Suppression d'une offre
        :param offer: 
        :return: 
        """
        logger.info("{} - remove_offer: {}".format(self.le2mclt.uid, offer))

        if offer["etat_monde"] == pms.PILE:
            if offer["achat_vente"] == pms.BUY:
                for o in self.offers_pile_achat:
                    if o["player_id"] == offer["player_id"]:
                        self.offers_pile_achat.remove(o)
                        break
                self.offers_pile_achat.sort(key=lambda x: x["prix"],
                                            reverse=True)
                self.update_list(
                    self.ecran_decision.listWidget_pile_offre_achat,
                    self.offers_pile_achat)

            else:
                for o in self.offers_pile_vente:
                    if o["player_id"] == offer["player_id"]:
                        self.offers_pile_vente.remove(o)
                        break
                self.offers_pile_vente.sort(key=lambda x: x["prix"])
                self.update_list(
                    self.ecran_decision.listWidget_pile_offre_vente,
                    self.offers_pile_vente)

        else:
            if offer["achat_vente"] == pms.BUY:
                for o in self.offers_face_achat:
                    if o["player_id"] == offer["player_id"]:
                        self.offers_face_achat.remove(o)
                        break
                self.offers_face_achat.sort(key=lambda x: x["prix"],
                                            reverse=True)
                self.update_list(
                    self.ecran_decision.listWidget_face_offre_achat,
                    self.offers_face_achat)

            else:
                for o in self.offers_face_vente:
                    if o["player_id"] == offer["player_id"]:
                        self.offers_face_vente.remove(o)
                        break
                self.offers_face_vente.sort(key=lambda x: x["prix"])
                self.update_list(
                    self.ecran_decision.listWidget_face_offre_vente,
                    self.offers_face_vente)

    def remote_add_transaction(self, transaction):
        """
        appelé par le joueur côté serveur, pour que la transaction soit ajoutée
        à la liste
        :param transaction:
        :return:
        """
        logger.info(
            "{} - add_transaction: {}".format(self.le2mclt.uid, transaction))

        if transaction["etat_monde"] == pms.PILE:
            if transaction["buyer_id"] == self.le2mclt.uid:
                self.income_pile = self.income_pile - transaction["prix"] + 1
                self.income_face -= transaction["prix"]
                self.income = self.get_current_income(self.income_pile,
                                                      self.income_face)

            if transaction["seller_id"] == self.le2mclt.uid:
                self.income_pile = self.income_pile + transaction["prix"] - 1
                self.income_face += transaction["prix"]
                self.income = self.get_current_income(self.income_pile,
                                                      self.income_face)

            self.transactions_pile.insert(0, transaction)
            self.ecran_decision.listWidget_pile_transactions.clear()
            self.ecran_decision.listWidget_pile_transactions.addItems(
                ["{:.2f}".format(t["prix"]) for t in self.transactions_pile])
            for i, t in enumerate(self.transactions_pile):
                if t["buyer_id"] == self.le2mclt.uid or t[
                    "seller_id"] == self.le2mclt.uid:
                    self.ecran_decision.listWidget_pile_transactions.item(
                        i).setTextColor(QColor("blue"))

        else:
            if transaction["buyer_id"] == self.le2mclt.uid:
                self.income_face = self.income_face - transaction["prix"] + 1
                self.income_pile -= transaction["prix"]
                self.income = self.get_current_income(self.income_pile,
                                                      self.income_face)

            if transaction["seller_id"] == self.le2mclt.uid:
                self.income_face = self.income_face + transaction["prix"] - 1
                self.income_pile += transaction["prix"]
                self.income = self.get_current_income(self.income_pile,
                                                      self.income_face)

            self.transactions_face.insert(0, transaction)
            self.ecran_decision.listWidget_face_transactions.clear()
            self.ecran_decision.listWidget_face_transactions.addItems(
                ["{:.2f}".format(t["prix"]) for t in self.transactions_face])
            for i, t in enumerate(self.transactions_face):
                if t["buyer_id"] == self.le2mclt.uid or t[
                    "seller_id"] == self.le2mclt.uid:
                    self.ecran_decision.listWidget_face_transactions.item(
                        i).setTextColor(QColor("blue"))

        # refresh the labels with the incomes
        self.ecran_decision.label_revenu_pile.setText(
            "{:.2f}".format(self.income_pile))
        self.ecran_decision.label_revenu_face.setText(
            "{:.2f}".format(self.income_face))
        self.ecran_decision.label_portefeuille.setText(
            "{:.2f}".format(self.income))

    def update_list(self, the_list_widget, the_list):
        """
        clear the list and add the items (transactions or offers)
        :param the_list_widget:
        :param the_list:
        :return:
        """
        the_list_widget.clear()
        the_list_widget.addItems(["{:.2f}".format(o["prix"]) for o in
                                  the_list])
        for i, o in enumerate(the_list):
            if o["player_id"] == self.le2mclt.uid:
                the_list_widget.item(i).setTextColor(QColor("blue"))

        self.ecran_decision.current_offer = None

    def get_current_income(self, income_pile, income_face):
        """
        return the income
        :param income_pile:
        :param income_face:
        :return:
        """
        esperance = np.mean([income_pile, income_face])
        variance = np.var([income_pile, income_face])
        try:
            income = esperance - self.aversion * (variance / esperance)
            return float("{:.2f}".format(income))
        except ZeroDivisionError:
            return float("{:.2f}".format(0))

    def get_simulated_income(self, offer, accept_or_send):
        """

        :param offer: offre either proposed or accepted
        :param accept_or_send: either accept or send
        :return: the tooltip text
        """
        if accept_or_send == "accept":
            logger.debug("set_tooltip for accept, offer: {}".format(offer))
            if offer["etat_monde"] == pms.PILE:
                if offer[
                    "achat_vente"] == pms.BUY:  # accepts a purchase offer so he makes a sell
                    inc_pile = self.income_pile + offer["prix"] - 1
                    inc_face = self.income_face + offer["prix"]
                else:
                    inc_pile = self.income_pile - offer["prix"] + 1
                    inc_face = self.income_face - offer["prix"]
            else:
                if offer[
                    "achat_vente"] == pms.BUY:  # accepts a purchase offer so he makes a sell
                    inc_face = self.income_face + offer["prix"] - 1
                    inc_pile = self.income_pile + offer["prix"]
                else:
                    inc_face = self.income_face - offer["prix"] + 1
                    inc_pile = self.income_pile - offer["prix"]

        else:
            logger.debug("set_tooltip for send, offer: {}".format(offer))
            if offer["etat_monde"] == pms.PILE:
                if offer["achat_vente"] == pms.BUY:  # makes a purchase offer
                    inc_pile = self.income_pile - offer["prix"] + 1
                    inc_face = self.income_face - offer["prix"]
                else:
                    inc_pile = self.income_pile + offer["prix"] - 1
                    inc_face = self.income_face + offer["prix"]
            else:
                if offer["achat_vente"] == pms.BUY:  # makes a purchase offer
                    inc_face = self.income_face - offer["prix"] + 1
                    inc_pile = self.income_pile - offer["prix"]
                else:
                    inc_face = self.income_face + offer["prix"] - 1
                    inc_pile = self.income_pile + offer["prix"]

        inc_simul = self.get_current_income(inc_pile, inc_face)
        return inc_pile, inc_face, inc_simul

    def remote_set_payoffs(self, in_euros, period_tiree):
        self._payoff_text = u"C'est la période {} qui a été tirée au sort pour " \
                            u"votre rémunération. A cette période vous avez " \
                            u"gagné {} euros.".format(period_tiree, in_euros)
