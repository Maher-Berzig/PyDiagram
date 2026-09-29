# document_io.py
"""
Loading and saving (manual Chapter 8). Dia's own native format is
gzip-compressed XML; we use plain JSON instead - same spirit (a
lossless, app-native round-trip format per 8.2.1: "The only format
guaranteed to be lossless is Dia XML") without pulling in an XML
schema for a from-scratch clone. File extension is .pydia.

Also covers export to PNG and SVG (manual 8.2.3), which - like Dia's
own exports - are one-way: you can save a .pydia and get it back
exactly, but an exported .png/.svg is for sharing, not reopening here.
"""

import json
import os

from PyQt5.QtCore import QPointF, QRectF, qInstallMessageHandler
from PyQt5.QtGui import QColor, QImage, QPainter

from items.color_picker import (
    is_gradient,
    is_pattern,
    is_radial_gradient,
    gradient_colors,
    gradient_angle,
    gradient_center,
    make_gradient,
    make_radial_gradient,
)
from items.pattern_fill import PatternFill

FORMAT_VERSION = 1


class _SuppressPorterDuffWarning:
    """Temporarily silence only Qt's Porter-Duff export warning.

    MaskItem intentionally uses CompositionMode_DestinationOut.  Raster
    devices support it, while Qt's PDF/SVG paint devices may print this
    diagnostic.  The original rendering path is preserved; only this
    specific message is filtered.
    """

    def __enter__(self):
        self._previous_handler = qInstallMessageHandler(self._handler)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        qInstallMessageHandler(self._previous_handler)
        return False

    def _handler(self, mode, context, message):
        if "QPainter::setCompositionMode: PorterDuff modes not supported on device" in message:
            return

        # Preserve an application-installed Qt message handler for all
        # messages that are not the one we intentionally suppress.
        if self._previous_handler is not None:
            self._previous_handler(mode, context, message)



def _color_to_json(color):
    """
    A plain color saves as its hex string, same as always; a gradient
    saves as {"gradient": [start_hex, end_hex], "angle": degrees} when
    linear, or {"gradient": [start_hex, end_hex], "type": "radial",
    "center": [x, y]} when radial; a pattern fill (app additions, not
    in the manual) saves as {"pattern": {...PatternFill fields...}} -
    so any of these survive a save/reload rather than crashing it
    (QColor.name() doesn't exist on a QGradient or a PatternFill).
    """

    if is_gradient(color):
        start, end = gradient_colors(color)

        if is_radial_gradient(color):
            cx, cy = gradient_center(color)
            return {
                "gradient": [start.name(), end.name()],
                "type": "radial",
                "center": [cx, cy],
            }

        return {
            "gradient": [start.name(), end.name()],
            "angle": gradient_angle(color),
        }

    if is_pattern(color):
        return {
            "pattern": {
                "pattern": color.pattern,
                "color_a": color.color_a.name(),
                "color_b": color.color_b.name(),
                "size": color.size,
                "line_width": color.line_width,
                "angle": color.angle,
                "image_path": color.image_path,
                "image_width": color.image_width,
                "image_height": color.image_height,
            }
        }

    return color.name()


def _color_from_json(value, default="#000000"):
    if value is None:
        return QColor(default)

    if isinstance(value, dict) and "gradient" in value:
        start, end = value["gradient"]

        if value.get("type") == "radial":
            cx, cy = value.get("center", [0.5, 0.5])
            return make_radial_gradient(QColor(start), QColor(end), (cx, cy))

        return make_gradient(QColor(start), QColor(end), value.get("angle", 0))

    if isinstance(value, dict) and "pattern" in value:
        p = value["pattern"]
        return PatternFill(
            pattern=p.get("pattern", "cross"),
            color_a=QColor(p.get("color_a", "#1565C0")),
            color_b=QColor(p.get("color_b", "#E3F2FD")),
            size=p.get("size", 24),
            line_width=p.get("line_width", 2),
            angle=p.get("angle", 0),
            image_path=p.get("image_path"),
            image_width=p.get("image_width", 70),
            image_height=p.get("image_height", 70),
        )

    return QColor(value)


def _nodes_to_json(nodes):
    def point_or_none(p):
        return [p.x(), p.y()] if p is not None else None

    return [
        {
            "anchor": point_or_none(n["anchor"]),
            "control_in": point_or_none(n["control_in"]),
            "control_out": point_or_none(n["control_out"]),
            "mode": n["mode"],
        }
        for n in nodes
    ]


def _nodes_from_json(entries):
    def point_or_none(v):
        return QPointF(*v) if v is not None else None

    return [
        {
            "anchor": point_or_none(e["anchor"]),
            "control_in": point_or_none(e["control_in"]),
            "control_out": point_or_none(e["control_out"]),
            "mode": e.get("mode", "symmetric"),
        }
        for e in entries
    ]


def _item_classes():
    # Deferred import: avoids a load-order cycle with items/*.py,
    # which already import from canvas.commands at module scope.
    from items.rectangle_item import RectangleItem
    from items.ellipse_item import EllipseItem
    from items.diamond_item import DiamondItem
    from items.cylinder_item import CylinderItem
    from items.actor_item import ActorItem
    from items.interface_item import InterfaceItem
    from items.class_item import ClassItem
    from items.plot_item import PlotItem
    from items.text_item import TextItem
    from items.line_item import LineItem
    from items.arc_item import ArcItem
    from items.polygon_item import PolygonItem
    from items.polyline_item import PolylineItem
    from items.zigzagline_item import ZigzaglineItem
    from items.image_item import ImageItem
    from items.bezierline_item import BezierlineItem
    from items.beziergon_item import BeziergonItem
    from items.mask_item import MaskItem
    from items.group_item import GroupItem
    from items.assorted_item import (
        SquareItem, CircleItem, IsoscelesTriangleItem, RightTriangleItem,
        CrossItem, RegularPolygonItem, StarItem, SpiralItem, CircleSectionItem,
    )

    return (
        RectangleItem, EllipseItem, DiamondItem, CylinderItem,
        ActorItem, InterfaceItem, ClassItem,
        PlotItem, TextItem, LineItem, GroupItem, ArcItem, PolygonItem,
        PolylineItem, ZigzaglineItem, ImageItem, BezierlineItem,
        BeziergonItem, SquareItem, CircleItem, IsoscelesTriangleItem,
        RightTriangleItem, CrossItem, RegularPolygonItem, StarItem, SpiralItem,
        CircleSectionItem,
    )


def _simple_shape_types():
    """
    Rectangle/Ellipse/Diamond/Cylinder/Actor/Interface all serialize
    identically - just a bounding rect plus fill/border/border_width -
    so they share one type<->class mapping instead of six near-
    duplicate branches. ClassItem also carries class_name/attributes/
    operations, so it's handled separately.
    """

    (RectangleItem, EllipseItem, DiamondItem, CylinderItem,
     ActorItem, InterfaceItem, _ClassItem) = _item_classes()[:7]

    (SquareItem, CircleItem, IsoscelesTriangleItem, RightTriangleItem,
     CrossItem, RegularPolygonItem, StarItem, SpiralItem) = _item_classes()[18:26]

    return {
        "rect": RectangleItem,
        "ellipse": EllipseItem,
        "diamond": DiamondItem,
        "cylinder": CylinderItem,
        "actor": ActorItem,
        "interface": InterfaceItem,
        "square": SquareItem,
        "circle": CircleItem,
        "isosceles_triangle": IsoscelesTriangleItem,
        "right_triangle": RightTriangleItem,
        "cross": CrossItem,
        "regular_polygon": RegularPolygonItem,
        "star": StarItem,
    }


def _stencil_shape_types():
    """Type-name -> class for the Flowchart/UML shapes in
    items/stencil_items.py (deferred import, same reason as
    _item_classes())."""

    from items.stencil_items import STENCIL_SHAPES

    return STENCIL_SHAPES


