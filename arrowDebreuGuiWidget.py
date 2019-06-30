# -*- coding: utf-8 -*-

"""=============================================================================

This module contains the widgets

============================================================================="""

# built-in
import sys
from PyQt4.QtGui import *
from PyQt4 import QtCore
import random
import logging

# le2m
from client.cltgui.cltguiwidgets import WDoubleSpinBox

# projet
import arrowDebreuParams as pms


logger = logging.getLogger("le2m")


class MyStandardItem(QStandardItem):
    """
    Surcharge du standard item pour la fonction sort de la liste qui
    accueillera ces items
    """
    def __init__(self, value):
        QStandardItem.__init__(self)
        self.__value = value
        self.setText(str(value))

    def __lt__(self, other):
        return other < self.__value

    def value(self):
        return self.__value


class OfferZone(QWidget):
    """
    Zone graphique composée d'une liste (pour les offres),
     d'une zone pour saisir une offre (avec un buton d'envoi) et d'une
     zone en dessous pour accepter une offre existante et supprimer
     son offre
    """

    # font_normale = QFont()
    # font_bold = QFont()
    # font_bold.setWeight(QFont.Bold)
    # font_bold.setPointSize(font_normale.pointSize() + 1)
    offer_selected = QtCore.pyqtSignal(dict)

    def __init__(self, BUY_or_SELL, zone_size=(400, 300)):
        QWidget.__init__(self)

        self.current_offer = None
        self._buy_or_sell = BUY_or_SELL
        self._offers = {}

        self.layout_main = QVBoxLayout()
        self.setLayout(self.layout_main)

        self.label = QLabel()
        if self._buy_or_sell == pms.BUY:
            self.label.setText("Offres d'achat")
        else:
            self.label.setText("Offres de vente")
        self.layout_main.addWidget(self.label)

        self.list_view = QListView()
        self.model = QStandardItemModel()
        self.list_view.setModel(self.model)
        self.layout_main.addWidget(self.list_view)

        self.layout_offer = QHBoxLayout()
        self.layout_main.addLayout(self.layout_offer)
        if self._buy_or_sell == pms.BUY:
            self.layout_offer.addWidget(
                QLabel("Faire une offre d'achat"))
        else:
            self.layout_offer.addWidget(
                QLabel("Faire une offre de vente"))
        self.spin_offer = WDoubleSpinBox()
        self.layout_offer.addWidget(self.spin_offer)
        self.pushbutton_send = QPushButton("Envoyer")
        self.pushbutton_send.setFixedWidth(100)
        self.pushbutton_send.setToolTip(
            u"Faire une offre ou remplacer l'offre actuelle")
        self.layout_offer.addWidget(self.pushbutton_send)
        self.layout_offer.addSpacerItem(
            QSpacerItem(20, 20, QSizePolicy.Expanding,
                              QSizePolicy.Minimum))

        self.layout_accept_remove = QHBoxLayout()
        self.layout_main.addLayout(self.layout_accept_remove)
        self.pushbutton_accept = QPushButton(u"Accepter l'offre")
        self.pushbutton_accept.setFixedWidth(160)
        self.pushbutton_accept.setToolTip(
            u"Sélectionner une offre et cliquer sur ce bouton pour l'accepter")
        self.layout_accept_remove.addWidget(self.pushbutton_accept)

        self.pushbutton_remove = QPushButton("Supprimer mon offre")
        self.pushbutton_remove.setFixedWidth(160)
        self.pushbutton_remove.setToolTip(
            u"Si vous avez une offre en cours cliquez sur ce bouton pour la "
            u"supprimer")
        self.layout_accept_remove.addWidget(
            self.pushbutton_remove)
        self.layout_accept_remove.addSpacerItem(
            QSpacerItem(20, 20, QSizePolicy.Expanding,
                              QSizePolicy.Minimum))

        # connections
        self.list_view.clicked.connect(self._set_current_offer)

        self.setFixedSize(*zone_size)

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def _set_current_offer(self, index):
        current_item = self.model.item(index.row(), 0)
        for k, v in self._offers.viewitems():
            if v[0] == current_item:
                self.current_offer = v[1]
                break
        self.offer_selected.emit(self.current_offer.copy())

    def add_offer(self, sender, offer, color):
        # remove the current offer
        self.remove_offer(sender)
        # add the new offer
        item = MyStandardItem(offer["MRI_offer_price"])
        item.setForeground(QColor(color))
        self.model.appendRow(item)
        self._sort()
        self._offers[sender] = (item, offer)

    def remove_offer(self, sender):
        """
        Remove the offer from the list
        :param sender:
        :return:
        """
        offer_item = self._offers.pop(sender, None)
        if offer_item is not None:
            for row in range(self.model.rowCount()):
                if self.model.item(row, 0) == offer_item[0]:
                    self.model.removeRow(row)
                    break
            self._sort()

    def _sort(self):
        if self._buy_or_sell == pms.BUY:
            self.model.sort(0, QtCore.Qt.DescendingOrder)
        else:
            self.model.sort(0, QtCore.Qt.AscendingOrder)

        for i in range(self.model.rowCount()):
            self.model.item(i).setFont(
                self.font_bold if i == 0 else self.font_normale)
        self.current_offer = None

    def clear(self):
        """
        we clear both the model and the dict that stores the offers
        :return:
        """
        self.model.clear()
        self._offers.clear()

    def exists_offer(self, price, sender):
        """
        We check whether there exists an offer with that price.
        If it does return the offer. If it doesn't return False
        :param sender:
        :param price:
        :return:
        """
        existing_offers = list()
        for k, v in self._offers.viewitems():
            if v[1]["MRI_offer_price"] == price and \
                            v[1]["MRI_offer_sender"] != sender:
                existing_offer = v[1]
                logger.debug(u"exists_offer: {}".format(existing_offer))
                existing_offers.append(existing_offer)
        if existing_offers:
            existing_offers.sort(key=lambda x: x["MRI_offer_time"])
            return existing_offers[0]
        return False

    def get_sender_offer(self, sender):
        try:
            return self._offers[sender][1]
        except KeyError:
            return None

    def select_an_item(self):
        if self._offers:
            random_item = random.choice([v[0] for v in self._offers.viewvalues()])
            index = self.model.indexFromItem(random_item)
            self.list_view.setCurrentIndex(index)
            self._set_current_offer(index)


class TransactionZone(QWidget):
    """
    Zone de transaction.
    """
    def __init__(self, zone_size=(400, 200)):
        QWidget.__init__(self)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.label = QLabel("Transactions")
        self.layout.addWidget(self.label)
        self.list = QListView()
        self.layout.addWidget(self.list)
        self.model = QStandardItemModel()
        self.list.setModel(self.model)

        self.setFixedSize(*zone_size)

    def add_transaction(self, price, buyer_seller, color):
        if buyer_seller == pms.BUYER:
            item = MyStandardItem(str(price) + " (achat)")
        elif buyer_seller == pms.SELLER:
            item = MyStandardItem(str(price) + " (vente)")
        else:
            item = MyStandardItem(price)
        item.setForeground(QColor(color))
        self.model.insertRow(0, item)

    def clear(self):
        self.model.clear()


if __name__ == "__main__":
    app = QApplication([])
    # wid = OfferZone(pms.SELL)
    wid = TransactionZone()
    wid.show()
    sys.exit(app.exec_())