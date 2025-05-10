"""
Main window to launch JsonViewer
"""

import ast
import importlib.resources
import json
import os
import sys

from Qt import QtWidgets, QtCore, QtGui
from Qt import _loadUi

import jsonEditor.qjsonmodel
import jsonEditor.qjsonnode
import jsonEditor.qjsonview
from jsonEditor.codeEditor.highlighter.jsonHighlight import JsonHighlighter




class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, app, origin_json):
        self.app = app
        super(MainWindow, self).__init__()
        self.result = None
        UI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui', 'jsonEditor.ui')
        _loadUi(UI_PATH, self)

        self.ui_tree_view = jsonEditor.qjsonview.QJsonView()
        self.ui_tree_view.setStyleSheet('QWidget{font: 12pt;}')
        # self.ui_tree_view.setStyleSheet('QWidget{font: 10pt "Bahnschrift";}')
        self.ui_grid_layout.addWidget(self.ui_tree_view, 1, 0)

        root = jsonEditor.qjsonnode.QJsonNode.load(json.loads(origin_json))

        self._model = jsonEditor.qjsonmodel.QJsonModel(root, self)

        # proxy model
        self._proxyModel = QtCore.QSortFilterProxyModel(self)
        self._proxyModel.setSourceModel(self._model)
        self._proxyModel.setDynamicSortFilter(False)
        self._proxyModel.setSortRole(jsonEditor.qjsonmodel.QJsonModel.sortRole)
        self._proxyModel.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self._proxyModel.setFilterRole(jsonEditor.qjsonmodel.QJsonModel.filterRole)
        self._proxyModel.setFilterKeyColumn(0)

        self.ui_tree_view.setModel(self._proxyModel)
        
        self.ui_tree_view.expandAll()

        self.ui_filter_edit.textChanged.connect(self._proxyModel.setFilterRegExp)
        # submit
        self.ui_out_btn.clicked.connect(self.updateBrowser)
        # rollback
        self.ui_update_btn.clicked.connect(self.updateModel)
        # push 
        self.ui_push_btn.clicked.connect(self.push)

        # Json Viewer
        JsonHighlighter(self.ui_view_edit.document())
        self.updateBrowser()

    def updateModel(self):
        text = self.ui_view_edit.toPlainText()
        jsonDict = ast.literal_eval(text)
        root = jsonEditor.qjsonnode.QJsonNode.load(jsonDict)
        self._model = jsonEditor.qjsonmodel.QJsonModel(root)
        self._proxyModel.setSourceModel(self._model)
        self.ui_tree_view.expandAll()

    def updateBrowser(self):
        self.ui_view_edit.clear()
        output = self.ui_tree_view.asDict(None)
        jsonDict = json.dumps(output, indent=4, sort_keys=True, ensure_ascii=False)
        self.ui_view_edit.setPlainText(str(jsonDict))

    def push(self):
        output = self.ui_tree_view.asDict(None)
        jsonDict = json.dumps(output, indent=4, sort_keys=True, ensure_ascii=False)
        self.result = jsonDict
        self.app.quit()
        # print(jsonDict)


def edit(origin_json):
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(app,origin_json)
    window.show()
    app.exec_()
    return window.result


if __name__ == '__main__':
    TEST_DICT = {
        "firstName": "John",
        "lastName": "Smith",
        "age": 35,
        "address": {
            "streetAddress": "21 2nd Street",
            "city": "New York",
            "state": "NY",
            "postalCode": "10021"
        },
        "phoneNumber": [
            {
                "type": "home",
                "number": "212 555-1234"
            },
            {
                "type": "fax",
                "number": "646 555-4567"
            }
        ]
    }
    print(edit(json.dumps(TEST_DICT)))
