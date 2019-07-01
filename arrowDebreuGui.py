# -*- coding: utf-8 -*-
"""
This module contains the GUI
"""

# built-in
import sys
import logging
from PyQt4 import QtGui, QtCore
import random
from twisted.internet import defer
from datetime import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

# le2m
from util.utiltools import get_formated_time
from client.cltgui.cltguidialogs import GuiHistorique
from client.cltgui.cltguiwidgets import WTableview
from client.cltgui.cltguitablemodels import TableModelHistorique

# Arrow-debreu
import arrowDebreuParams as pms
from arrowDebreuGuiSrc import AD_Decision

logger = logging.getLogger("le2m.gui")
SIZE_HISTO = (1200, 500)


class GuiDecision(QtGui.QDialog, AD_Decision.Ui_Form):

    def __init__(self, remote, defered):
        super(GuiDecision, self).__init__(parent=remote.le2mclt.screen)
        self.setupUi(self)

        # ----------------------------------------------------------------------
        # variables
        # ----------------------------------------------------------------------
        self.remote = remote
        self._defered = defered
        self._automatique = self.remote.le2mclt.automatique
        self.current_time = pms.MARKET_TIME
        self.current_offer = None

        self._initUi()

        if self._automatique:
            self._timer_automatique = QtCore.QTimer()
            self._timer_automatique.setObjectName("Timer automatique")
            self._timer_automatique.timeout.connect(self.play_automatically)
            self._timer_automatique.start(random.randint(2000, 7000))

    def _initUi(self):
        self.setWindowTitle(u"Marché")
        self.label_period.setText(
            u"Période {}".format(self.remote.current_period))
        self.label_timer.setText(get_formated_time(pms.MARKET_TIME))
        self.textEdit_explication.setText(
            u"Votre revenu si pile est {} euros et votre revenu si face est {} "
            u"euros. Votre paramètre alpha est {}. La valeur de votre "
            u"portefeuille est {} euros.".format(
                self.remote.income_pile, self.remote.income_face,
                self.remote.aversion, self.remote.income
            )
        )
        self.label_revenu_pile.setText(
            "{:.2f}".format(self.remote.income_pile))
        self.label_revenu_face.setText(
            "{:.2f}".format(self.remote.income_face))
        self.label_txt_portefeuille.setText("Valeur de votre portefeuille")
        self.label_portefeuille.setText("{:.2f}".format(self.remote.income))

        # ----------------------------------------------------------------------
        # connexions doublespinbox
        # ----------------------------------------------------------------------
        self.doubleSpinBox_pile_offre_achat.valueChanged["double"].connect(
            self.set_tooltip)
        self.doubleSpinBox_pile_offre_vente.valueChanged["double"].connect(
            self.set_tooltip)
        self.doubleSpinBox_face_offre_achat.valueChanged["double"].connect(
            self.set_tooltip)
        self.doubleSpinBox_face_offre_vente.valueChanged["double"].connect(
            self.set_tooltip)

        # ----------------------------------------------------------------------
        # connexions sélection offre
        # ----------------------------------------------------------------------
        self.listWidget_pile_offre_achat.itemClicked.connect(
            self.set_current_offer)
        self.listWidget_pile_offre_vente.itemClicked.connect(
            self.set_current_offer)
        self.listWidget_face_offre_achat.itemClicked.connect(
            self.set_current_offer)
        self.listWidget_face_offre_vente.itemClicked.connect(
            self.set_current_offer)

        # ----------------------------------------------------------------------
        # connexions boutons accepter
        # ----------------------------------------------------------------------
        self.pushButton_pile_offre_achat_accepter.clicked.connect(
            lambda _: self.accept_offer())
        self.pushButton_pile_offre_vente_accepter.clicked.connect(
            lambda _: self.accept_offer())
        self.pushButton_face_offre_achat_accepter.clicked.connect(
            lambda _: self.accept_offer())
        self.pushButton_face_offre_vente_accepter.clicked.connect(
            lambda _: self.accept_offer())

        # ----------------------------------------------------------------------
        # connexions boutons envoyer
        # ----------------------------------------------------------------------
        self.pushButton_pile_offre_achat_envoyer.clicked.connect(
            lambda _: self.send_offer(self.pushButton_pile_offre_achat_envoyer))
        self.pushButton_pile_offre_vente_envoyer.clicked.connect(
            lambda _: self.send_offer(self.pushButton_pile_offre_vente_envoyer))
        self.pushButton_face_offre_achat_envoyer.clicked.connect(
            lambda _: self.send_offer(self.pushButton_face_offre_achat_envoyer))
        self.pushButton_face_offre_vente_envoyer.clicked.connect(
            lambda _: self.send_offer(self.pushButton_face_offre_vente_envoyer))

        # ----------------------------------------------------------------------
        # connexions boutons supprimer
        # ----------------------------------------------------------------------
        self.pushButton_pile_offre_achat_supprimer.clicked.connect(
            lambda _: self.remove_offer())
        self.pushButton_pile_offre_vente_supprimer.clicked.connect(
            lambda _: self.remove_offer())
        self.pushButton_face_offre_achat_supprimer.clicked.connect(
            lambda _: self.remove_offer())
        self.pushButton_face_offre_vente_supprimer.clicked.connect(
            lambda _: self.remove_offer())

        # ----------------------------------------------------------------------
        # compte à rebours
        # ----------------------------------------------------------------------
        self.timer_rebours = QtCore.QTimer()
        self.timer_rebours.timeout.connect(self.display_timer_rebours)
        self.timer_rebours.start(1000)

    @QtCore.pyqtSlot()
    def display_timer_rebours(self):
        minutes = self.current_time.minute
        seconds = self.current_time.second - 1
        if seconds < 0:
            seconds = 59
            minutes = self.current_time.minute - 1
        self.current_time = time(0, minutes, seconds)
        self.label_timer.setText(get_formated_time(self.current_time))
        if self.current_time.minute == 0 and self.current_time.second == 0:
            self.timer_rebours.stop()
            self._accept()

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def set_current_offer(self):
        """
        - appelée par les listes, quand le sujet click sur un des items
        - place l'offre sélectionnée comme current_offer
        - cette current_offer pourra être ensuite soit acceptée soit supprimée
        :return:
        """
        list_source = self.sender()
        logger.debug(self.sender().objectName())

        if list_source == self.listWidget_pile_offre_achat:
            try:
                self.current_offer = self.remote.offers_pile_achat[
                    list_source.currentRow()]
                self.pushButton_pile_offre_achat_accepter.setToolTip(
                    "Revenu: {}".format(
                        self.remote.get_simulated_income(self.current_offer,
                                                         "accept")[2]))
            except IndexError:
                pass

        elif list_source == self.listWidget_pile_offre_vente:
            try:
                self.current_offer = self.remote.offers_pile_vente[
                    list_source.currentRow()]
                self.pushButton_pile_offre_vente_accepter.setToolTip(
                    "Revenu: {}".format(
                        self.remote.get_simulated_income(self.current_offer,
                                                         "accept")[2]))
            except IndexError:
                pass

        elif list_source == self.listWidget_face_offre_achat:
            try:
                self.current_offer = self.remote.offers_face_achat[
                    list_source.currentRow()]
                self.pushButton_face_offre_achat_accepter.setToolTip(
                    "Revenu: {}".format(
                        self.remote.get_simulated_income(self.current_offer,
                                                         "accept")[2]))
            except IndexError:
                pass

        elif list_source == self.listWidget_face_offre_vente:
            try:
                self.current_offer = self.remote.offers_face_vente[
                    list_source.currentRow()]
                self.pushButton_face_offre_vente_accepter.setToolTip(
                    "Revenu: {}".format(
                        self.remote.get_simulated_income(self.current_offer,
                                                         "accept")[2]))
            except IndexError:
                pass

        logger.debug("Current offer: {}".format(self.current_offer))

    @QtCore.pyqtSlot()
    @defer.inlineCallbacks
    def accept_offer(self):
        if self.current_offer is None or self.current_offer[
            "player_id"] == self.remote.le2mclt.uid:
            return
        else:
            inc_left, inc_right, inc_simul = self.remote.get_simulated_income(
                self.current_offer, "accept")
            if inc_left >= 0 and inc_right >= 0 and inc_simul >= 0:
                yield (self.remote.player_on_srv.callRemote("accept_offer",
                                                            self.current_offer))
            else:
                return

    @QtCore.pyqtSlot(QtGui.QPushButton)
    @defer.inlineCallbacks
    def send_offer(self, button_source):
        """
        Envoie l'offre au serveur
        :return:
        """
        logger.debug("btn source: {}".format(button_source.objectName()))

        def test_incomes(offer):
            inc_left, inc_right, inc_simul = self.remote.get_simulated_income(
                offer, "send")
            return inc_left >= 0 and inc_right >= 0 and inc_simul >= 0

        if button_source == self.pushButton_pile_offre_achat_envoyer:
            offer = {
                "etat_monde": pms.PILE,
                "achat_vente": pms.BUY,
                "prix": self.doubleSpinBox_pile_offre_achat.value(),
            }
            if test_incomes(offer):
                self.doubleSpinBox_pile_offre_achat.setValue(0)
                yield (self.remote.player_on_srv.callRemote("add_offer", offer))
            else:
                return

        elif button_source == self.pushButton_pile_offre_vente_envoyer:
            offer = {
                "etat_monde": pms.PILE,
                "achat_vente": pms.SELL,
                "prix": self.doubleSpinBox_pile_offre_vente.value()
            }
            if test_incomes(offer):
                self.doubleSpinBox_pile_offre_vente.setValue(0)
                yield (self.remote.player_on_srv.callRemote("add_offer", offer))
            else:
                return

        elif button_source == self.pushButton_face_offre_achat_envoyer:
            offer = {
                "etat_monde": pms.FACE,
                "achat_vente": pms.BUY,
                "prix": self.doubleSpinBox_face_offre_achat.value()
            }
            if test_incomes(offer):
                self.doubleSpinBox_face_offre_achat.setValue(0)
                yield (self.remote.player_on_srv.callRemote("add_offer", offer))
            else:
                return

        elif button_source == self.pushButton_face_offre_vente_envoyer:
            offer = {
                "etat_monde": pms.FACE,
                "achat_vente": pms.SELL,
                "prix": self.doubleSpinBox_face_offre_vente.value()
            }
            if test_incomes(offer):
                self.doubleSpinBox_face_offre_vente.setValue(0)
                yield (self.remote.player_on_srv.callRemote("add_offer", offer))
            else:
                return

    @QtCore.pyqtSlot()
    @defer.inlineCallbacks
    def remove_offer(self):
        if self.current_offer is None or self.current_offer[
            "player_id"] != self.remote.le2mclt.uid:
            return

        yield (self.remote.player_on_srv.callRemote("remove_offer",
                                                    self.current_offer))
        self.current_offer = None

    @QtCore.pyqtSlot(float)
    def set_tooltip(self, value):
        source = self.sender()

        if source == self.doubleSpinBox_pile_offre_achat:
            offer = {"etat_monde": pms.PILE, "achat_vente": pms.BUY,
                     "prix": value}
            self.pushButton_pile_offre_achat_envoyer.setToolTip(
                "Revenu: {}".format(
                    self.remote.get_simulated_income(offer, "send")[2]))

        elif source == self.doubleSpinBox_pile_offre_vente:
            offer = {"etat_monde": pms.PILE, "achat_vente": pms.SELL,
                     "prix": value}
            self.pushButton_pile_offre_vente_envoyer.setToolTip(
                "Revenu: {}".format(
                    self.remote.get_simulated_income(offer, "send")[2]))

        elif source == self.doubleSpinBox_face_offre_achat:
            offer = {"etat_monde": pms.FACE, "achat_vente": pms.BUY,
                     "prix": value}
            self.pushButton_face_offre_achat_envoyer.setToolTip(
                "Revenu: {}".format(
                    self.remote.get_simulated_income(offer, "send")[2]))

        elif source == self.doubleSpinBox_face_offre_vente:
            offer = {"etat_monde": pms.FACE, "achat_vente": pms.SELL,
                     "prix": value}
            self.pushButton_face_offre_vente_envoyer.setToolTip(
                "Revenu: {}".format(
                    self.remote.get_simulated_income(offer, "send")[2]))

    @QtCore.pyqtSlot()
    def play_automatically(self):
        etat_monde = random.choice([pms.PILE, pms.FACE])
        achat_vente = random.choice([pms.BUY, pms.SELL])
        accept_send = "accept" if random.randint(0, 1) == 0 else "send"

        if etat_monde == pms.PILE:
            if achat_vente == pms.BUY:
                if accept_send == "accept":
                    if self.remote.offers_pile_achat:
                        try:
                            selected = random.randint(0, len(
                                self.remote.offers_pile_achat))
                            item = self.listWidget_pile_offre_achat.item(
                                selected)
                            item.setSelected(True)
                            self.listWidget_pile_offre_achat.itemClicked.emit(
                                item)
                            self.pushButton_pile_offre_achat_accepter.click()
                        except AttributeError:
                            pass

                else:
                    prix = random.choice(np.arange(0.01, 1.01, 0.01))
                    self.doubleSpinBox_pile_offre_achat.setValue(prix)
                    self.pushButton_pile_offre_achat_envoyer.click()

            else:
                if accept_send == "accept":
                    if self.remote.offers_pile_vente:
                        try:
                            selected = random.randint(0, len(
                                self.remote.offers_pile_vente))
                            item = self.listWidget_pile_offre_vente.item(
                                selected)
                            item.setSelected(True)
                            self.listWidget_pile_offre_achat.itemClicked.emit(
                                item)
                            self.pushButton_pile_offre_vente_accepter.click()
                        except AttributeError:
                            pass

                else:
                    prix = random.choice(np.arange(0.01, 1.01, 0.01))
                    self.doubleSpinBox_pile_offre_vente.setValue(prix)
                    self.pushButton_pile_offre_vente_envoyer.click()

        else:
            if achat_vente == pms.BUY:
                if accept_send == "accept":
                    if self.remote.offers_face_achat:
                        try:
                            selected = random.randint(0, len(
                                self.remote.offers_face_achat))
                            item = self.listWidget_face_offre_achat.item(
                                selected)
                            item.setSelected(True)
                            self.listWidget_face_offre_achat.itemClicked.emit(
                                item)
                            self.pushButton_face_offre_achat_accepter.click()
                        except AttributeError:
                            pass

                else:
                    prix = random.choice(np.arange(0, 1.01, 0.01))
                    self.doubleSpinBox_face_offre_achat.setValue(prix)
                    self.pushButton_face_offre_achat_envoyer.click()

            else:
                if accept_send == "accept":
                    if self.remote.offers_face_vente:
                        try:
                            selected = random.randint(0, len(
                                self.remote.offers_face_vente))
                            item = self.listWidget_face_offre_vente.item(
                                selected)
                            item.setSelected(True)
                            self.listWidget_face_offre_vente.itemClicked.emit(
                                item)
                            self.pushButton_face_offre_vente_accepter.click()
                        except AttributeError:
                            pass

                else:
                    prix = random.choice(np.arange(0.01, 1.01, 0.01))
                    self.doubleSpinBox_face_offre_vente.setValue(prix)
                    self.pushButton_face_offre_vente_envoyer.click()

    def reject(self):
        pass

    def _accept(self):
        try:
            self._timer_automatique.stop()
        except AttributeError:
            pass
        logger.info(u"Ok")
        self.accept()
        self._defered.callback((self.remote.income_pile,
                                self.remote.income_face, self.remote.income))