def _serialize_item(item, id_map, layer_id_map):
    from items.mask_item import MaskItem

    (RectangleItem, EllipseItem, DiamondItem, CylinderItem,
     ActorItem, InterfaceItem, ClassItem,
     PlotItem, TextItem, LineItem, GroupItem, ArcItem, PolygonItem,
     PolylineItem, ZigzaglineItem, ImageItem, BezierlineItem,
     BeziergonItem, SquareItem, CircleItem, IsoscelesTriangleItem,
     RightTriangleItem, CrossItem, RegularPolygonItem, StarItem, SpiralItem,
     CircleSectionItem) = _item_classes()

    scene_pos = item.scenePos()

    data = {
        "id": id_map[item],
        "pos": [scene_pos.x(), scene_pos.y()],
        "rotation": item.rotation_angle,
        "flip_h": item.flip_horizontal,
        "flip_v": item.flip_vertical,
        "scale_x": item.scale_x,
        "scale_y": item.scale_y,
        # App addition (not in the manual): a user-given Diagram Tree
        # name (manual 4.5) - see items.diagram_item.DiagramItem
        # .custom_name.
        "custom_name": item.custom_name,
        # App addition (not in the manual): destination document ID for
        # an internal PDF page link.  It is intentionally not a page
        # number; the exporter resolves the ID after the final export
        # order is known.
        "pdf_link_target": getattr(item, "pdf_link_target", None),
        # App addition (not in the manual): an ImageItem's LaTeX
        # recipe, if "Create from LaTeX..." produced its file - see
        # items.image_item.ImageItem.latex_recipe and app/
        # latex_render.py's module docstring. None for every other
        # item type, and for a plain Browse...'d image.
        "latex_recipe": getattr(item, "latex_recipe", None),
        "layer_index": (
            layer_id_map[item.layer]
            if getattr(item, "layer", None) in layer_id_map else 0
        ),
        "local_z": getattr(item, "local_z", 0.0),
        # App addition (not in the manual): user-placed connection
        # points from the Anchor tool - see
        # DiagramItem.add_custom_connection_point()/
        # all_connection_points().
        "custom_connection_points": [
            [p.x(), p.y()] for p in item._custom_connection_points
        ],
    }

    if isinstance(item, GroupItem):
        data["type"] = "group"
        data["children"] = [id_map[c] for c in item._children]
        return data

    if isinstance(item, TextItem):
        r = item._rect
        data["type"] = "text"
        data["rect"] = [r.x(), r.y(), r.width(), r.height()]
        data["text"] = item.text()
        data["font_family"] = item.font_family
        data["font_size"] = item.font_size
        data["font_weight"] = item.font_weight
        data["text_align"] = item.text_align
        data["text_color"] = _color_to_json(item.text_color)
        data["fill_color"] = _color_to_json(item.fill_color)
        data["draw_background"] = item.draw_background
        data["letter_spacing"] = item.letter_spacing
        data["outline_enabled"] = item.outline_enabled
        data["outline_color"] = _color_to_json(item.outline_color)
        data["outline_width"] = item.outline_width
        return data

    if isinstance(item, ClassItem):
        r = item._rect
        data["type"] = "class"
        data["rect"] = [r.x(), r.y(), r.width(), r.height()]
        data["fill"] = _color_to_json(item.fill_color)
        data["border"] = _color_to_json(item.border_color)
        data["border_width"] = item.border_width
        data["class_name"] = item.class_name
        data["attributes"] = item.attributes
        data["operations"] = item.operations
        return data

    if isinstance(item, PlotItem):
        r = item._rect
        data["type"] = "plot"
        data["rect"] = [r.x(), r.y(), r.width(), r.height()]
        data["f1_expr"] = item.f1_expr
        data["f2_expr"] = item.f2_expr
        data["x1"] = item.x1
        data["x2"] = item.x2
        data["x_min"] = item.x_min
        data["x_max"] = item.x_max
        data["y_min"] = item.y_min
        data["y_max"] = item.y_max
        data["axis_type"] = item.axis_type
        data["show_grid"] = item.show_grid
        data["show_bounds_lines"] = item.show_bounds_lines
        data["show_xtick_labels"] = item.show_xtick_labels
        data["show_ytick_labels"] = item.show_ytick_labels
        data["xtick_interval"] = item.xtick_interval
        data["ytick_interval"] = item.ytick_interval
        data["x_tick_label_format"] = item.x_tick_label_format
        data["y_tick_label_format"] = item.y_tick_label_format
        data["num_points"] = item.num_points
        data["f1_color"] = _color_to_json(item.f1_color)
        data["f2_color"] = _color_to_json(item.f2_color)
        data["curve_width"] = item.curve_width
        data["x1_line_color"] = _color_to_json(item.x1_line_color)
        data["x2_line_color"] = _color_to_json(item.x2_line_color)
        data["bounds_line_width"] = item.bounds_line_width
        data["bounds_line_style"] = item.bounds_line_style
        data["fill_color"] = _color_to_json(item.fill_color)
        data["border_color"] = _color_to_json(item.border_color)
        data["border_width"] = item.border_width
        data["line_style"] = item.line_style
        data["dash_length"] = item.dash_length
        return data

    from items.stencil_items import StencilItem

    if isinstance(item, StencilItem):
        # Flowchart/UML shapes (items/stencil_items.py). The size
        # parameters each shape has (item.PARAMS) are stored by name, so
        # a shape gaining a parameter later stays readable both ways.
        r = item._rect
        data["type"] = item.SHAPE_TYPE
        data["rect"] = [r.x(), r.y(), r.width(), r.height()]
        data["fill"] = _color_to_json(item.fill_color)
        data["border"] = _color_to_json(item.border_color)
        data["border_width"] = item.border_width
        data["line_style"] = item.line_style
        data["dash_length"] = item.dash_length
        data["draw_background"] = item.draw_background
        data.update(item.param_values())
        return data

    if isinstance(item, CircleSectionItem):
        r = item._rect
        data["type"] = "circle_section"
        data["rect"] = [r.x(), r.y(), r.width(), r.height()]
        data["missing_angle"] = item.missing_angle
        data["fill"] = _color_to_json(item.fill_color)
        data["border"] = _color_to_json(item.border_color)
        data["border_width"] = item.border_width
        data["line_style"] = item.line_style
        data["dash_length"] = item.dash_length
        data["draw_background"] = item.draw_background
        return data

    for type_name, cls in _simple_shape_types().items():
        if isinstance(item, cls):
            r = item._rect
            data["type"] = type_name
            data["rect"] = [r.x(), r.y(), r.width(), r.height()]
            data["fill"] = _color_to_json(item.fill_color)
            data["border"] = _color_to_json(item.border_color)
            data["border_width"] = item.border_width

            if type_name == "rect":
                # Manual 5.1.2, "Box": Box-only properties.
                data["corner_radii"] = item.corner_radii
                data["draw_background"] = item.draw_background

            if type_name in (
                "rect", "ellipse", "circle",
                "isosceles_triangle", "right_triangle", "cross",
                "regular_polygon", "star",
            ):
                data["line_style"] = item.line_style
                data["dash_length"] = item.dash_length

            if type_name == "regular_polygon":
                data["num_points"] = item.num_points
                data["corner_radius"] = item.corner_radius
                data["draw_background"] = item.draw_background

            if type_name == "star":
                data["num_points"] = item.num_points
                data["inner_radius_ratio"] = item.inner_radius_ratio
                data["outer_corner_radius"] = item.outer_corner_radius
                data["inner_corner_radius"] = item.inner_corner_radius
                data["draw_background"] = item.draw_background

            return data

    if isinstance(item, SpiralItem):
        data["type"] = "spiral"
        data["center"] = [item._center.x(), item._center.y()]
        data["endpoint"] = [item._endpoint.x(), item._endpoint.y()]
        data["turns"] = item.turns
        data["pen_color"] = _color_to_json(item.pen_color)
        data["pen_width"] = item.pen_width
        data["line_style"] = item.line_style
        data["dash_length"] = item.dash_length
        return data

    if isinstance(item, ArcItem):
        # Checked before the plain-LineItem branch below, since Arc
        # is implemented as a LineItem subclass (manual 5.1.7/5.1.11 -
        # "all lines share" width/color/style/arrows) and would
        # otherwise be caught there first, losing its bow.
        data["type"] = "arc"
        data["p1"] = [item._p1.x(), item._p1.y()]
        data["p2"] = [item._p2.x(), item._p2.y()]
        data["bow"] = item._bow
        data["pen_color"] = _color_to_json(item.pen_color)
        data["pen_width"] = item.pen_width
        data["line_style"] = item.line_style
        data["dash_length"] = item.dash_length
        data["start_arrow"] = item.start_arrow
        data["end_arrow"] = item.end_arrow
        data["start_arrow_size"] = item.start_arrow_size
        data["end_arrow_size"] = item.end_arrow_size

        data["start_conn"] = (
            {"item": id_map[item._start_conn[0]], "index": item._start_conn[1]}
            if item._start_conn and item._start_conn[0] in id_map else None
        )
        data["end_conn"] = (
            {"item": id_map[item._end_conn[0]], "index": item._end_conn[1]}
            if item._end_conn and item._end_conn[0] in id_map else None
        )
        return data

    if isinstance(item, LineItem):
        data["type"] = "line"
        data["p1"] = [item._p1.x(), item._p1.y()]
        data["p2"] = [item._p2.x(), item._p2.y()]
        data["pen_color"] = _color_to_json(item.pen_color)
        data["pen_width"] = item.pen_width
        data["line_style"] = item.line_style
        data["dash_length"] = item.dash_length
        data["start_arrow"] = item.start_arrow
        data["end_arrow"] = item.end_arrow
        data["start_arrow_size"] = item.start_arrow_size
        data["end_arrow_size"] = item.end_arrow_size

        data["start_conn"] = (
            {"item": id_map[item._start_conn[0]], "index": item._start_conn[1]}
            if item._start_conn and item._start_conn[0] in id_map else None
        )
        data["end_conn"] = (
            {"item": id_map[item._end_conn[0]], "index": item._end_conn[1]}
            if item._end_conn and item._end_conn[0] in id_map else None
        )
        return data

    if isinstance(item, PolygonItem):
        data["type"] = "polygon"
        data["points"] = [[p.x(), p.y()] for p in item._points]
        data["fill"] = _color_to_json(item.fill_color)
        data["border"] = _color_to_json(item.border_color)
        data["border_width"] = item.border_width
        data["line_style"] = item.line_style
        data["dash_length"] = item.dash_length
        return data

    if isinstance(item, ZigzaglineItem):
        # Checked before the plain PolylineItem branch below, since
        # Zigzagline is a Polyline subclass and would otherwise match
        # there first, losing its autoroute flag.
        data["type"] = "zigzagline"
        data["points"] = [[p.x(), p.y()] for p in item._points]
        data["pen_color"] = _color_to_json(item.pen_color)
        data["pen_width"] = item.pen_width
        data["line_style"] = item.line_style
        data["dash_length"] = item.dash_length
        data["start_arrow"] = item.start_arrow
        data["end_arrow"] = item.end_arrow
        data["start_arrow_size"] = item.start_arrow_size
        data["end_arrow_size"] = item.end_arrow_size
        data["corner_radius"] = item.corner_radius
        data["autoroute"] = item.autoroute

        data["start_conn"] = (
            {"item": id_map[item._start_conn[0]], "index": item._start_conn[1]}
            if item._start_conn and item._start_conn[0] in id_map else None
        )
        data["end_conn"] = (
            {"item": id_map[item._end_conn[0]], "index": item._end_conn[1]}
            if item._end_conn and item._end_conn[0] in id_map else None
        )
        return data

    if isinstance(item, PolylineItem):
        data["type"] = "polyline"
        data["points"] = [[p.x(), p.y()] for p in item._points]
        data["pen_color"] = _color_to_json(item.pen_color)
        data["pen_width"] = item.pen_width
        data["line_style"] = item.line_style
        data["dash_length"] = item.dash_length
        data["start_arrow"] = item.start_arrow
        data["end_arrow"] = item.end_arrow
        data["start_arrow_size"] = item.start_arrow_size
        data["end_arrow_size"] = item.end_arrow_size
        data["corner_radius"] = item.corner_radius

        data["start_conn"] = (
            {"item": id_map[item._start_conn[0]], "index": item._start_conn[1]}
            if item._start_conn and item._start_conn[0] in id_map else None
        )
        data["end_conn"] = (
            {"item": id_map[item._end_conn[0]], "index": item._end_conn[1]}
            if item._end_conn and item._end_conn[0] in id_map else None
        )
        return data

    if isinstance(item, ImageItem):
        r = item._rect
        data["type"] = "image"
        data["rect"] = [r.x(), r.y(), r.width(), r.height()]
        data["file_path"] = item.file_path
        return data

    if isinstance(item, MaskItem):
        data["type"] = "mask"
        data["nodes"] = _nodes_to_json(item._nodes)
        data["fill"] = _color_to_json(item.fill_color)
        data["border"] = _color_to_json(item.border_color)
        data["border_width"] = item.border_width
        data["line_style"] = item.line_style
        data["dash_length"] = item.dash_length
        return data

    if isinstance(item, BeziergonItem):
        data["type"] = "beziergon"
        data["nodes"] = _nodes_to_json(item._nodes)
        data["fill"] = _color_to_json(item.fill_color)
        data["border"] = _color_to_json(item.border_color)
        data["border_width"] = item.border_width
        data["line_style"] = item.line_style
        data["dash_length"] = item.dash_length
        return data

    if isinstance(item, BezierlineItem):
        data["type"] = "bezierline"
        data["nodes"] = _nodes_to_json(item._nodes)
        data["pen_color"] = _color_to_json(item.pen_color)
        data["pen_width"] = item.pen_width
        data["line_style"] = item.line_style
        data["dash_length"] = item.dash_length
        data["start_arrow"] = item.start_arrow
        data["end_arrow"] = item.end_arrow
        data["start_arrow_size"] = item.start_arrow_size
        data["end_arrow_size"] = item.end_arrow_size

        data["start_conn"] = (
            {"item": id_map[item._start_conn[0]], "index": item._start_conn[1]}
            if item._start_conn and item._start_conn[0] in id_map else None
        )
        data["end_conn"] = (
            {"item": id_map[item._end_conn[0]], "index": item._end_conn[1]}
            if item._end_conn and item._end_conn[0] in id_map else None
        )
        return data

    return None


