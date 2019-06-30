# built-in
from server.servbase import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime
import logging
from PyQt4.QtCore import QTimer
from twisted.internet import defer
from datetime import datetime

# le2m
from util.utiltwisted import forAll
from server.srvgroup import Group

# Arrow Debreu
import arrowDebreuParams as pms

logger = logging.getLogger("le2m.group")


class ADGroup(Group, Base):
    __tablename__ = "ADGroup"
    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String)
    session_id = Column(Integer)
    AD_sequence = Column(Integer)
    AD_treatment = Column(Integer)
    AD_periods = relationship("ADGroupPeriods")

    def __init__(self, le2msrv, group_id, players, num_sequence):
        Group.__init__(self, le2msrv, group_id, players)
        self.AD_sequence = num_sequence
        self.current_period = None

    def new_period(self, period):
        self.current_period = ADGroupPeriods(self.uid, period)
        self.le2msrv.gestionnaire_base.ajouter(self.current_period)

    @defer.inlineCallbacks
    def add_offer(self, player_id, offer_info):
        offer = ADGroupOffer(player_id, offer_info, (
                datetime.now() - self.current_period.start_time).total_seconds())
        self.le2msrv.gestionnaire_base.ajouter(offer)
        self.current_period.AD_offers.append(offer)
        self.le2msrv.gestionnaire_graphique.infoclt(
            "{} - {}".format(self, offer))

        yield (forAll(self.get_players(), "inform_player_about_offer",
                      offer.to_dict()))

    @defer.inlineCallbacks
    def add_transaction(self, transaction_info, offer_1, offer_2):
        transaction = ADGroupTransaction(transaction_info, (
                datetime.now() - self.current_period.start_time).total_seconds())
        self.le2msrv.gestionnaire_base.ajouter(transaction)
        self.current_period.AD_transactions.append(transaction)
        self.le2msrv.gestionnaire_graphique.infoclt(
            "{} - {}".format(self, transaction))

        yield (
            forAll(self.get_players(), "inform_player_about_transaction",
                   transaction.to_dict()))
        yield self.remove_offer(offer_1)
        yield self.remove_offer(offer_2)
        logger.debug("add_transaction: {}".format(transaction))

    @defer.inlineCallbacks
    def remove_offer(self, offer):
        yield (forAll(self.get_players(),
                      "inform_player_about_offer_removal", offer))


class ADGroupPeriods(Base):
    __tablename__ = "ADGroupPeriods"
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey("ADGroup.id"))
    period = Column(Integer)
    start_time = Column(DateTime)
    AD_offers = relationship("ADGroupOffer")
    AD_transactions = relationship("ADGroupTransaction")

    def __init__(self, group_id, period):
        self.group_id = group_id
        self.period = period
        self.start_time = datetime.now()

    def get_transactions(self):
        transactions = list()
        for t in self.AD_transactions:
            transactions.append(t.to_dict())
        return transactions


class ADGroupOffer(Base):
    __tablename__ = "ADGroupOffer"
    id = Column(Integer, primary_key=True, autoincrement=True)
    period_id = Column(Integer, ForeignKey("ADGroupPeriods.id"))
    player_id = Column(String)
    etat_monde = Column(Integer)
    achat_vente = Column(Integer)
    prix = Column(Float)
    seconds_from_start = Column(Float)

    def __init__(self, player_id, offer, seconds_from_start):
        self.player_id = player_id
        self.etat_monde = offer["etat_monde"]
        self.achat_vente = offer["achat_vente"]
        self.prix = offer["prix"]
        self.seconds_from_start = seconds_from_start

    def to_dict(self):
        return {
            "id": self.id,
            "player_id": self.player_id,
            "etat_monde": self.etat_monde,
            "achat_vente": self.achat_vente,
            "prix": self.prix,
            "seconds_from_start": self.seconds_from_start
        }

    def __str__(self):
        return "{} - {} - {} - {}".format(
            self.player_id,
            "Pile" if self.etat_monde == pms.PILE else "Face",
            "Achat" if self.achat_vente == pms.BUY else "Vente",
            self.prix)


class ADGroupTransaction(Base):
    __tablename__ = "ADGroupTransaction"
    id = Column(Integer, primary_key=True, autoincrement=True)
    period_id = Column(Integer, ForeignKey("ADGroupPeriods.id"))
    buyer_id = Column(String)
    seller_id = Column(String)
    etat_monde = Column(Integer)
    prix = Column(Float)
    seconds_from_start = Column(Float)

    def __init__(self, transaction, seconds_from_start):
        self.buyer_id = transaction["buyer_id"]
        self.seller_id = transaction["seller_id"]
        self.etat_monde = transaction["etat_monde"]
        self.prix = transaction["prix"]
        self.seconds_from_start = seconds_from_start

    def to_dict(self):
        return {
            "id": self.id,
            "buyer_id": self.buyer_id,
            "seller_id": self.seller_id,
            "etat_monde": self.etat_monde,
            "prix": self.prix,
            "seconds_from_start": self.seconds_from_start
        }

    def __str__(self):
        return "{} - {} - {} - {}".format(
            self.buyer_id,
            self.seller_id,
            "Pile" if self.etat_monde == pms.PILE else "Face",
            self.prix)