class GuiRecapitulatif(QtGui.QDialog):

    def __init__(self, remote, defered, summary_text, group_transactions):
        super(GuiRecapitulatif, self).__init__(remote.le2mclt.screen)
        self.setWindowTitle(u"Récapitulatif")

        self._remote = remote
        self._defered = defered

        layout = QtGui.QVBoxLayout(self)

        # period label and history button --------------------------------------
        self.ecran_historique = GuiHistorique(self, self._remote.histo,
                                              size=SIZE_HISTO)

        label_period = QtGui.QLabel(
            u"Période {}".format(self._remote.current_period))
        button_history = QtGui.QPushButton("Historique")
        button_history.clicked.connect(self.ecran_historique.show)

        layout_period = QtGui.QHBoxLayout()
        layout_period.addWidget(label_period, 0, QtCore.Qt.AlignLeft)
        layout_period.addWidget(button_history, 0, QtCore.Qt.AlignRight)
        layout.addLayout(layout_period)

        # explanation zone -----------------------------------------------------
        self.explication = QtGui.QTextEdit()
        self.explication.setFixedSize(SIZE_HISTO[0], 80)
        self.explication.setText(summary_text)
        layout.addWidget(self.explication, 0, QtCore.Qt.AlignHCenter)

        # # history table ------------------------------------------------------
        histo_recap = [self._remote.histo[0], self._remote.histo[-1]]
        self.tablemodel = TableModelHistorique(histo_recap)
        self.widtableview = WTableview(parent=self, tablemodel=self.tablemodel,
                                       size=(SIZE_HISTO[0], 100))
        self.widtableview.ui.tableView.verticalHeader().setResizeMode(
            QtGui.QHeaderView.Stretch)
        layout.addWidget(self.widtableview)

        # transactions ---------------------------------------------------------
        try:
            prix_max = max([t["prix"] for t in group_transactions])
        except ValueError:  # if no transactions
            prix_max = 1

        widget_graphiques = QtGui.QWidget()
        widget_graphiques.setFixedWidth(SIZE_HISTO[0])
        transactions_layout = QtGui.QGridLayout(widget_graphiques)
        layout.addWidget(widget_graphiques, 0, QtCore.Qt.AlignHCenter)

        # pile
        transactions_pile = [g for g in group_transactions if
                             g["etat_monde"] == pms.PILE]

        pile_label = QtGui.QLabel("Transactions Pile")
        pile_label.setStyleSheet("font-weight: bold;")
        transactions_layout.addWidget(pile_label, 0, 0)
        self._pile_transactions_graph = GraphicalZone(
            transactions_pile, prix_max, "*")
        transactions_layout.addWidget(self._pile_transactions_graph, 1, 0)

        # face
        transactions_face = [g for g in group_transactions if
                             g["etat_monde"] == pms.FACE]

        face_label = QtGui.QLabel("Transactions Face")
        face_label.setStyleSheet("font-weight: bold;")
        transactions_layout.addWidget(face_label, 0, 1)
        self._face_transactions_graph = GraphicalZone(
            transactions_face, prix_max, "*")
        transactions_layout.addWidget(self._face_transactions_graph, 1, 1)

        # button ---------------------------------------------------------------
        buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok)
        buttons.accepted.connect(self._accept)
        layout.addWidget(buttons, 0, QtCore.Qt.AlignRight)

        # # automatique
        if self._remote.le2mclt.automatique:
            self._timer_automatique = QtCore.QTimer()
            self._timer_automatique.timeout.connect(
                buttons.button(QtGui.QDialogButtonBox.Ok).click)
            self._timer_automatique.start(7000)

    def _accept(self):
        try:
            self._timer_automatique.stop()
        except AttributeError:
            pass
        try:
            self._compte_rebours.stop()
        except AttributeError:
            pass
        logger.info(u"callback: Ok summary")
        self._defered.callback(1)
        self.accept()

    def reject(self):
        pass