def serialize_scene(scene):
    from items.diagram_item import DiagramItem

    all_items = [i for i in scene.items() if isinstance(i, DiagramItem)]
    id_map = {item: idx for idx, item in enumerate(all_items)}

    layer_manager = scene.layer_manager
    layer_id_map = {
        layer: idx for idx, layer in enumerate(layer_manager.layers)
    }

    items_data = [
        entry for entry in (
            _serialize_item(item, id_map, layer_id_map)
            for item in all_items
        ) if entry is not None
    ]

    layers_data = [
        {"name": layer.name, "visible": layer.visible}
        for layer in layer_manager.layers
    ]

    return {
        "version": FORMAT_VERSION,
        "document_id": getattr(scene, "document_id", None),
        "items": items_data,
        "layers": layers_data,
        "current_layer_index": layer_manager.current_index,
        # Manual 3.1-3.4/9.1.5: per-diagram canvas settings, edited via
        # Diagram -> Properties.
        "canvas": {
            "show_grid": scene.show_grid,
            "grid_x_size": scene.grid_x_size,
            "grid_y_size": scene.grid_y_size,
            "grid_color": scene.grid_color.name(),
            "snap_to_grid": scene.snap_to_grid,
            "snap_to_objects": scene.snap_to_objects,
            "show_connection_points": scene.show_connection_points,
            "background_color": scene.background_color.name(),
            "paper_format": getattr(scene, "paper_format", "A4"),
            "paper_orientation": getattr(scene, "paper_orientation", "portrait"),
            "custom_width_mm": getattr(scene, "custom_width_mm", 210.0),
            "custom_height_mm": getattr(scene, "custom_height_mm", 297.0),
        },
    }


