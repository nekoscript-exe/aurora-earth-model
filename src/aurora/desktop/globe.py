"""AURORA — Interactive planetary observation explorer."""

from .i18n import tr

import json
import time
import numpy as np
from .temporal import TemporalSelector
from aurora.temporal import select_interval
from aurora.catalog import ObservationSeries, populate_regions, populate_variables, display_scale
from .tasks import ReaderJobs

from rasterio.features import rasterize, bounds as geometry_bounds
from rasterio.transform import from_bounds
from .geospatial import (RasterGrid, load_observations,
                         orthographic_inverse, orthographic_forward)

from matplotlib import colormaps

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QVariantAnimation, QEasingCurve, QAbstractAnimation
from PySide6.QtGui import QPainter, QImage, QColor, QPen, QPainterPath, QLinearGradient
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSlider, QCheckBox, QProgressBar, QSplitter, QScrollArea
)


SCALES = {
    "ndvi": (-0.2, 1.0, "RdYlGn", "NDVI · dimensionless"),
    "lst": (-10.0, 70.0, "turbo", "LST · °C"),
}


class ColorLegend(QWidget):
    """Same fixed scale as the raster; tails are clipped, never rescaled per date."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.variable = "ndvi"
        self.scales = dict(SCALES)
        self.setMinimumHeight(88)

    def paintEvent(self, event):
        low, high, name, unit = self.scales[self.variable]
        painter = QPainter(self)
        painter.setPen(QColor("#bacbd8"))
        painter.drawText(0, 15, unit)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        for t in np.linspace(0, 1, 33):
            color = colormaps[name](t)
            gradient.setColorAt(float(t), QColor.fromRgbF(*color[:3]))
        painter.fillRect(QRectF(0, 25, self.width(), 16), gradient)
        painter.drawText(0, 57, f"≤ {low:g}")
        painter.drawText(self.width()//2-20, 57, f"{(low+high)/2:g}")
        painter.drawText(self.width()-50, 57, f"≥ {high:g}")
        painter.drawText(0, 79, "NoData / QA / outside region: transparent")


class Planet(QWidget):

    def __init__(self, root, parent=None):
        super().__init__(parent)

        self.setMinimumSize(320, 300)
        self.setToolTip("Drag: rotate · Wheel: zoom · Double-click: place a WGS84 pin")
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self.lon = -100.0
        self.lat = 20.0
        self.zoom = 1.0
        self.opacity = 0.90
        self.grid = True
        self.daylight = True

        self.drag = None
        self.image = None
        self.dirty = True

        self.frame = None
        self.variable = "ndvi"
        self.scales = dict(SCALES)

        self.mapping = None
        self.base = None
        self.paths = None
        self.borders = True
        self.markers = True
        self.locations = [("Querétaro", -100.3899, 20.5888),
                          ("Mexico City", -99.1332, 19.4326)]
        self.pins = []
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(650)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.valueChanged.connect(self.animate_camera)
        self.animation.finished.connect(lambda: self.invalidate(camera=True))
        self.camera_start = None

        path = root / "assets/desktop/geography/land_50m.geojson"
        features = json.loads(path.read_text())["features"]

        self.land_shapes = [f["geometry"] for f in features]
        self.land_bounds = np.array([geometry_bounds(g) for g in self.land_shapes])
        self.land = rasterize(
            [(f["geometry"], 1) for f in features],
            out_shape=(1800, 3600),
            transform=from_bounds(
                -180, -90, 180, 90, 3600, 1800
            ),
            fill=0,
            dtype="uint8"
        )

        self.rotation = QTimer(self)
        self.boundary_lines = []
        self.coast_lines = []
        for feature in features:
            geometry = feature["geometry"]
            polygons = ([geometry["coordinates"]] if geometry["type"] == "Polygon"
                        else geometry["coordinates"])
            self.coast_lines.extend(ring for polygon in polygons for ring in polygon)
        for filename in ("countries.geojson", "states.geojson", "states_mexico.geojson"):
            collection = json.loads((path.parent/filename).read_text())
            lines = []
            for feature in collection["features"]:
                geometry = feature["geometry"]
                if geometry["type"] == "LineString":
                    lines.append(geometry["coordinates"])
                elif geometry["type"] == "MultiLineString":
                    lines.extend(geometry["coordinates"])
            self.boundary_lines.append(lines)
        self.coast_lines = self.prepare_lines(self.coast_lines)
        self.boundary_lines = [self.prepare_lines(lines) for lines in self.boundary_lines]
        self.rotation.setInterval(33)
        self.rotation.timeout.connect(self.rotate)

        self.render_size = None
        self.last_rotation = time.monotonic()

    def invalidate(self, camera=False):

        if camera:
            self.mapping = None
            self.base = None
            self.paths = None

        self.dirty = True
        self.update()

    def focus(self, lon, lat, zoom):
        self.animation.stop()
        self.camera_start = (self.lon, self.lat, self.zoom)
        delta = (lon-self.lon+180) % 360-180
        self.camera_end = (self.lon+delta, lat, float(np.clip(zoom, .75, 100)))
        self.animation.start()

    def animate_camera(self, value):
        if self.camera_start is None:
            return
        a, b = self.camera_start, self.camera_end
        self.lon = (a[0]+(b[0]-a[0])*value+180) % 360-180
        self.lat = a[1]+(b[1]-a[1])*value
        self.zoom = float(np.exp(np.log(a[2])*(1-value)+np.log(b[2])*value))
        self.invalidate(camera=True)

    def rotate(self):
        now = time.monotonic()
        elapsed = min(now-self.last_rotation, .1)
        self.last_rotation = now
        if self.isVisible() and self.drag is None and self.animation.state() == QAbstractAnimation.State.Stopped:
            self.lon = (self.lon+5*elapsed+180) % 360-180
            self.invalidate(camera=True)

    def set_rotation(self, enabled):

        if enabled:
            self.last_rotation = time.monotonic()
            self.rotation.start()
        else:
            self.rotation.stop()
            self.invalidate(camera=True)

    def mousePressEvent(self, event):

        if event.button() == Qt.MouseButton.LeftButton:
            self.animation.stop()
            self.drag = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):

        if self.drag is None:
            return

        delta = event.position() - self.drag
        self.drag = event.position()

        self.lon = (
            self.lon - delta.x() * 0.35 / self.zoom + 180
        ) % 360 - 180

        self.lat = float(np.clip(
            self.lat + delta.y() * 0.35 / self.zoom,
            -89, 89
        ))

        self.invalidate(camera=True)

    def mouseReleaseEvent(self, event):

        self.drag = None
        self.invalidate(camera=True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def wheelEvent(self, event):

        delta = event.angleDelta().y()/120
        if delta:
            target = self.camera_end[2] if self.animation.state() == QAbstractAnimation.State.Running else self.zoom
            self.focus(self.lon, self.lat, target*1.18**delta)
            event.accept()

    def set_dataset(self, frame, metadata, variable):
        self.raster_grid = RasterGrid.from_metadata(metadata, frame.shape)
        self.variable = variable
        self.frame = frame
        self.invalidate(camera=True)

    def set_frame(self, frame):

        if frame.shape != (self.raster_grid.height, self.raster_grid.width):
            raise ValueError("Frame shape changed within dataset")
        self.frame = frame
        self.invalidate()

    def clear_layer(self):

        self.frame = None
        self.invalidate(camera=True)

    def build_mapping(self):

        if self.render_size is None:
            raise ValueError("Render dimensions have not been initialized")
        width, height = self.render_size
        return self.raster_grid.orthographic_mapping(
            width, height, self.lon, self.lat, self.zoom)

    def render_planet(self):
        # Bound CPU work while retaining the viewport aspect and using its width.
        moving = self.drag is not None or self.animation.state() == QAbstractAnimation.State.Running or self.rotation.isActive()
        limit = 640 if moving else 960
        factor = min(1, limit/max(self.width(), self.height()))
        width, height = max(2, int(self.width()*factor)), max(2, int(self.height()*factor))
        if self.render_size != (width, height):
            self.render_size = (width, height)
            unit = min(width, height)/2
            self.xx, self.yy = np.meshgrid(
                (np.arange(width, dtype=float)+.5-width/2)/unit,
                (height/2-np.arange(height, dtype=float)-.5)/unit)
            self.mapping = self.base = self.paths = None
        if self.base is None:
            self.base, self.coordinates = self.render_base()
        rgb = self.base.copy()
        lon, lat, visible, z = self.coordinates
        if self.frame is not None:
            if self.mapping is None:
                self.mapping = self.build_mapping()
            pos, rr, cc = self.mapping
            values = self.frame[rr, cc]
            valid = np.isfinite(values)
            lower, upper, name, _ = self.scales[self.variable]
            colors = colormaps[name](np.clip(
                (values[valid]-lower)/(upper-lower), 0, 1))[:, :3]*255
            flat = rgb.reshape(-1, 3)
            target = pos[valid]
            flat[target] = flat[target]*(1-self.opacity)+colors*self.opacity
        rgb = np.ascontiguousarray(np.clip(rgb, 0, 255).astype(np.uint8))
        return QImage(rgb.data, width, height, rgb.strides[0],
                      QImage.Format.Format_RGB888).copy()

    def render_base(self):
        x = self.xx/(.82*self.zoom)
        y = self.yy/(.82*self.zoom)
        lon, lat, visible = orthographic_inverse(x, y, self.lon, self.lat)
        z = np.sqrt(np.maximum(0, 1-x*x-y*y))
        rows = np.clip(
            ((90-lat)*10).astype(int), 0, 1799
        )

        cols = np.clip(
            ((lon+180)*10).astype(int), 0, 3599
        )

        land_mask = self.land
        if land_mask is None:
            raise RuntimeError("Land rasterization did not produce an array")
        land = land_mask[rows, cols] == 1
        # Refine the cartographic basemap at regional zoom without changing
        # scientific sampling. The global fallback safely handles the date line.
        if self.zoom >= 3 and visible.any():
            west, east = lon[visible].min(), lon[visible].max()
            south, north = lat[visible].min(), lat[visible].max()
            if 0 < east-west < 120 and 0 < north-south < 80:
                height, width = lon.shape
                west, east = west-1e-5, east+1e-5
                south, north = south-1e-5, north+1e-5
                bounds = self.land_bounds
                intersects = ((bounds[:, 0] <= east) & (bounds[:, 2] >= west)
                              & (bounds[:, 1] <= north) & (bounds[:, 3] >= south))
                shapes = [(self.land_shapes[i], 1) for i in np.flatnonzero(intersects)]
                if shapes:
                    local = rasterize(shapes, out_shape=(height, width),
                                      transform=from_bounds(west, south, east, north,
                                                            width, height),
                                      fill=0, dtype="uint8")
                    rr = np.clip(((north-lat)/(north-south)*height).astype(int), 0, height-1)
                    cc = np.clip(((lon-west)/(east-west)*width).astype(int), 0, width-1)
                    if local is None:
                        raise RuntimeError("Regional land rasterization did not produce an array")
                    land = local[rr, cc] == 1
                else:
                    land[:] = False

        rgb = np.empty((*lon.shape, 3), dtype=np.float32)

        rgb[:] = [13, 39, 58]
        rgb[land] = [36, 91, 80]

        if self.daylight:
            light = 0.46 + 0.54*np.clip(
                0.8*z - 0.35*x + 0.35*y, 0, 1
            )
            rgb *= light[..., None]

        if self.grid:

            interval = 30 if self.zoom < 3 else (
                5 if self.zoom < 20 else 0.5
            )

            dlat = np.abs((lat+interval/2) % interval-interval/2)
            dlon = np.abs((lon+interval/2) % interval-interval/2)
            lat_step = np.hypot(*np.gradient(lat))
            lon_dx = ((np.roll(lon, -1, 1)-np.roll(lon, 1, 1)+180) % 360-180)/2
            lon_dy = ((np.roll(lon, -1, 0)-np.roll(lon, 1, 0)+180) % 360-180)/2
            lon_step = np.hypot(lon_dx, lon_dy)
            distance = np.minimum(dlat/np.maximum(lat_step, 1e-8),
                                  dlon/np.maximum(lon_step, 1e-8))
            weight = (np.clip(1.1-distance, 0, 1)*visible*.4)[..., None]
            rgb = rgb*(1-weight)+np.array([130, 190, 184])*weight

        rgb[~visible] = [8, 14, 23]
        # A restrained atmosphere gradient; illumination is illustrative only.
        rim = np.clip((.16-z)/.16, 0, 1)*visible
        rgb += rim[..., None]*np.array([22, 65, 78])
        return rgb, (lon, lat, visible, z)

    def resizeEvent(self, event):
        self.invalidate(camera=True)
        super().resizeEvent(event)

    def screen_point(self, lon, lat):
        x, y, front = orthographic_forward(lon, lat, self.lon, self.lat)
        scale = min(self.width(), self.height())*.41*self.zoom
        return self.width()/2+x*scale, self.height()/2-y*scale, front

    @staticmethod
    def prepare_lines(lines):
        result = []
        for line in lines:
            points = np.asarray(line, dtype=float)
            segments = []
            for a, b in zip(points[:-1], points[1:]):
                delta = b-a
                delta[0] = (delta[0]+180) % 360-180
                count = max(1, int(np.ceil(np.max(np.abs(delta))/.25)))
                segments.append(a+np.arange(count)[:, None]/count*delta)
            if segments:
                result.append(np.vstack([*segments, points[-1:], [[np.nan, np.nan]]]))
        return np.vstack(result) if result else np.empty((0, 2))

    def line_path(self, lines):
        path = QPainterPath()
        points = lines
        x, y, front = self.screen_point(points[:, 0], points[:, 1])
        in_view = front & (x >= -10) & (x <= self.width()+10) & (y >= -10) & (y <= self.height()+10)
        # Include immediate neighbours so clipping doesn't cut crossing edges.
        keep = in_view | np.r_[False, in_view[:-1]] | np.r_[in_view[1:], False]
        previous = -2
        for i in np.flatnonzero(keep & front):
            if i == previous+1:
                path.lineTo(float(x[i]), float(y[i]))
            else:
                path.moveTo(float(x[i]), float(y[i]))
            previous = i
        return path

    def mouseDoubleClickEvent(self, event):
        scale = min(self.width(), self.height())*.41*self.zoom
        lon, lat, visible = orthographic_inverse(
            (event.position().x()-self.width()/2)/scale,
            (self.height()/2-event.position().y())/scale, self.lon, self.lat)
        if visible:
            self.pins.append((f"Pin {len(self.pins)+1}", float(lon), float(lat)))
            self.setToolTip(f"Pin {len(self.pins)} · WGS84 · {float(lat):.5f}°, {float(lon):.5f}°")
            self.update()

    def paintEvent(self, event):

        if self.dirty or self.image is None:
            self.image = self.render_planet()
            self.dirty = False

        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawImage(QRectF(self.rect()), self.image)
        if self.paths is None:
            self.paths = [self.line_path(self.coast_lines)]
            self.paths.extend(self.line_path(lines) for lines in self.boundary_lines)
        painter.setPen(QPen(QColor("#538a88"), .8))
        painter.drawPath(self.paths[0])
        if self.borders:
            painter.setPen(QPen(QColor("#c3d7d8"), 1.0))
            painter.drawPath(self.paths[1])
            if self.zoom >= 2:
                painter.setPen(QPen(QColor("#759999"), .8))
                painter.drawPath(self.paths[2])
                painter.drawPath(self.paths[3])
        if self.markers:
            label_boxes = []
            for label, lon, lat in self.locations+self.pins:
                x, y, front = self.screen_point(lon, lat)
                if front and 0 <= x <= self.width() and 0 <= y <= self.height():
                    painter.setPen(QPen(QColor("#080e17"), 2))
                    painter.setBrush(QColor("#69d9bd"))
                    painter.drawEllipse(QPointF(float(x), float(y)), 4, 4)
                    painter.setPen(QColor("#e7edf5"))
                    for offset in (-8, 22, -28):
                        box = QRectF(painter.fontMetrics().boundingRect(label))
                        box.moveBottomLeft(QPointF(float(x)+8, float(y)+offset))
                        if self.rect().contains(box.toRect()) and not any(
                                box.intersects(other) for other in label_boxes):
                            painter.fillRect(box.adjusted(-2, -1, 2, 1), QColor(8, 14, 23, 190))
                            painter.drawText(box, Qt.AlignmentFlag.AlignLeft, label)
                            label_boxes.append(box)
                            break
        painter.setPen(Qt.GlobalColor.white)

        painter.drawText(
            14, self.height()-14,
            f"LAT {self.lat:.3f}°  |  "
            f"LON {self.lon:.3f}°  |  "
            f"ZOOM {self.zoom:.1f}x"
        )

        painter.end()


class PlanetaryExplorer(QWidget):

    def __init__(self, root, parent=None):
        super().__init__(parent)

        from .theme import STYLE
        self.setStyleSheet(STYLE)
        self.root = root
        self.reader_jobs = ReaderJobs(self, self.read_ready, self.read_error)
        self.values = None
        self.dates = None

        layout = QVBoxLayout(self)

        title = QLabel(tr('Planetary Explorer'))
        title.setStyleSheet(
            "font-size:27px;font-weight:bold;color:#69d9bd;"
        )
        title_row = QHBoxLayout()
        title_row.addWidget(title)
        title_row.addStretch()
        self.setup_toggle = QPushButton(tr('Investigation setup'))
        self.setup_toggle.setCheckable(True)
        self.setup_toggle.setToolTip("Toggle the scientific investigation controls")
        self.setup_toggle.hide()  # Enabled by the host window.
        title_row.addWidget(self.setup_toggle)
        layout.addLayout(title_row)

        layout.addWidget(QLabel(
            "Drag to rotate · Scroll to zoom · Explore satellite history"
        ))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)
        scene = QWidget()
        scene_layout = QVBoxLayout(scene)
        scene_layout.setContentsMargins(0, 0, 8, 0)
        splitter.addWidget(scene)
        sidebar = QWidget()
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 0, 10, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(300)
        scroll.setWidget(sidebar)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([900, 320])
        navigation = QHBoxLayout()

        self.planet = Planet(root, self)

        for name, lon, lat, zoom in [
            ("Earth", -100, 20, 1),
            ("Mexico", -102.5, 23.6, 4),
            ("Queretaro", -99.9, 20.85, 48)
        ]:
            button = QPushButton(name)
            button.clicked.connect(
                lambda _, a=lon,b=lat,c=zoom:
                    self.planet.focus(a,b,c)
            )
            navigation.addWidget(button)

        scene_layout.addLayout(navigation)
        scene_layout.addWidget(self.planet, 1)
        hint = QLabel("Double-click to place a pin · Lighting is illustrative")
        hint.setWordWrap(True)
        scene_layout.addWidget(hint)

        controls = QVBoxLayout()

        self.region = QComboBox()
        self.registry = populate_regions(self.region, root)

        self.variable = QComboBox()
        self.variable.addItem("NDVI", "ndvi")
        self.variable.addItem("LST", "lst")

        populate_variables(self.variable, self.registry, self.region.currentData(), preserve=False)

        load = QPushButton(tr('Load observations'))
        load.clicked.connect(lambda _: self.load_dataset(asynchronous=True))

        for widget in [self.region, self.variable, load]:
            controls.addWidget(widget)

        layout.addLayout(controls)
        self.read_progress = QProgressBar(); self.read_progress.setRange(0, 0); self.read_progress.hide()
        self.cancel_read_button = QPushButton(tr('Cancel loading')); self.cancel_read_button.setEnabled(False)
        self.cancel_read_button.clicked.connect(self.cancel_read)
        layout.addWidget(self.read_progress); layout.addWidget(self.cancel_read_button)


        settings = QVBoxLayout()

        rotation = QCheckBox("Auto rotate")
        rotation.toggled.connect(self.planet.set_rotation)

        grid = QCheckBox("Grid")
        grid.setChecked(True)
        grid.toggled.connect(self.set_grid)

        light = QCheckBox("Lighting")
        light.setChecked(True)
        light.toggled.connect(self.set_light)

        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity.setValue(90)
        self.opacity.valueChanged.connect(self.set_opacity)

        for widget in [rotation, grid, light, QLabel(tr('Opacity'))]:
            settings.addWidget(widget)

        self.opacity_value = QLabel("90%")
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self.opacity, 1)
        opacity_row.addWidget(self.opacity_value)
        settings.addLayout(opacity_row)
        borders = QCheckBox("Country / state boundaries")
        borders.setChecked(True)
        borders.toggled.connect(lambda enabled: self.set_overlay("borders", enabled))
        markers = QCheckBox("Geographic markers")
        markers.setChecked(True)
        markers.toggled.connect(lambda enabled: self.set_overlay("markers", enabled))
        clear_pins = QPushButton(tr('Clear user pins'))
        clear_pins.clicked.connect(self.clear_pins)
        for widget in (borders, markers, clear_pins):
            settings.addWidget(widget)
        self.legend = ColorLegend()
        layout.addWidget(self.legend)

        layout.addLayout(settings)

        self.period = TemporalSelector()
        layout.addWidget(self.period.create_toggle())
        layout.addWidget(self.period)
        self.period.changed.connect(self.apply_period)

        self.date = QLabel(tr('No observations loaded'))
        self.date.setWordWrap(True)
        self.date.setStyleSheet(
            "font-size:20px;font-weight:bold;color:#69d9bd;"
        )
        layout.addWidget(self.date)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.valueChanged.connect(self.render_frame)
        layout.addWidget(self.slider)

        playback = QHBoxLayout()

        self.previous = previous = QPushButton("‹")
        previous.setToolTip("Previous observation")
        previous.clicked.connect(lambda: self.step(-1))

        self.play = QPushButton(tr('Play'))
        self.play.clicked.connect(self.toggle_play)

        self.following = following = QPushButton("›")
        following.setToolTip("Next observation")
        following.clicked.connect(lambda: self.step(1))

        self.speed = QComboBox()

        for label, ms in [
            ("0.5x",1000), ("1x",500),
            ("2x",250), ("4x",125)
        ]:
            self.speed.addItem(label,ms)

        self.speed.setCurrentIndex(1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: self.step(1))

        self.speed.currentIndexChanged.connect(
            lambda _: self.timer.setInterval(
                self.speed.currentData()
            )
        )

        for widget in [
            previous, self.play, following, self.speed
        ]:
            playback.addWidget(widget)

        layout.addLayout(playback)

        self.details = QLabel(
            "Geography: Natural Earth | "
            "Scientific observations: NASA Terra / MODIS"
        )
        self.details.setWordWrap(True)
        layout.addWidget(self.details)

        self.region.currentIndexChanged.connect(self.region_changed)
        self.variable.currentIndexChanged.connect(self.reset)
        layout.addStretch(1)
        self.reset()

    def set_overlay(self, name, enabled):
        setattr(self.planet, name, enabled)
        self.planet.update()

    def clear_pins(self):
        self.planet.pins.clear()
        self.planet.update()

    def set_temporal_controls(self, enabled):
        for widget in (self.slider, self.previous, self.following, self.play, self.speed):
            widget.setEnabled(enabled)

    def set_opacity(self, value):
        self.opacity_value.setText(f"{value}%")
        self.planet.opacity = value / 100
        self.planet.invalidate()

    def set_grid(self, enabled):
        self.planet.grid = enabled
        self.planet.invalidate(camera=True)

    def set_light(self, enabled):
        self.planet.daylight = enabled
        self.planet.invalidate(camera=True)

    def pause(self):
        self.timer.stop()
        self.play.setText(tr('Play'))

    def hideEvent(self, event):
        self.pause()
        super().hideEvent(event)

    def reset(self, *_):

        self.reader_jobs.cancel_all()
        self.set_read_busy(False)
        self.pause()
        self.values = None
        self.dates = None
        self.period.set_dates([])
        self.set_temporal_controls(False)
        variable = self.variable.currentData()
        try: self.planet.scales[variable] = self.legend.scales[variable] = display_scale(self.registry.find(self.region.currentData(), variable).metadata)
        except FileNotFoundError: pass
        self.legend.variable = variable
        self.legend.update()
        self.planet.clear_layer()
        self.slider.setRange(0, 0)
        self.date.setText(tr('No observations loaded'))
        self.details.setText(tr('Load the selected dataset.'))

    def load_dataset(self, asynchronous=False):

        self.reset()

        region = self.region.currentData()
        variable = self.variable.currentData()

        try:
            record = self.registry.find(region, variable)
            self.planet.scales[variable] = self.legend.scales[variable] = display_scale(record.metadata)
            if asynchronous:
                self.details.setText("Opening observed data in background…")
                def read(check):
                    series = ObservationSeries(record.directory, variable, check=check)
                    series[0]
                    return series
                self.set_read_busy(True)
                self.reader_jobs.start('dataset', read)
                return
            self.attach_series(ObservationSeries(record.directory, variable))
        except Exception as exc:
            self.read_error(str(exc))

    def attach_series(self, series):
            self.values = series
            variable = self.variable.currentData()
            self.dates, self.mask = self.values.dates, self.values.mask
            metadata = self.values.metadata
            self.provenance = f"{metadata['source']} · {metadata['grid']['crs']} · display stride {self.values.stride}"
            self.planet.set_dataset(
                self.values[0], metadata, variable
            )

            self.slider.blockSignals(True)
            self.slider.setRange(0, len(self.dates)-1)
            self.slider.setValue(0)
            self.slider.blockSignals(False)

            grid = self.values.reader.grid
            x, y = grid.affine @ (grid.width/2, grid.height/2)
            from rasterio.warp import transform
            projected = transform(grid.crs, "EPSG:4326", [x], [y])
            lon, lat = projected[0], projected[1]
            self.planet.focus(lon[0], lat[0], min(48, max(1, 8000/max(grid.width, grid.height))))

            self.period.set_dates(self.dates)
            self.set_temporal_controls(True)
            self.render_frame(0)


    def region_changed(self, *_):
        populate_variables(self.variable, self.registry, self.region.currentData())
        self.reset()

    def read_error(self, message):
        self.reset(); self.details.setText(f"Dataset unavailable: {message}")

    def read_ready(self, kind, value):
        self.set_read_busy(False)
        if kind == 'dataset': self.attach_series(value)
        else: self.apply_frame(*value)

    def render_frame(self, index):

        if self.values is None:
            return

        if self.values.reader.format == 'zarr' or self.values.mask.size > 262144:
            series = self.values
            self.set_read_busy(True)
            self.reader_jobs.start('frame', lambda check: (index, series[index]))
            return
        self.apply_frame(index, self.values[index])

    def apply_frame(self, index, frame):
        if self.values is None or self.dates is None:
            return
        if not 0 <= index < len(self.dates):
            return
        self.planet.set_frame(frame)

        finite = frame[np.isfinite(frame)]
        weighted_mean, coverage = self.values.summary(frame)
        mean = f"{weighted_mean:.4f}" if weighted_mean is not None else "N/A"

        unit = self.values.spec.identifier+" · "+self.values.spec.unit

        scale = (
            f"{self.planet.scales[self.variable.currentData()][0]} to {self.planet.scales[self.variable.currentData()][1]}"
        )

        self.date.setText(
            f"{self.dates[index]}  |  "
            f"{index+1}/{len(self.dates)}"
        )

        self.details.setText(
            f"{self.provenance}\n{unit} | Valid pixels: {finite.size:,} | "
            f"Coverage: {coverage:.2%} | Mean: {mean} (area weighted)\n"
            f"Fixed scale: {scale} | "
            "Missing observations remain uncolored."
        )

    def apply_period(self):
        if self.values is None or not len(self.period.dates):
            return
        try:
            selected = select_interval(self.dates, *self.period.interval())
        except ValueError:
            return
        indices = np.flatnonzero(selected)
        self.pause()
        self.slider.setRange(int(indices[0]), int(indices[-1]))
        self.slider.setValue(int(indices[0]))

    def step(self, amount):

        if self.values is not None and not self.reader_jobs.busy('frame'):
            self.slider.setValue(
                (self.slider.value()-self.slider.minimum()+amount) % (self.slider.maximum()-self.slider.minimum()+1)+self.slider.minimum()
            )

    def toggle_play(self):

        if self.values is None:
            return

        if self.timer.isActive():
            self.pause()
        else:
            self.timer.start(self.speed.currentData())
            self.play.setText(tr('Pause'))

    def set_read_busy(self, busy):
        self.read_progress.setVisible(busy); self.cancel_read_button.setEnabled(busy)

    def cancel_read(self):
        self.reset(); self.details.setText('Read cancelled; no incomplete observation displayed.')
