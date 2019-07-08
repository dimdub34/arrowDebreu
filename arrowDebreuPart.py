# -*- coding: utf-8 -*-

# built-in
import logging
from datetime import datetime
from twisted.spread import pb  # because some functions can be called remotely
from twisted.internet import defer
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime, \
    Boolean
import random

# le2m
from server.servbase import Base
from server.servparties import Partie
from util.utiltools import get_module_attributes

# arrowDebreu
import arrowDebreuParams as pms

logger = logging.getLogger("le2m.part")


class PartieAD(Partie, pb.Referenceable):
    __tablename__ = "partie_arrowDebreu"
    __mapper_args__ = {'polymorphic_identity': 'arrowDebreu'}
    partie_id = Column(Integer, ForeignKey('parties.id'), primary_key=True)
    repetitions = relationship('RepetitionsAD')
    AD_sequence = Column(Integer)
    AD_treatment = Column(Integer)
    AD_trial = Column(Boolean)
    AD_group = Column(String)
    AD_endowment_pile = Column(Float)
    AD_endowment_face = Column(Float)
    AD_initial_income = Column(Float)
    AD_aversion = Column(Float)
    AD_gain_ecus = Column(Float)
    AD_gain_euros = Column(Float)

    def __init__(self, le2mserv, joueur):
        super(PartieAD, self).__init__(
            nom="arrowDebreu", nom_court="AD",
            joueur=joueur, le2mserv=le2mserv)
        self.AD_gain_ecus = 0
        self.AD_gain_euros = 0

    @defer.inlineCallbacks
    def configure(self):
        logger.debug(u"{} Configure".format(self.joueur))
        self.AD_treatment = pms.TREATMENTS[pms.TREATMENT]["code"]
        self.AD_trial = pms.PARTIE_ESSAI
        # set the initial income depending on the position in the group
        self.AD_endowment_pile, self.AD_endowment_face = \
            pms.TREATMENTS[pms.TREATMENT]["endowment"][
                self.joueur.group.get_place_of_player(self)]
        self.AD_aversion = pms.TREATMENTS[pms.TREATMENT]["aversion"][
            self.joueur.group.get_place_of_player(self)]
        self.AD_income = yield (
            self.remote.callRemote("configure", get_module_attributes(pms),
                                   self, (self.AD_endowment_pile,
                                          self.AD_endowment_face),
                                   self.AD_aversion))
        self.joueur.info(u"Ok")

    @defer.inlineCallbacks
    def newperiod(self, period):
        """
        Create a new period and inform the remote
        If this is the first period then empty the historic
        :param periode:
        :return:
        """
        logger.debug(u"{} New Period".format(self.joueur))
        self.currentperiod = RepetitionsAD(period)
        self.le2mserv.gestionnaire_base.ajouter(self.currentperiod)
        self.repetitions.append(self.currentperiod)
        yield (
            self.remote.callRemote("newperiod", period, self.AD_endowment_pile,
                                   self.AD_endowment_face))
        logger.info(u"{} Ready for period {}".format(self.joueur, period))

    @defer.inlineCallbacks
    def display_decision(self):
        """
        Display the decision screen on the remote
        Get back the decision
        :return:
        """
        logger.debug(u"{} Decision".format(self.joueur))
        debut = datetime.now()
        self.currentperiod.AD_income_end_pile, \
        self.currentperiod.AD_income_end_face, \
        self.currentperiod.AD_periodpayoff = yield (
            self.remote.callRemote("display_decision"))
        self.currentperiod.AD_decisiontime = (datetime.now() - debut).seconds
        self.joueur.remove_waitmode()

    def compute_periodpayoff(self):
        """
        Compute the payoff for the period
        :return:
        """

        # fill the fields
        try:
            period_transactions = self.joueur.group.current_period.get_transactions()
            for t in period_transactions:
                if t["buyer_id"] == self.joueur.uid:
                    if t["etat_monde"] == pms.PILE:
                        self.currentperiod.AD_nb_buy_pile += 1
                        self.currentperiod.AD_sum_buy_pile += t["prix"]
                    else:
                        self.currentperiod.AD_nb_buy_face += 1
                        self.currentperiod.AD_sum_buy_face += t["prix"]

                elif t["seller_id"] == self.joueur.uid:
                    if t["etat_monde"] == pms.PILE:
                        self.currentperiod.AD_nb_sell_pile += 1
                        self.currentperiod.AD_sum_sell_pile += t["prix"]
                    else:
                        self.currentperiod.AD_nb_sell_face += 1
                        self.currentperiod.AD_sum_sell_face += t["prix"]
        except Exception as e:
            logger.warning("Error: {}".format(e.message))

        # cumulative payoff since the first period
        if self.currentperiod.AD_period == 1:
            self.currentperiod.AD_cumulativepayoff = \
                self.currentperiod.AD_periodpayoff
        else:
            previousperiod = self.periods[self.currentperiod.AD_period - 1]
            self.currentperiod.AD_cumulativepayoff = \
                previousperiod.AD_cumulativepayoff + \
                self.currentperiod.AD_periodpayoff

        # we store the period in the self.periodes dictionnary
        self.periods[self.currentperiod.AD_period] = self.currentperiod

        logger.debug(u"{} Period Payoff {}".format(
            self.joueur,
            self.currentperiod.AD_periodpayoff))

    @defer.inlineCallbacks
    def display_summary(self, *args):
        """
        Send a dictionary with the period content values to the remote.
        The remote creates the text and the history
        :param args:
        :return:
        """
        logger.debug(u"{} Summary".format(self.joueur))
        period_infos = self.currentperiod.todict()
        period_infos["AD_income_start_pile"] = self.AD_endowment_pile
        period_infos["AD_income_start_face"] = self.AD_endowment_face
        yield (self.remote.callRemote("display_summary", period_infos,
                                      self.joueur.group.current_period.get_transactions()))
        self.joueur.info("Ok")
        self.joueur.remove_waitmode()

    @defer.inlineCallbacks
    def compute_partpayoff(self):
        """
        Compute the payoff for the part and set it on the remote.
        The remote stores it and creates the corresponding text for display
        (if asked)
        :return:
        """
        logger.debug(u"{} Part Payoff".format(self.joueur))

        period_tiree = random.randint(1, pms.NOMBRE_PERIODES)
        self.AD_gain_ecus = self.periods[period_tiree].AD_periodpayoff
        self.AD_gain_euros = float(self.AD_gain_ecus) * float(
            pms.TAUX_CONVERSION)
        yield (self.remote.callRemote(
            "set_payoffs", self.AD_gain_euros, period_tiree))

        logger.info(u'{} Période tirée {} Payoff euros {:.2f}'.format(
            self.joueur, period_tiree, self.AD_gain_euros))

    @defer.inlineCallbacks
    def remote_add_offer(self, offer):
        """
        lorsque le sujet fait une offre
        on l'ajoute aux offres du groupe et on prévient tout le monde
        :param etat_monde
        :param achat_vente
        :param prix
        :return:
        """
        logger.debug("add_offer: {}".format(offer))
        yield (self.joueur.group.add_offer(self.joueur.uid, offer))

    @defer.inlineCallbacks
    def remote_accept_offer(self, offer):
        """
        lorsque le sujet accepte une offre existante
        on ajoute aux transactions du groupe et on prévient tout le monde
        :param offer
        :return:
        """
        new_offer = {
            "player_id": self.joueur.uid,
            "etat_monde": offer["etat_monde"],
            "achat_vente": pms.BUY if offer[
                                          "achat_vente"] == pms.SELL else pms.SELL,
            "prix": offer["prix"]
        }
        yield (self.joueur.group.add_offer(self.joueur.uid, new_offer))
        transaction = {
            "buyer_id": offer["player_id"] if offer[
                                                  "achat_vente"] == pms.BUY else
            new_offer["player_id"],
            "seller_id": offer["player_id"] if offer[
                                                   "achat_vente"] == pms.SELL else
            new_offer["player_id"],
            "etat_monde": offer["etat_monde"],
            "prix": offer["prix"]
        }
        yield (self.joueur.group.add_transaction(transaction, offer, new_offer))

    @defer.inlineCallbacks
    def remote_remove_offer(self, offer):
        """
        lorsque le sujet supprime une de ses offres
        :param etat_monde:
        :param achat_vente:
        :param prix:
        :return:
        """
        yield (self.joueur.group.remove_offer(offer))

    @defer.inlineCallbacks
    def inform_player_about_offer(self, offer):
        yield (self.remote.callRemote("add_offer", offer))

    @defer.inlineCallbacks
    def inform_player_about_transaction(self, transaction):
        yield (self.remote.callRemote("add_transaction", transaction))

    @defer.inlineCallbacks
    def inform_player_about_offer_removal(self, offer):
        yield (self.remote.callRemote("remove_offer", offer))