def save_scene(scene, path):
    data = serialize_scene(scene)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def serialize_items(items):
    """
    The same per-item JSON shape as serialize_scene()/_serialize_item -
    but scoped to just `items` (each already on some scene) rather
    than everything in it, and with no layers/canvas section, since
    there's no whole document here to describe. Used for exporting a
    reusable custom shape (app/custom_shapes.py: Objects -> Save as
    New Shape...) rather than a full diagram.

    A GroupItem among `items` pulls its children in automatically
    (recursively - a group of groups works too), same as
    serialize_scene() does implicitly by walking scene.items(). Every
    item, group children included, is still recorded at its absolute
    scene position (_serialize_item always uses .scenePos()) - exactly
    what deserialize_items() below expects to find.
    """

    from items.group_item import GroupItem

    def _collect(item, acc):
        acc.append(item)

        if isinstance(item, GroupItem):
            for child in item._children:
                _collect(child, acc)

    all_items = []

    for item in items:
        _collect(item, all_items)

    id_map = {item: idx for idx, item in enumerate(all_items)}

    items_data = [
        entry for entry in (
            _serialize_item(item, id_map, {})
            for item in all_items
        ) if entry is not None
    ]

    return {
        "version": FORMAT_VERSION,
        "items": items_data,
        "root_ids": [id_map[item] for item in items],
    }


def deserialize_items(data):
    """
    The reverse of serialize_items(): rebuilds the saved items as
    freestanding QGraphicsItems - not added to any scene, and with no
    layer/undo-stack bookkeeping, since a saved shape has none of its
    own until whoever places it (see canvas.tools.CustomShapeTool)
    adds it to one. Returns just the top-level items (data["root_ids"]);
    for a shape saved as a single combined selection that's usually
    one item (often a GroupItem), but a shape saved from several
    still-independent top-level items comes back the same way.

    Mirrors deserialize_scene()'s Pass 1 (build every item at its
    saved absolute position) and Pass 2 (reparent group children,
    which Qt then repositions to preserve that absolute position -
    see GroupItemsCommand for the same pattern). There's no Pass 3
    here: a line connection into another item in the selection isn't
    restored, the same deliberate simplification already used for
    Copy/Paste/Duplicate (see MainWindow._snapshot_item).
    """

    items_data = data.get("items", [])
    by_id = {}

    for entry in items_data:
        item = _construct_item_from_entry(entry)

        if item is None:
            continue

        # Rotation/flip first, so the item's transform is already in
        # place when _pos_for_target_point() below reads it back -
        # see that function's docstring.
        item.rotation_angle = entry.get("rotation", 0.0)
        item.flip_horizontal = entry.get("flip_h", False)
        item.flip_vertical = entry.get("flip_v", False)
        item.scale_x = entry.get("scale_x", 1.0)
        item.scale_y = entry.get("scale_y", 1.0)
        item.custom_name = entry.get("custom_name")
        item.pdf_link_target = entry.get("pdf_link_target")

        if hasattr(item, "latex_recipe"):
            item.latex_recipe = entry.get("latex_recipe")

        item.setPos(_pos_for_target_point(item, QPointF(*entry["pos"])))

        # App addition (not in the manual): restore each item's
        # relative stacking position among its future siblings -
        # without this, every reconstructed item ties at the default
        # 0.0 and whoever places this shape (CustomShapeTool) falls
        # back to _children's plain list order, which is back-to-front
        # (see GroupItemsCommand's docstring) - the *opposite* of the
        # front-to-back order the Diagram Tree expects, inverting a
        # saved group's child order there.
        item.local_z = entry.get("local_z", 0.0)

        by_id[entry["id"]] = item

    for entry in items_data:
        if entry.get("type") != "group":
            continue

        group = by_id.get(entry["id"])

        if group is None:
            continue

        children = [
            by_id[cid] for cid in entry.get("children", []) if cid in by_id
        ]

        for child in children:
            # See the matching comment in deserialize_scene()'s Pass 2:
            # child.pos() is still the absolute position saved in
            # entry["pos"], and setParentItem() won't adjust it for
            # us, so convert to the group's local coordinates first
            # (mapFromScene() also accounts for the group's own
            # rotation/flip transform) to keep the child's true
            # position unchanged across the reparent.
            target_point = group.mapFromScene(child.scenePos())
            child.setParentItem(group)
            child.setPos(_pos_for_target_point(child, target_point))
            child.setFlag(child.ItemIsSelectable, False)
            child.setFlag(child.ItemIsMovable, False)

        group._children = children

    root_ids = data.get("root_ids", list(by_id.keys()))

    return [by_id[i] for i in root_ids if i in by_id]


