"""
The view inheriting QTreeView for displaying QJsonModel
this view is strictly used to display and control dictionary-like,
hierarchical data structure.
With custom implementation of drag & drop, editing behavior

Reference:
https://doc.qt.io/qt-5/model-view-programming.html#mime-data
https://doc.qt.io/qt-5/qitemselectionmodel.html
https://stackoverflow.com/questions/10778936/qt-mousemoveevent-qtleftbutton
https://doc.qt.io/qt-5/qmouseevent.html#button
"""

import ast

from Qt import QtWidgets, QtCore, QtGui

import jsonEditor.qjsonnode
from jsonEditor.textEditDialog import TextEditDialog


class QJsonView(QtWidgets.QTreeView):
    dragStartPosition = None

    def __init__(self):
        """
        Initialization
        """
        super(QJsonView, self).__init__()

        self._clipBroad = ''

        # set flags
        self.setSortingEnabled(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setUniformRowHeights(True)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.openContextMenu)

    def setModel(self, model):
        """
        Extend: set the current model and sort it

        :param model: QSortFilterProxyModel. model
        """
        super(QJsonView, self).setModel(model)
        self.model().sort(0, QtCore.Qt.AscendingOrder)

    def openContextMenu(self):
        """
        Custom: create a right-click context menu
        """
        contextMenu = QtWidgets.QMenu()

        indices = self.getSelectedIndices()
        # # no selection
        # if not indices:
        #     addAction = contextMenu.addAction('add entry')
        #     addAction.triggered.connect(self.custom_add)
        #
        #     clearAction = contextMenu.addAction('clear')
        #     clearAction.triggered.connect(self.clear)
        # else:

        # single selection
        if len(indices) == 1:
            index = indices[0]

            if index.internalPointer().dtype == list:
                addAction = contextMenu.addAction('add entry')
                addAction.triggered.connect(lambda: self.custom_add(index=index))

                if self._clipBroad:
                    pasteAction = contextMenu.addAction('paste entry(s)')
                    pasteAction.triggered.connect(lambda: self.paste(index))
            # only allow add when parent node is a list
            parent = index.parent()
            if parent.isValid() and parent.internalPointer().dtype == list:
                removeAction = contextMenu.addAction('remove entry(s)')
                removeAction.triggered.connect(lambda: self.remove(indices))

                copyAction = contextMenu.addAction('copy entry(s)')
                copyAction.triggered.connect(self.copy)

        contextMenu.exec_(QtGui.QCursor().pos())

    # helper methods

    def getSelectedIndices(self):
        """
        Custom: get source model indices of the selected item(s)

        :return: list of QModelIndex. selected indices
        """
        indices = self.selectionModel().selectedRows()
        return [self.model().mapToSource(index) for index in indices]

    def asDict(self, indices):
        """
        Custom: serialize specified model indices to dictionary

        :param indices: list of QModelIndex. root indices
        :return: dict. output dictionary
        """
        output = dict()
        if not indices:
            output = self.model().sourceModel().asDict()
        else:
            for index in indices:
                output.update(self.model().sourceModel().asDict(index))
        return output

    # overwrite drag and drop

    def mousePressEvent(self, event):
        """
        Override: record mouse click position
        """
        super(QJsonView, self).mousePressEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            self.dragStartPosition = event.pos()

    def mouseMoveEvent(self, event):
        """
        Override: instantiate custom drag object when dragging with left-click
        """
        if not event.buttons():
            return

        if not event.buttons() == QtCore.Qt.LeftButton:
            return

        if (event.pos() - self.dragStartPosition).manhattanLength() \
                < QtWidgets.QApplication.startDragDistance():
            return

        if self.selectionModel().selectedRows():
            drag = QtGui.QDrag(self)
            mimeData = QtCore.QMimeData()

            selected = self.asDict(self.getSelectedIndices())
            mimeData.setText(str(selected))
            drag.setMimeData(mimeData)

            drag.exec_()

    def dragEnterEvent(self, event):
        """
        Override: allow dragging only for certain drag object
        """
        data = event.mimeData()
        if data.hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """
        Override: disable dropping to certain model index based on node type
        """
        data = event.mimeData()
        if data.hasText():
            event.acceptProposedAction()

        dropIndex = self.indexAt(event.pos())
        dropIndex = self.model().mapToSource(dropIndex)

        # not allowing drop to non dictionary or list
        if not dropIndex == QtCore.QModelIndex():
            if dropIndex.internalPointer().dtype not in [list, dict]:
                event.ignore()

    def dropEvent(self, event):
        """
        Override: customize drop behavior to move for internal drag & drop
        """
        dropIndex = self.indexAt(event.pos())
        dropIndex = self.model().mapToSource(dropIndex)

        data = event.mimeData()
        self.remove(self.getSelectedIndices())
        self.add(data.text(), dropIndex)
        event.acceptProposedAction()

    # custom behavior

    def remove(self, indices):
        """
        Custom: remove node(s) of specified indices

        :param indices: QModelIndex. specified indices
        """
        for index in indices:
            currentNode = index.internalPointer()
            position = currentNode.row()

            # let the model know we are removing
            self.model().sourceModel().removeChild(position, index.parent())

    def add(self, text=None, index=QtCore.QModelIndex()):
        """
        Custom: add node(s) under the specified index

        :param text: str. input text for de-serialization
        :param index: QModelIndex. parent index
        """
        # populate items with a temp root
        root = jsonEditor.qjsonnode.QJsonNode.load(ast.literal_eval(text))

        self.model().sourceModel().addChildren(root.children, index)
        self.model().sort(0, QtCore.Qt.AscendingOrder)

    def clear(self):
        """
        Custom: clear the entire view
        """
        self.model().sourceModel().clear()

    def copy(self):
        """
        Custom: copy the selected indices by store the serialized value
        """
        selected = self.asDict(self.getSelectedIndices())
        self._clipBroad = str(selected)

    def paste(self, index):
        """
        Custom: paste to index by de-serialize clipboard value

        :param index: QModelIndex. target index
        """
        self.custom_add(self._clipBroad, index)
        # self._clipBroad = ''

    def custom_add(self, text=None, index=QtCore.QModelIndex()):
        """
        Custom: add node(s) under the specified index using specified values

        :param text: str. input text for de-serialization
        :param index: QModelIndex. parent index
        """

        # test value
        if not text:
            text = "{'item': {'name': 'department_name', 'url': 'people_page_url'}}"

        self.add(text, index)