class RepetitionsAD(Base):
    __tablename__ = 'partie_arrowDebreu_repetitions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    partie_partie_id = Column(
        Integer,
        ForeignKey("partie_arrowDebreu.partie_id"))

    AD_period = Column(Integer)
    AD_period_start_time = Column(DateTime)
    AD_decisiontime = Column(Integer)
    AD_nb_buy_pile = Column(Integer, default=0)
    AD_nb_sell_pile = Column(Integer, default=0)
    AD_nb_buy_face = Column(Integer, default=0)
    AD_nb_sell_face = Column(Integer, default=0)
    AD_sum_buy_pile = Column(Float, default=0)
    AD_sum_sell_pile = Column(Float, default=0)
    AD_sum_buy_face = Column(Float, default=0)
    AD_sum_sell_face = Column(Float, default=0)
    AD_income_end_pile = Column(Float)
    AD_income_end_face = Column(Float)
    AD_periodpayoff = Column(Float)
    AD_cumulativepayoff = Column(Float)

    def __init__(self, period):
        self.AD_period_start_time = datetime.now()
        self.AD_period = period
        self.AD_decisiontime = 0
        self.AD_periodpayoff = 0
        self.AD_cumulativepayoff = 0

    def todict(self, joueur=None):
        temp = {c.name: getattr(self, c.name) for c in self.__table__.columns
                if "AD" in c.name}
        if joueur:
            temp["joueur"] = joueur
        return temp