def _construct_item_from_entry(entry):
    """
    Builds and configures one item from its serialized entry (the
    per-item shape _serialize_item() produces) - everything about the
    item's *type* (rect/text/group/...), i.e. every field besides
    pos/rotation/flip/layer/z. Those are deliberately left to the
    caller: deserialize_scene()'s Pass 1 places the item straight
    into a live scene/layer, while deserialize_items() (a saved
    custom shape - see app/custom_shapes.py) builds freestanding
    items with no scene or layers to place them into at all. Returns
    None for an entry of an unrecognized type (forward-compatibility:
    an old build opening a file saved by a newer one skips whatever
    it doesn't understand instead of crashing).
    """

    from items.mask_item import MaskItem

    (RectangleItem, EllipseItem, DiamondItem, CylinderItem,
     ActorItem, InterfaceItem, ClassItem,
     PlotItem, TextItem, LineItem, GroupItem, ArcItem, PolygonItem,
     PolylineItem, ZigzaglineItem, ImageItem, BezierlineItem,
     BeziergonItem, SquareItem, CircleItem, IsoscelesTriangleItem,
     RightTriangleItem, CrossItem, RegularPolygonItem, StarItem, SpiralItem,
     CircleSectionItem) = _item_classes()

    simple_shape_types = _simple_shape_types()
    kind = entry.get("type")

    if kind == "text":
        item = TextItem(QRectF(*entry["rect"]), entry.get("text", ""))
        item.font_family = entry.get("font_family", "Sans Serif")
        item.font_size = entry.get("font_size", 11)
        item.font_weight = entry.get("font_weight", "normal")
        item.text_align = entry.get("text_align", "left")
        item.text_color = _color_from_json(entry.get("text_color"), "#202020")
        item.fill_color = _color_from_json(entry.get("fill_color"), "#ffffff")
        item.draw_background = entry.get("draw_background", False)
        item.letter_spacing = entry.get("letter_spacing", 0.0)
        item.outline_enabled = entry.get("outline_enabled", False)
        item.outline_color = _color_from_json(entry.get("outline_color"), "#000000")
        item.outline_width = entry.get("outline_width", 2.0)
    elif kind == "class":
        item = ClassItem(
            QRectF(*entry["rect"]),
            entry.get("class_name", "ClassName"),
            entry.get("attributes", ""),
            entry.get("operations", ""),
        )
        item.fill_color = _color_from_json(entry["fill"])
        item.border_color = _color_from_json(entry["border"])
        item.border_width = entry["border_width"]
    elif kind == "plot":
        item = PlotItem(QRectF(*entry["rect"]))
        item.f1_expr = entry.get("f1_expr", item.f1_expr)
        item.f2_expr = entry.get("f2_expr", item.f2_expr)
        item.x1 = entry.get("x1", item.x1)
        item.x2 = entry.get("x2", item.x2)
        item.x_min = entry.get("x_min", item.x_min)
        item.x_max = entry.get("x_max", item.x_max)
        item.y_min = entry.get("y_min", item.y_min)
        item.y_max = entry.get("y_max", item.y_max)
        item.axis_type = entry.get("axis_type", item.axis_type)
        item.show_grid = entry.get("show_grid", item.show_grid)
        item.show_bounds_lines = entry.get(
            "show_bounds_lines", item.show_bounds_lines
        )
        item.show_xtick_labels = entry.get(
            "show_xtick_labels", item.show_xtick_labels
        )
        item.show_ytick_labels = entry.get(
            "show_ytick_labels", item.show_ytick_labels
        )
        item.xtick_interval = entry.get("xtick_interval", item.xtick_interval)
        item.ytick_interval = entry.get("ytick_interval", item.ytick_interval)
        item.x_tick_label_format = entry.get(
            "x_tick_label_format", item.x_tick_label_format
        )
        item.y_tick_label_format = entry.get(
            "y_tick_label_format", item.y_tick_label_format
        )
        item.num_points = entry.get("num_points", item.num_points)
        item.f1_color = _color_from_json(entry.get("f1_color"), "#1565C0")
        item.f2_color = _color_from_json(entry.get("f2_color"), "#C62828")
        item.curve_width = entry.get("curve_width", item.curve_width)
        item.x1_line_color = _color_from_json(
            entry.get("x1_line_color"), "#607D8B"
        )
        item.x2_line_color = _color_from_json(
            entry.get("x2_line_color"), "#607D8B"
        )
        item.bounds_line_width = entry.get(
            "bounds_line_width", item.bounds_line_width
        )
        item.bounds_line_style = entry.get(
            "bounds_line_style", item.bounds_line_style
        )
        item.fill_color = _color_from_json(entry.get("fill_color"))
        item.border_color = _color_from_json(entry.get("border_color"))
        item.border_width = entry.get("border_width", item.border_width)
        item.line_style = entry.get("line_style", item.line_style)
        item.dash_length = entry.get("dash_length", item.dash_length)
    elif kind == "circle_section":
        item = CircleSectionItem(QRectF(*entry["rect"]))
        item.missing_angle = max(item.MIN_MISSING_ANGLE, min(item.MAX_MISSING_ANGLE, float(entry.get("missing_angle", item.missing_angle))))
        item.fill_color = _color_from_json(entry.get("fill"))
        item.border_color = _color_from_json(entry.get("border"))
        item.border_width = entry.get("border_width", item.border_width)
        item.line_style = entry.get("line_style", item.line_style)
        item.dash_length = entry.get("dash_length", item.dash_length)
        item.draw_background = entry.get("draw_background", True)
        item._update_angle_handle()
    elif kind in _stencil_shape_types():
        item = _stencil_shape_types()[kind](QRectF(*entry["rect"]))
        item.fill_color = _color_from_json(entry.get("fill"), "#ffffff")
        item.border_color = _color_from_json(entry.get("border"), "#202020")
        item.border_width = entry.get("border_width", item.border_width)
        item.line_style = entry.get("line_style", "solid")
        item.dash_length = entry.get("dash_length", 10.0)
        item.draw_background = entry.get("draw_background", True)
        item.set_param_values(entry)
    elif kind in simple_shape_types:
        item = simple_shape_types[kind](QRectF(*entry["rect"]))
        item.fill_color = _color_from_json(entry["fill"])
        item.border_color = _color_from_json(entry["border"])
        item.border_width = entry["border_width"]

        if kind == "rect":
            # .get() with a default: older saved files won't have
            # these keys yet.
            if "corner_radii" in entry:
                item.corner_radii = entry["corner_radii"]
            else:
                # Older files: one radius for all four corners.
                item.corner_radius = entry.get("corner_radius", 0.0)

            item.draw_background = entry.get("draw_background", True)

        if kind in (
            "rect", "ellipse", "circle",
            "isosceles_triangle", "right_triangle", "cross",
            "regular_polygon", "star",
        ):
            item.line_style = entry.get("line_style", "solid")
            item.dash_length = entry.get("dash_length", 10.0)

        if kind == "regular_polygon":
            item.num_points = max(item.MIN_POINTS, int(entry.get("num_points", item.num_points)))
            item.corner_radius = entry.get("corner_radius", item.corner_radius)
            item.draw_background = entry.get("draw_background", True)

        if kind == "star":
            item.num_points = max(item.MIN_POINTS, int(entry.get("num_points", item.num_points)))
            item.inner_radius_ratio = entry.get("inner_radius_ratio", item.inner_radius_ratio)
            item.outer_corner_radius = entry.get("outer_corner_radius", item.outer_corner_radius)
            item.inner_corner_radius = entry.get("inner_corner_radius", item.inner_corner_radius)
            item.draw_background = entry.get("draw_background", True)
            item._update_special_handles()
    elif kind == "spiral":
        item = SpiralItem(QPointF(*entry.get("center", [0, 0])), QPointF(*entry.get("endpoint", [100, 0])))
        item.turns = entry.get("turns", item.turns)
        item.pen_color = _color_from_json(entry.get("pen_color"), "#202020")
        item.pen_width = entry.get("pen_width", item.pen_width)
        item.line_style = entry.get("line_style", "solid")
        item.dash_length = entry.get("dash_length", 10.0)
        item._update_handles()
    elif kind == "line":
        item = LineItem(QPointF(*entry["p1"]), QPointF(*entry["p2"]))
        item.pen_color = _color_from_json(entry["pen_color"])
        item.pen_width = entry["pen_width"]
        item.line_style = entry.get("line_style", "solid")
        item.dash_length = entry.get("dash_length", 10.0)
        item.start_arrow = entry.get("start_arrow", "none")
        item.end_arrow = entry.get("end_arrow", "none")
        item.start_arrow_size = entry.get("start_arrow_size", 1.0)
        item.end_arrow_size = entry.get("end_arrow_size", 1.0)
    elif kind == "arc":
        item = ArcItem(QPointF(*entry["p1"]), QPointF(*entry["p2"]))
        item._bow = entry.get("bow", 30.0)
        item.pen_color = _color_from_json(entry["pen_color"])
        item.pen_width = entry["pen_width"]
        item.line_style = entry.get("line_style", "solid")
        item.dash_length = entry.get("dash_length", 10.0)
        item.start_arrow = entry.get("start_arrow", "none")
        item.end_arrow = entry.get("end_arrow", "none")
        item.start_arrow_size = entry.get("start_arrow_size", 1.0)
        item.end_arrow_size = entry.get("end_arrow_size", 1.0)
        item._position_handles()
    elif kind == "polygon":
        item = PolygonItem(
            [QPointF(x, y) for x, y in entry.get("points", [])]
        )
        item.fill_color = _color_from_json(entry["fill"])
        item.border_color = _color_from_json(entry["border"])
        item.border_width = entry["border_width"]
        item.line_style = entry.get("line_style", "solid")
        item.dash_length = entry.get("dash_length", 10.0)
    elif kind == "zigzagline":
        item = ZigzaglineItem(
            [QPointF(x, y) for x, y in entry.get("points", [])]
        )
        item.autoroute = entry.get("autoroute", True)
        item.pen_color = _color_from_json(entry["pen_color"])
        item.pen_width = entry["pen_width"]
        item.line_style = entry.get("line_style", "solid")
        item.dash_length = entry.get("dash_length", 10.0)
        item.start_arrow = entry.get("start_arrow", "none")
        item.end_arrow = entry.get("end_arrow", "none")
        item.start_arrow_size = entry.get("start_arrow_size", 1.0)
        item.end_arrow_size = entry.get("end_arrow_size", 1.0)
        item.corner_radius = entry.get("corner_radius", 0.0)
        item._position_handles()
    elif kind == "polyline":
        item = PolylineItem(
            [QPointF(x, y) for x, y in entry.get("points", [])]
        )
        item.pen_color = _color_from_json(entry["pen_color"])
        item.pen_width = entry["pen_width"]
        item.line_style = entry.get("line_style", "solid")
        item.dash_length = entry.get("dash_length", 10.0)
        item.start_arrow = entry.get("start_arrow", "none")
        item.end_arrow = entry.get("end_arrow", "none")
        item.start_arrow_size = entry.get("start_arrow_size", 1.0)
        item.end_arrow_size = entry.get("end_arrow_size", 1.0)
        item.corner_radius = entry.get("corner_radius", 0.0)
        item._position_handles()
    elif kind == "image":
        item = ImageItem(QRectF(*entry["rect"]))
        item.file_path = entry.get("file_path", "")
    elif kind == "mask":
        item = MaskItem()
        item._nodes = _nodes_from_json(entry["nodes"])
        item._rebuild_handles()
        item.fill_color = _color_from_json(entry.get("fill"), "#DCEBFF")
        item.border_color = _color_from_json(entry.get("border"), "#202020")
        item.border_width = entry.get("border_width", 2)
        item.line_style = entry.get("line_style", "solid")
        item.dash_length = entry.get("dash_length", 10.0)
    elif kind == "beziergon":
        item = BeziergonItem()
        item._nodes = _nodes_from_json(entry["nodes"])
        item._rebuild_handles()
        item.fill_color = _color_from_json(entry["fill"])
        item.border_color = _color_from_json(entry["border"])
        item.border_width = entry["border_width"]
        item.line_style = entry.get("line_style", "solid")
        item.dash_length = entry.get("dash_length", 10.0)
    elif kind == "bezierline":
        item = BezierlineItem()
        item._nodes = _nodes_from_json(entry["nodes"])
        item._rebuild_handles()
        item.pen_color = _color_from_json(entry["pen_color"])
        item.pen_width = entry["pen_width"]
        item.line_style = entry.get("line_style", "solid")
        item.dash_length = entry.get("dash_length", 10.0)
        item.start_arrow = entry.get("start_arrow", "none")
        item.end_arrow = entry.get("end_arrow", "none")
        item.start_arrow_size = entry.get("start_arrow_size", 1.0)
        item.end_arrow_size = entry.get("end_arrow_size", 1.0)
    elif kind == "group":
        item = GroupItem()
    else:
        return None

    # App addition (not in the manual): restore any user-placed
    # connection points (Anchor tool) - common to every item type, so
    # handled once here rather than in each branch above.
    item._custom_connection_points = [
        QPointF(x, y) for x, y in entry.get("custom_connection_points", [])
    ]

    return item