class DConfigure(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)

        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

        form = QtGui.QFormLayout()
        layout.addLayout(form)

        # treatment
        self._combo_treatment = QtGui.QComboBox()
        self._combo_treatment.addItems(
            [v for k, v in sorted(pms.TREATMENTS_NAMES.items())])
        self._combo_treatment.setCurrentIndex(pms.TREATMENT)
        form.addRow(QtGui.QLabel(u"Traitement"), self._combo_treatment)

        # nombre de périodes
        self._spin_periods = QtGui.QSpinBox()
        self._spin_periods.setMinimum(0)
        self._spin_periods.setMaximum(100)
        self._spin_periods.setSingleStep(1)
        self._spin_periods.setValue(pms.NOMBRE_PERIODES)
        self._spin_periods.setButtonSymbols(QtGui.QSpinBox.NoButtons)
        self._spin_periods.setMaximumWidth(50)
        form.addRow(QtGui.QLabel(u"Nombre de périodes"), self._spin_periods)

        # taille groupes
        self._spin_groups = QtGui.QSpinBox()
        self._spin_groups.setMinimum(0)
        self._spin_groups.setMaximum(100)
        self._spin_groups.setSingleStep(1)
        self._spin_groups.setValue(pms.TAILLE_GROUPES)
        self._spin_groups.setButtonSymbols(QtGui.QSpinBox.NoButtons)
        self._spin_groups.setMaximumWidth(50)
        form.addRow(QtGui.QLabel(u"Taille des groupes"), self._spin_groups)

        # market duration
        self._timeEdit_market = QtGui.QTimeEdit()
        self._timeEdit_market.setDisplayFormat("hh:mm:ss")
        self._timeEdit_market.setTime(QtCore.QTime(pms.MARKET_TIME.hour,
                                                   pms.MARKET_TIME.minute,
                                                   pms.MARKET_TIME.second))
        self._timeEdit_market.setMaximumWidth(100)
        form.addRow(u"Temps de marché", self._timeEdit_market)

        # partie d'essai
        self._checkbox_essai = QtGui.QCheckBox()
        self._checkbox_essai.setChecked(pms.PARTIE_ESSAI)
        form.addRow(QtGui.QLabel(u"Partie d'essai"), self._checkbox_essai)

        button = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        button.accepted.connect(self._accept)
        button.rejected.connect(self.reject)
        layout.addWidget(button)

        self.setWindowTitle(u"Configurer")
        self.adjustSize()
        self.setFixedSize(self.size())

    def _accept(self):
        pms.TREATMENT = self._combo_treatment.currentIndex()
        pms.PARTIE_ESSAI = self._checkbox_essai.isChecked()
        pms.NOMBRE_PERIODES = self._spin_periods.value()
        pms.TAILLE_GROUPES = self._spin_groups.value()
        pms.MARKET_TIME = self._timeEdit_market.time().toPyTime()
        self.accept()


