# layers.py
"""
Manual Chapter 10, "Managing Layers": a diagram has one or more named
layers, stacked in order. Objects belong to exactly one layer. Only
the current layer's objects can be selected (10.2.2 note: "Only
objects present in the current layer can be selected"). Each layer
can be independently shown/hidden (the "Eye Icon", 10.3) and moved up
or down in the stack (10.2.3).

Stacking is implemented as z-value bands: layer index * BAND_SIZE,
plus each item's own "local_z" (its position within just that layer,
which is what Objects->Send to Back/Bring to Front/etc. actually
move - see MainWindow.send_to_back and friends). BAND_SIZE is large
enough that ordinary within-layer z-shuffling never crosses into a
neighboring layer's band.
"""

BAND_SIZE = 1_000_000


class Layer:
    def __init__(self, name):
        self.name = name
        self.visible = True


class LayerManager:

    def __init__(self, scene):
        self.scene = scene
        self.layers = [Layer("Background")]
        self.current_index = 0

    def current_layer(self):
        return self.layers[self.current_index]

    def layer_index(self, layer):
        return self.layers.index(layer)

    # -- assigning items ----------------------------------------------

    def assign_to_current(self, item):
        self.assign(item, self.current_layer())

    def assign(self, item, layer):
        item.layer = layer

        if not hasattr(item, "local_z"):
            item.local_z = 0.0

        self._apply_item_z(item)

        item.setFlag(
            item.ItemIsSelectable,
            layer is self.current_layer()
        )

        item.setVisible(layer.visible)

    def local_z(self, item):
        return getattr(item, "local_z", 0.0)

    def set_local_z(self, item, value):
        item.local_z = value
        self._apply_item_z(item)

    def items_in_layer(self, layer):
        return [
            i for i in self.scene.items()
            if getattr(i, "layer", None) is layer
        ]

    def _apply_item_z(self, item):
        layer = getattr(item, "layer", None)

        if layer is None:
            return

        band = self.layer_index(layer) * BAND_SIZE
        item.setZValue(band + getattr(item, "local_z", 0.0))

    def _apply_all_z(self):
        for layer in self.layers:
            for item in self.items_in_layer(layer):
                self._apply_item_z(item)

    # -- managing layers (manual 10.2) --------------------------------

    def add_layer(self, name):
        layer = Layer(name)
        self.layers.append(layer)
        self.current_index = len(self.layers) - 1
        self._update_selectability()
        return layer

    def delete_layer(self, index):
        if len(self.layers) <= 1:
            return None

        layer = self.layers[index]

        for item in self.items_in_layer(layer):
            self.scene.removeItem(item)

        del self.layers[index]
        self.current_index = min(self.current_index, len(self.layers) - 1)

        self._apply_all_z()
        self._update_selectability()

        return layer

    def move_layer_up(self, index):
        """
        "Raise" a layer (manual 10.2.3): move it toward the top of the
        stack. Since z-value bands are index * BAND_SIZE, "toward the
        top" means toward a *higher* index.
        """

        if index >= len(self.layers) - 1:
            return

        self._swap(index, index + 1)

    def move_layer_down(self, index):
        if index <= 0:
            return

        self._swap(index, index - 1)

    def _swap(self, i, j):
        self.layers[i], self.layers[j] = self.layers[j], self.layers[i]

        if self.current_index == i:
            self.current_index = j
        elif self.current_index == j:
            self.current_index = i

        self._apply_all_z()

    def rename_layer(self, index, name):
        self.layers[index].name = name

    def set_current(self, index):
        self.current_index = index
        self._update_selectability()

    def set_visible(self, index, visible):
        layer = self.layers[index]
        layer.visible = visible

        for item in self.items_in_layer(layer):
            item.setVisible(visible)

    def _update_selectability(self):
        current = self.current_layer()

        for item in self.scene.items():
            if not hasattr(item, "layer"):
                continue

            # Group children have their own selectability locked by
            # the grouping mechanism (see GroupItemsCommand) - layers
            # only govern top-level items (a GroupItem itself included).
            if item.parentItem() is not None:
                continue

            is_current = item.layer is current
            item.setFlag(item.ItemIsSelectable, is_current)

            if not is_current and item.isSelected():
                item.setSelected(False)