def _pos_for_target_point(item, target_point):
    """
    Back-computes the pos() to give `item` so that it ends up sitting
    at `target_point` in whatever coordinate system target_point is
    expressed in (scene coordinates for a top-level item, or the
    future parent's local coordinates for a not-yet-reparented group
    child) - accounting for the item's own rotation/flip transform.

    item.mapToParent(0, 0) - i.e. where the item's own local origin
    lands in that outer coordinate system - is item.pos() +
    item.transform().map(0, 0), not pos() alone: rotation/flip
    (DiagramItem._update_transform()) is a transform centered on the
    item's own bounding-rect center, not its local origin, so it
    shifts where (0, 0) maps to unless that center already *is*
    (0, 0). _serialize_item() saves item.scenePos() - the item's
    fully-transformed position - so restoring it means solving that
    same equation for pos() once the item's rotation/flip transform
    is already in place (call this only after rotation_angle/
    flip_horizontal/flip_vertical are set); doing it before, or using
    target_point as pos() directly, applies that offset a second time
    on top of the saved coordinate.
    """

    return target_point - item.transform().map(QPointF(0, 0))


def deserialize_scene(data, scene):
    scene.clear()
    scene.undo_stack.clear()

    # Older .pydia files do not have a document ID.  Keep the ID of the
    # newly-created tab in that case; files created by this version keep
    # their original ID so links from other open documents remain valid.
    document_id = data.get("document_id")
    if document_id:
        scene.document_id = document_id

    canvas = data.get("canvas", {})
    scene.show_grid = canvas.get("show_grid", True)
    scene.grid_x_size = canvas.get("grid_x_size", scene.GRID_SIZE)
    scene.grid_y_size = canvas.get("grid_y_size", scene.GRID_SIZE)
    scene.grid_color = QColor(canvas.get("grid_color", "#d3d3d3"))
    # Saved for real below, once every item's position has been
    # restored - see the comment where it's applied.
    saved_snap_to_grid = canvas.get("snap_to_grid", True)
    scene.snap_to_objects = canvas.get("snap_to_objects", False)
    scene.show_connection_points = canvas.get("show_connection_points", True)
    scene.background_color = QColor(canvas.get("background_color", "#ffffff"))
    scene.set_paper_settings(
        canvas.get("paper_format", getattr(scene, "paper_format", "A4")),
        canvas.get("paper_orientation", getattr(scene, "paper_orientation", "portrait")),
        canvas.get("custom_width_mm", getattr(scene, "custom_width_mm", 210.0)),
        canvas.get("custom_height_mm", getattr(scene, "custom_height_mm", 297.0)),
    )

    # DiagramItem.itemChange() snaps ItemPositionChange to the grid
    # for any item that already has a scene - which every item placed
    # below immediately does (Pass 1 adds it to `scene` before/around
    # positioning it, and Pass 2's reparented children are still
    # scene-attached throughout). Left at its saved value, that would
    # silently round every restored position (group children included)
    # to the nearest grid line, unless it happened to already sit
    # exactly on one - so it's kept off until every position below has
    # been set, then restored to the saved value once nothing more
    # will call setPos().
    scene.snap_to_grid = False

    # Rebuild the layer stack before placing any items, so assign()
    # below can look layers up by index.
    layer_manager = scene.layer_manager
    layers_data = data.get(
        "layers", [{"name": "Background", "visible": True}]
    )

    from canvas.layers import Layer
    layer_manager.layers = []

    for layer_entry in layers_data:
        layer = Layer(layer_entry.get("name", "Layer"))
        layer.visible = layer_entry.get("visible", True)
        layer_manager.layers.append(layer)

    if not layer_manager.layers:
        layer_manager.layers.append(Layer("Background"))

    layer_manager.current_index = min(
        data.get("current_layer_index", 0),
        len(layer_manager.layers) - 1
    )

    items_data = data.get("items", [])
    by_id = {}

    # Pass 1: create every item as a fresh top-level scene item, at
    # its saved absolute scene position (group children included -
    # they get reparented in pass 2, which preserves this position).
    for entry in items_data:
        item = _construct_item_from_entry(entry)

        if item is None:
            continue

        scene.addItem(item)
        # Rotation/flip first, so the item's transform is already in
        # place when _pos_for_target_point() below reads it back.
        item.rotation_angle = entry.get("rotation", 0.0)
        item.flip_horizontal = entry.get("flip_h", False)
        item.flip_vertical = entry.get("flip_v", False)
        item.scale_x = entry.get("scale_x", 1.0)
        item.scale_y = entry.get("scale_y", 1.0)
        item.custom_name = entry.get("custom_name")
        # The internal PDF link must be restored on this (top-level)
        # load path too, not only for the children of a saved group.
        item.pdf_link_target = entry.get("pdf_link_target")

        if hasattr(item, "latex_recipe"):
            item.latex_recipe = entry.get("latex_recipe")

        item.setPos(_pos_for_target_point(item, QPointF(*entry["pos"])))

        layer_index = min(
            entry.get("layer_index", 0), len(layer_manager.layers) - 1
        )
        layer_manager.assign(item, layer_manager.layers[layer_index])
        layer_manager.set_local_z(item, entry.get("local_z", 0.0))

        by_id[entry["id"]] = item

    # Pass 2: reparent group children (preserves scene position, see
    # GroupItemsCommand for the same pattern used by interactive Group).
    for entry in items_data:
        if entry.get("type") != "group":
            continue

        group = by_id[entry["id"]]

        children = [
            by_id[cid] for cid in entry.get("children", []) if cid in by_id
        ]

        for child in children:
            child.setSelected(False)
            # child.pos() is still the absolute scene position it was
            # given in Pass 1 (every item, group or not, is placed as
            # a fresh top-level item there). setParentItem() does NOT
            # adjust position to compensate - it keeps pos() as-is and
            # just reinterprets it relative to the new parent - so
            # reparenting without correction would silently double up
            # the group's own offset (group.scenePos() + child's old
            # absolute pos) on every child. Converting to the group's
            # local coordinate system first (via mapFromScene(), which
            # accounts for the group's own position *and* any
            # rotation/flip transform on it) keeps the child's true
            # scene position unchanged across the reparent - exactly
            # what interactive Group (GroupItemsCommand) gets for free
            # by starting brand-new groups at pos (0, 0).
            target_point = group.mapFromScene(child.scenePos())
            child.setParentItem(group)
            child.setPos(_pos_for_target_point(child, target_point))
            child.setFlag(child.ItemIsSelectable, False)
            child.setFlag(child.ItemIsMovable, False)

        group._children = children

    # Every position for this load is now set - safe to restore the
    # document's real snap-to-grid setting (see where it was forced
    # off, above).
    scene.snap_to_grid = saved_snap_to_grid

    # Pass 3: restore line connection bookkeeping (endpoint positions
    # are already correct from p1/p2 above; this just re-registers
    # each line with its connected shape so future moves/resizes of
    # that shape drag the line along, same as a freshly-drawn one).
    # Covers "arc"/"polyline"/"zigzagline"/"bezierline" too - all
    # share LineItem's connection mechanics (_h1/_h2/_start_conn/
    # _end_conn), either by subclassing it (Arc) or by duck-typing
    # onto the same attribute names (Polyline/Zigzagline/Bezierline -
    # see polyline_item.py/bezierline_item.py).
    for entry in items_data:
        if entry.get("type") not in (
            "line", "arc", "polyline", "zigzagline", "bezierline"
        ):
            continue

        line = by_id[entry["id"]]

        for which, key in (("p1", "start_conn"), ("p2", "end_conn")):
            conn = entry.get(key)

            if conn and conn.get("item") in by_id:
                target = by_id[conn["item"]]
                line._set_connection(which, target, conn["index"])

                handle = line._h1 if which == "p1" else line._h2
                handle.set_connected(True)

    # Re-apply after all items exist so ``Best Fit`` can follow the
    # complete content rectangle rather than the temporary empty canvas.
    scene.set_paper_settings(
        canvas.get("paper_format", getattr(scene, "paper_format", "A4")),
        canvas.get("paper_orientation", getattr(scene, "paper_orientation", "portrait")),
        canvas.get("custom_width_mm", getattr(scene, "custom_width_mm", 210.0)),
        canvas.get("custom_height_mm", getattr(scene, "custom_height_mm", 297.0)),
    )

    return list(by_id.values())


