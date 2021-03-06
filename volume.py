"""
	volume.py (a volume control applet for the ROX Panel)

	Copyright 2004 Kenneth Hayber <ken@hayber.us>
		All rights reserved.

	This program is free software; you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation; either version 2 of the License.

	This program is distributed in the hope that it will be useful
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program; if not, write to the Free Software
	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import rox, sys, os, gtk, gobject
from rox import app_options, applet, Menu, InfoWin, OptionsBox
from rox.options import Option
from volumecontrol import VolumeControl
from options import (
    get_mixer_device, MIXER_DEVICE, VOLUME_CONTROL, SHOW_ICON, SHOW_BAR, THEME
)

try:
	import alsaaudio
except ImportError:
	rox.croak(_("You need to install the pyalsaaudio module"))

APP_DIR = rox.app_dir
APP_SIZE = [28, 150]


class Volume(applet.Applet):
	icons = []
	size = 24


	"""An applet to control a sound card Master or PCM volume"""
	def __init__(self, filename):
		applet.Applet.__init__(self, filename)
                self.set_name("VolumePanelApplet")

		self.vertical = self.get_panel_orientation() in ('Right', 'Left')
		if self.vertical:
			self.set_size_request(8, -1)
			self.box = gtk.VBox()
			bar_orient = gtk.PROGRESS_LEFT_TO_RIGHT
		else:
			self.set_size_request(-1, 8)
			self.box = gtk.HBox()
			bar_orient = gtk.PROGRESS_BOTTOM_TO_TOP

		self.add(self.box)

		self.load_icons()
		self.image = gtk.Image()
		self.box.pack_start(self.image)

		self.bar = gtk.ProgressBar()
		self.bar.set_orientation(bar_orient)
		self.bar.set_size_request(12,12)
		self.box.pack_end(self.bar)

		self.tips = gtk.Tooltips()

		rox.app_options.add_notify(self.get_options)
		self.connect('size-allocate', self.event_callback)
		self.connect('scroll_event', self.button_scroll)

		self.add_events(gtk.gdk.BUTTON_PRESS_MASK)
		self.connect('button-press-event', self.button_press)
		self.menu = Menu.Menu('main', [
			Menu.Action(_('Mixer'), 'run_mixer', ''),
			Menu.Action(_('Mute'), 'mute', ''),
			Menu.Separator(),
			Menu.Action(_('Options'), 'show_options', '', gtk.STOCK_PREFERENCES),
			Menu.Action(_('Info'), 'get_info', '', gtk.STOCK_DIALOG_INFO),
			Menu.Action(_('Close'), 'quit', '', gtk.STOCK_CLOSE),
			])
		self.menu.attach(self, self)

		self.thing = None
		try:
			self.mixer = alsaaudio.Mixer(VOLUME_CONTROL.value, 0, get_mixer_device())
		except alsaaudio.ALSAAudioError:
			rox.info(_('Failed to open Mixer device "%s". Please select a different device.\n') % get_mixer_device())
			return

		self.get_volume()
		self.update_ui()
		self.show_all()
		self.show()

		if not SHOW_ICON.int_value:
			self.image.hide()
		if not SHOW_BAR.int_value:
			self.bar.hide()

		def theme_changed(theme):
		    self.load_icons()
		    self.update_ui()
		gtk.icon_theme_get_default().connect("changed", theme_changed)

	def load_icons(self):
		self.icons = []

		if THEME.value == 'gtk-theme':

			theme = gtk.icon_theme_get_default()
			fallback_theme_dir = os.path.join(APP_DIR, 'themes', 'GnomeSVG')

			def load_icon_from_theme(icon_name):
				try:
					return theme.load_icon(icon_name, 24, 0)
				except gobject.GError:
					return gtk.gdk.pixbuf_new_from_file(os.path.join(fallback_theme_dir, '%s.svg' % icon_name))

			self.icons.append(load_icon_from_theme('audio-volume-muted'))
			self.icons.append(load_icon_from_theme('audio-volume-low'))
			self.icons.append(load_icon_from_theme('audio-volume-medium'))
			self.icons.append(load_icon_from_theme('audio-volume-high'))
			return
		theme_dir = os.path.join(APP_DIR, 'themes', THEME.value)
		self.icons.append(gtk.gdk.pixbuf_new_from_file(os.path.join(theme_dir, 'audio-volume-muted.svg')))
		self.icons.append(gtk.gdk.pixbuf_new_from_file(os.path.join(theme_dir, 'audio-volume-low.svg')))
		self.icons.append(gtk.gdk.pixbuf_new_from_file(os.path.join(theme_dir, 'audio-volume-medium.svg')))
		self.icons.append(gtk.gdk.pixbuf_new_from_file(os.path.join(theme_dir, 'audio-volume-high.svg')))

	def button_scroll(self, window, event):
		vol = self.bar.get_fraction()
		if event.direction == 0:
			vol += 0.02
		elif event.direction == 1:
			vol -= 0.02
		self.set_volume((vol*100, vol*100))

	def event_callback(self, widget, rectangle):
		"""Called when the panel sends a size."""
		if self.vertical:
			size = rectangle[2]
		else:
			size = rectangle[3]
		if size != self.size:
			self.resize_image(size)

	def resize_image(self, size):
		"""Called to resize the image."""
		#I like the look better with the -2, there is no technical reason for it.
		scaled_pixbuf = self.pixbuf.scale_simple(size-2, size-2, gtk.gdk.INTERP_BILINEAR)
		self.image.set_from_pixbuf(scaled_pixbuf)
		self.size = size

	def button_press(self, window, event):
		"""Show/Hide the volume control on button 1 and the menu on button 3"""
		if event.button == 1:
			if event.type == gtk.gdk._2BUTTON_PRESS:
				self.mute()
			else:
				if not self.hide_volume():
					self.show_volume(event)
		elif event.button == 3:
			self.hide_volume()
			self.menu.popup(self, event, self.position_menu)

	def hide_volume(self, event=None):
		"""Destroy the popup volume control"""
		if self.thing:
			self.thing.destroy()
			self.thing = None
			return True
		return False

	def get_panel_orientation(self):
		"""Return the panel orientation ('Top', 'Bottom', 'Left', 'Right')
		and the margin for displaying a popup menu"""
		pos = self.socket.property_get('_ROX_PANEL_MENU_POS', 'STRING', False)
		if pos: pos = pos[2]
		if pos:
			side, margin = pos.split(',')
			margin = int(margin)
		else:
			side, margin = None, 2
		return side

	def set_position(self):
		"""Set the position of the popup"""
		side = self.get_panel_orientation()
		vertical = False

		# widget (x, y, w, h, bits)
		geometry = self.socket.get_geometry()

		if side == 'Bottom':
			vertical = True
			self.thing.set_size_request(APP_SIZE[0], APP_SIZE[1])
			self.thing.move(self.socket.get_origin()[0],
						self.socket.get_origin()[1]-APP_SIZE[1])
		elif side == 'Top':
			vertical = True
			self.thing.set_size_request(APP_SIZE[0], APP_SIZE[1])
			self.thing.move(self.socket.get_origin()[0],
						self.socket.get_origin()[1]+geometry[3])
		elif side == 'Left':
			vertical = False
			self.thing.set_size_request(APP_SIZE[1], APP_SIZE[0])
			self.thing.move(self.socket.get_origin()[0]+geometry[2],
						self.socket.get_origin()[1])
		elif side == 'Right':
			vertical = False
			self.thing.set_size_request(APP_SIZE[1], APP_SIZE[0])
			self.thing.move(self.socket.get_origin()[0]-APP_SIZE[1],
						self.socket.get_origin()[1])
		else:
			vertical = True
			self.thing.set_size_request(APP_SIZE[0], APP_SIZE[1])
			self.thing.move(self.socket.get_origin()[0],
						self.socket.get_origin()[1]-APP_SIZE[1])
		return vertical

	def show_volume(self, event):
		"""Display the popup volume control"""

		self.thing = gtk.Window(type=gtk.WINDOW_POPUP)
		self.thing.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_MENU)
		self.thing.set_decorated(False)

		self.volume = VolumeControl(0, 0, 0, True, None, self.set_position())
		self.volume.set_level(self.get_volume())
		self.volume.connect("volume_changed", self.adjust_volume)

		self.thing.add(self.volume)
		self.thing.show_all()
		self.thing.show()

	def adjust_volume(self, vol, channel, vol_left, vol_right):
		"""Set the playback volume"""
		self.set_volume((vol_left, vol_right))

	def set_volume(self, vol):
		"""Send the volume setting(s) to the mixer """
		for i, v in enumerate(vol):
			try:
			        self.mixer.setvolume(int(v), i)
			except alsaaudio.ALSAAudioError:
				pass
		self.level = vol
		self.update_ui()

	def get_volume(self):
		"""Get the volume settings from the mixer"""
		vol = self.mixer.getvolume()
		if len(vol) == 1:
			vol = vol + vol
		self.level = vol
		return (vol[0], vol[1])

	def mute(self):
		try:
			mute = self.mixer.getmute()[0]
			if mute:
				self.mixer.setmute(0)
			else:
				self.mixer.setmute(2)
			self.update_ui()
		except alsaaudio.ALSAAudioError:
			rox.info(_('Device does not support Muting.'))

	def update_ui(self):
		vol = self.level
		try: mute = self.mixer.getmute()[0]
		except alsaaudio.ALSAAudioError: mute = False

		if (vol[0] <= 0) or mute:
			self.pixbuf = self.icons[0]
		elif vol[0] >= 66:
			self.pixbuf = self.icons[3]
		elif vol[0] >= 33:
			self.pixbuf = self.icons[2]
		else:
			self.pixbuf = self.icons[1]

		self.resize_image(self.size)
		self.tips.set_tip(self, _('Volume control') + ': %d%%' % min(vol[0], vol[1]))
		if self.thing:
			self.volume.set_level((vol[0], vol[1]))
		self.bar.set_fraction(max(vol[0], vol[1])/100.0)

	def get_options(self):
		"""Used as the notify callback when options change"""
		if VOLUME_CONTROL.has_changed or MIXER_DEVICE.has_changed:
			try:
				self.mixer = alsaaudio.Mixer(VOLUME_CONTROL.value, 0, get_mixer_device())
			except alsaaudio.ALSAAudioError:
				pass
			else:
				self.get_volume()
				self.update_ui()

		if SHOW_BAR.has_changed:
			if SHOW_BAR.int_value:
				self.bar.show()
			else:
				self.bar.hide()

		if SHOW_ICON.has_changed:
			if SHOW_ICON.int_value:
				self.image.show()
			else:
				self.image.hide()

		if THEME.has_changed:
			self.load_icons()
			self.update_ui()

	def show_options(self, button=None):
		"""Options edit dialog"""
		rox.edit_options()

	def get_info(self):
		"""Display an InfoWin box"""
		InfoWin.infowin(APP_NAME)

	def run_mixer(self, button=None):
		from rox import filer
		filer.spawn_rox((APP_DIR,))

	def quit(self):
		"""Quit"""
		self.destroy()