class GraphicalZone(QtGui.QWidget):
    def __init__(self, transactions, max_price, marker):
        QtGui.QWidget.__init__(self)

        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

        figure = plt.Figure(figsize=(6, 3), facecolor="white")
        canvas = FigureCanvas(figure)
        canvas.setFixedSize(550, 300)
        layout.addWidget(canvas)

        graph = figure.add_subplot(111)
        if transactions:
            graph.plot([t["seconds_from_start"] for t in transactions],
                       [t["prix"] for t in transactions], color="k", ls="",
                       marker=marker)
        graph.set_xlabel("Temps (secondes)")
        graph.set_xlim(-5,
                       pms.MARKET_TIME.minute * 60 + pms.MARKET_TIME.second + 5)
        graph.set_xticks(
            range(0,
                  pms.MARKET_TIME.minute * 60 + pms.MARKET_TIME.second + 1, 10))
        graph.set_xticklabels(
            ["{}".format(i) if i % 30 == 0 else "" for i in
             range(0, pms.MARKET_TIME.minute * 60 + pms.MARKET_TIME.second + 1,
                   10)])
        graph.set_ylabel("Prix")
        graph.set_ylim(-0.25, max_price + 0.25)
        graph.set_yticks(np.arange(0, max_price + 0.1, 0.25))
        graph.grid(ls="--")

        figure.tight_layout()