def load_scene(path, scene):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return deserialize_scene(data, scene)


def content_rect(scene, margin=20):
    from items.diagram_item import DiagramItem

    shapes = [i for i in scene.items() if isinstance(i, DiagramItem)]

    if not shapes:
        return QRectF(0, 0, 100, 100)

    rect = None

    for item in shapes:
        item_rect = item.mapRectToScene(item.boundingRect())
        rect = item_rect if rect is None else rect.united(item_rect)

    return rect.adjusted(-margin, -margin, margin, margin)


def export_rect(scene, margin=20):
    """Return the rectangle used by exports.

    A defined paper format is a fixed export boundary; ``Best Fit``
    follows the same content rectangle used by the Best Fit view command.
    """
    if getattr(scene, "paper_format", "A4") == "Best Fit":
        return content_rect(scene, margin=margin)

    paper = getattr(scene, "paper_rect", None)
    if callable(paper):
        return paper()
    return content_rect(scene, margin=margin)


def _set_line_handles_visible(scene, visible):
    from items.line_item import LineItem
    from items.arc_item import ArcItem
    from items.polyline_item import PolylineItem
    from items.bezierline_item import BezierlineItem

    for item in scene.items():
        if isinstance(item, (LineItem, PolylineItem, BezierlineItem)):
            item._h1.setVisible(visible)
            item._h2.setVisible(visible)

            if isinstance(item, ArcItem):
                item._h3.setVisible(visible)

            if isinstance(item, PolylineItem):
                # Interior bend handles too - Line/Arc only ever have
                # the two endpoints, but Polyline/Zigzagline can have
                # more.
                for handle in item._vertex_handles:
                    handle.setVisible(visible)

            if isinstance(item, BezierlineItem):
                for handle in item._anchor_handles:
                    handle.setVisible(visible)

                for handle in item._control_handle_map.values():
                    handle.setVisible(visible)


def export_png(scene, path, scale=2.0):
    """
    Renders just the diagram's content (not the full 3000x2000 canvas,
    and not the background grid) to a PNG - manual 8.2.3.
    """

    source_rect = export_rect(scene)

    image = QImage(
        max(int(source_rect.width() * scale), 1),
        max(int(source_rect.height() * scale), 1),
        QImage.Format_ARGB32,
    )
    # Manual 3.4: the diagram's background color (white by default)
    # carries over into exports, same as the on-canvas appearance.
    image.fill(getattr(scene, "background_color", QColor("#ffffff")))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    scene.export_mode = True
    previous_selection = scene.selectedItems()
    scene.clearSelection()
    _set_line_handles_visible(scene, False)

    try:
        scene.render(
            painter,
            QRectF(0, 0, image.width(), image.height()),
            source_rect,
        )
    finally:
        scene.export_mode = False
        _set_line_handles_visible(scene, True)

        for item in previous_selection:
            item.setSelected(True)

    painter.end()

    return image.save(path, "PNG")


def _collect_pdf_links(containers, page_map):
    """Collect internal PDF links from the diagrams in export order.

    Each DiagramItem stores only the target document ID.  This function
    resolves that ID to the actual PDF page number and calculates the
    clickable rectangle in PDF points.
    """
    links = []
    missing_target = False

    for source_page, container in enumerate(containers):
        scene = container.scene
        source_rect = export_rect(scene)

        for item in scene.items():
            target_id = getattr(item, "pdf_link_target", None)
            if not target_id:
                continue

            target_page = page_map.get(target_id)
            if target_page is None:
                missing_target = True
                continue

            # mapRectToScene() correctly handles item rotation/flip and
            # parent/group transforms.  PDF coordinates use points,
            # while the QGraphicsScene export uses 96 DPI pixels.
            scene_rect = item.mapRectToScene(item.boundingRect())
            x = (scene_rect.left() - source_rect.left()) * 0.75
            y = (scene_rect.top() - source_rect.top()) * 0.75
            w = scene_rect.width() * 0.75
            h = scene_rect.height() * 0.75

            if w <= 0 or h <= 0:
                continue

            links.append({
                "source_page": source_page,
                "target_page": target_page,
                "rect_top_left": (x, y, x + w, y + h),
            })

    return links, missing_target


def _add_internal_pdf_links(path, links):
    """Add invisible internal GoTo annotations to an existing PDF.

    pypdf 5.x represents an internal link with a Link annotation whose
    target_page_index is the zero-based page index.  The source rectangle
    is converted from the top-left coordinate system used by Qt to the
    bottom-left coordinate system used by PDF.
    """
    if not links:
        return

    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.annotations import Link
    except ImportError as exc:
        raise RuntimeError(
            "Internal PDF links require the 'pypdf' package. "
            "Install it with: pip install pypdf"
        ) from exc

    reader = PdfReader(path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    for link in links:
        source_page = link["source_page"]
        target_page = link["target_page"]
        x1, y1, x2, y2 = link["rect_top_left"]

        page_height = float(reader.pages[source_page].mediabox.height)
        pdf_rect = (
            x1,
            page_height - y2,
            x2,
            page_height - y1,
        )

        writer.add_annotation(
            source_page,
            Link(
                rect=pdf_rect,
                target_page_index=target_page,
            ),
        )

    # pypdf writes Link(target_page_index=N) as /Dest [N /Fit], with a bare
    # integer as the page.  The PDF specification only allows an integer
    # page in *remote* go-to destinations; an internal link must point at
    # the page object itself, and viewers such as Acrobat ignore the
    # integer form.  Replace each integer with a reference to the page.
    from pypdf.generic import NumberObject

    for page in writer.pages:
        for annotation_ref in page.get("/Annots") or []:
            annotation = annotation_ref.get_object()
            destination = annotation.get("/Dest")
            if (
                destination is not None
                and len(destination) > 0
                and isinstance(destination[0], NumberObject)
            ):
                destination[0] = writer.pages[
                    int(destination[0])
                ].indirect_reference

    temp_path = path + ".pdf_link_tmp"
    try:
        with open(temp_path, "wb") as output:
            writer.write(output)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def export_pdf(containers, path):
    """Write one vector PDF page per document container, in export order.

    Containers are passed instead of bare scenes so the exporter can map
    each item's persistent ``document_id`` to the user's final PDF page
    order and add internal page-link annotations after QPdfWriter has
    finished the vector rendering.
    """

    from PyQt5.QtCore import QMarginsF, QSizeF
    from PyQt5.QtGui import QPageSize, QPdfWriter

    if not containers:
        return False

    # The page map is deliberately built from the user's selected order.
    page_map = {
        getattr(container, "document_id", None): page_number
        for page_number, container in enumerate(containers)
        if getattr(container, "document_id", None)
    }

    links, missing_target = _collect_pdf_links(containers, page_map)
    if missing_target:
        raise ValueError(
            "One or more PDF links point to a document that is not included "
            "in the selected PDF export. Include the destination document "
            "in the export order and try again."
        )

    writer = QPdfWriter(path)
    writer.setResolution(96)
    writer.setTitle("PyDiagram export")

    painter = None

    try:
        for container in containers:
            scene = container.scene
            source_rect = export_rect(scene)

            writer.setPageSize(
                QPageSize(
                    QSizeF(source_rect.width() * 0.75, source_rect.height() * 0.75),
                    QPageSize.Point,
                )
            )
            writer.setPageMargins(QMarginsF(0, 0, 0, 0))

            if painter is None:
                painter = QPainter(writer)
                painter.setRenderHint(QPainter.Antialiasing)
            else:
                writer.newPage()

            scene.export_mode = True
            previous_selection = scene.selectedItems()
            scene.clearSelection()
            _set_line_handles_visible(scene, False)

            try:
                with _SuppressPorterDuffWarning():
                    scene.render(
                        painter,
                        QRectF(0, 0, source_rect.width(), source_rect.height()),
                        source_rect,
                    )
            finally:
                scene.export_mode = False
                _set_line_handles_visible(scene, True)

                for item in previous_selection:
                    item.setSelected(True)
    finally:
        if painter is not None:
            painter.end()

    # QPdfWriter has now closed the document.  Add standard PDF Link
    # annotations in a second pass so the original vector rendering is
    # left untouched.
    _add_internal_pdf_links(path, links)

    return True


def export_svg(scene, path):
    from PyQt5.QtSvg import QSvgGenerator

    source_rect = export_rect(scene)

    generator = QSvgGenerator()
    generator.setFileName(path)
    generator.setSize(source_rect.size().toSize())
    generator.setViewBox(QRectF(0, 0, source_rect.width(), source_rect.height()))
    generator.setTitle("PyDiagram export")

    painter = QPainter(generator)
    painter.setRenderHint(QPainter.Antialiasing)

    scene.export_mode = True
    previous_selection = scene.selectedItems()
    scene.clearSelection()
    _set_line_handles_visible(scene, False)
    # Unlike export_png() (which explicitly fills the PNG with the
    # diagram's background color to match the on-canvas appearance),
    # an SVG export should have a transparent background. drawBackground()
    # unconditionally fillRect()s with scene.background_color regardless
    # of export_mode, so blank it out for the duration of the render.
    previous_background = scene.background_color
    scene.background_color = QColor(0, 0, 0, 0)

    try:
        with _SuppressPorterDuffWarning():
            scene.render(
                painter,
                QRectF(0, 0, source_rect.width(), source_rect.height()),
                source_rect,
            )
    finally:
        scene.export_mode = False
        scene.background_color = previous_background
        _set_line_handles_visible(scene, True)

        for item in previous_selection:
            item.setSelected(True)

    painter.end()

    return True


def export_items_svg(scene, items, path):
    """
    Same idea as export_svg(), but scoped to just `items` (each
    already on `scene`) rather than the whole diagram - used to
    render a custom shape's toolbox icon (app/custom_shapes.py:
    Objects -> Save as New Shape...) without every other shape on the
    canvas bleeding into it.

    QGraphicsScene.render() draws everything under source_rect, not
    just the items we ask for, so every other top-level DiagramItem
    is hidden for the duration of the render (hiding a GroupItem
    hides its children too, via Qt's normal visibility propagation)
    and restored again afterwards, success or failure.
    """

    from PyQt5.QtSvg import QSvgGenerator
    from items.diagram_item import DiagramItem

    if not items:
        return False

    source_rect = None

    for item in items:
        item_rect = item.mapRectToScene(item.boundingRect())
        source_rect = (
            item_rect if source_rect is None else source_rect.united(item_rect)
        )

    margin = 6
    source_rect = source_rect.adjusted(-margin, -margin, margin, margin)

    generator = QSvgGenerator()
    generator.setFileName(path)
    generator.setSize(source_rect.size().toSize())
    generator.setViewBox(QRectF(0, 0, source_rect.width(), source_rect.height()))
    generator.setTitle("PyDiagram shape")

    painter = QPainter(generator)
    painter.setRenderHint(QPainter.Antialiasing)

    keep_visible = set(items)
    others = [
        i for i in scene.items()
        if isinstance(i, DiagramItem)
        and i.parentItem() is None
        and i not in keep_visible
    ]
    hidden = [i for i in others if i.isVisible()]

    for i in hidden:
        i.setVisible(False)

    scene.export_mode = True
    previous_selection = scene.selectedItems()
    scene.clearSelection()
    _set_line_handles_visible(scene, False)
    # See export_svg(): SVG exports should be transparent, not carry
    # the diagram's background color.
    previous_background = scene.background_color
    scene.background_color = QColor(0, 0, 0, 0)

    try:
        with _SuppressPorterDuffWarning():
            scene.render(
                painter,
                QRectF(0, 0, source_rect.width(), source_rect.height()),
                source_rect,
            )
    finally:
        scene.export_mode = False
        scene.background_color = previous_background
        _set_line_handles_visible(scene, True)

        for i in hidden:
            i.setVisible(True)

        for item in previous_selection:
            item.setSelected(True)

    painter.end()

    return True
